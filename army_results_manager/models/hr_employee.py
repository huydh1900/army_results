from odoo import api, fields, models, _
from statistics import mean

class HrEmployeePrivate(models.Model):
    _inherit = ['hr.employee']

    training_expertise = fields.Char(string="Chuyên môn huấn luyện")
    coaching_experience = fields.Char(string="Kinh nghiệm huấn luyện")
    appointment_date = fields.Date(string="Ngày nhận chức")
    role = fields.Selection([
        ('commanding_officer', 'Cán bộ chỉ huy'),
        ('training_officer', 'Cán bộ phụ trách huấn luyện'),
        ('student', 'Học viên'),
    ], string="Vai trò")
    job_id = fields.Many2one(tracking=True, string='Chức vụ')
    identification_id = fields.Char(string='Số hiệu sĩ quan', groups="hr.group_hr_user", tracking=True)
    result_ids = fields.One2many('training.result', 'employee_id')
    day_ids = fields.Many2many('training.day')
    classification = fields.Selection(
        [
            ("pass", "Đạt"),
            ("fail", "Không đạt"),
            ("excellent", "Xuất sắc"),
            ("good", "Khá"),
            ("average", "Trung bình"),
        ],
        string="Xếp loại", compute="_compute_classification", store=True,
    )

    @api.model
    def count_student_summary(self):
        Employee = self.env['hr.employee']

        domain_student = [('role', '=', 'student')]

        total = Employee.search_count(domain_student)
        good = Employee.search_count(domain_student + [('classification', '=', 'excellent')])
        fail = Employee.search_count(domain_student + [('classification', '=', 'fail')])

        plans = self.env['training.plan'].search([])
        students = plans.mapped('course_ids.student_ids')
        unique_students = set(students)
        training = len(unique_students)

        return {
            'total': total,
            'good': good,
            'fail': fail,
            'training': training,
        }

    @api.depends("result_ids")
    def _compute_classification(self):
        for rec in self:
            scores = []

            # Thu thập toàn bộ điểm của record
            for result in rec.result_ids:
                # Nếu result.score là 1 con số:
                if isinstance(result.score, (int, float)):
                    scores.append(result.score)
                # Nếu là danh sách điểm (ví dụ One2many):
                elif isinstance(result.score, list):
                    scores.extend(result.score)

            if not scores:
                rec.classification = False
                continue

            avg_score = mean(scores)

            # Xếp loại theo ngưỡng điểm
            if avg_score >= 9:
                rec.classification = "excellent"
            elif avg_score >= 8:
                rec.classification = "good"
            elif avg_score >= 6.5:
                rec.classification = "average"
            elif avg_score >= 5:
                rec.classification = "pass"
            else:
                rec.classification = "fail"

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        role = self.env.context.get('default_role')
        department_id = self.env.context.get('default_department_id')
        course_id = self.env.context.get('default_course')
        res['department_id'] = department_id

        if role == 'commanding_officer':
            res['role'] = 'commanding_officer'
        elif role == 'training_officer':
            res['role'] = 'training_officer'
        else:
            res['role'] = 'student'

        if course_id:
            res['result_ids'] = [(0, 0, {
                'training_course_id': course_id,
            })]

        return res


class Employee(models.Model):
    _inherit = "hr.employee"

    is_training_officer = fields.Boolean(
        string="Cán bộ chỉ huy",
        default=False,
    )
