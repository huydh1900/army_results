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
    ], string="Vai trò", readonly=True)
    job_id = fields.Many2one(tracking=True, string='Chức vụ')
    cap_bac = fields.Char(string='Cấp bậc')
    ngay_sinh = fields.Date(string='Ngày sinh')
    identification_id = fields.Char(string='Số hiệu sĩ quan', groups="hr.group_hr_user", tracking=True)
    result_ids = fields.One2many('training.result', 'employee_id')
    day_comment_ids = fields.Many2many('training.day.comment')
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
    message_main_attachment_id = fields.Many2one(groups="base.group_user")
    don_vi_cong_tac = fields.Text(string='Đơn vị công tác')

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

    def action_related_contacts(self):
        return

    @api.depends("result_ids.score", "result_ids.result")
    def _compute_classification(self):
        for emp in self:
            results = emp.result_ids.filtered(lambda r: r.score and r.result)

            if not results:
                emp.classification = False
                continue

            total = 0
            count = 0
            for r in results:
                try:
                    total += float(r.score)
                    count += 1
                except:
                    pass

            if not count:
                emp.classification = False
                continue

            avg = total / count

            if avg >= 8:
                emp.classification = "excellent"
            elif avg >= 7:
                emp.classification = "good"
            elif avg >= 5:
                emp.classification = "pass"
            elif avg >= 4:
                emp.classification = "average"
            else:
                emp.classification = "fail"

    @api.model
    def get_top_department_training(self, limit=5):
        self.env.cr.execute("""
            SELECT 
                d.id,
                d.name,
                COUNT(e.id) AS good_count
            FROM hr_employee e
            JOIN hr_department d ON e.department_id = d.id
            WHERE e.classification IN ('excellent', 'good')
            GROUP BY d.id, d.name
            ORDER BY good_count DESC
            LIMIT %s
        """, (limit,))

        rows = self.env.cr.dictfetchall()

        return [
            {"label": r["name"], "value": r["good_count"]}
            for r in rows
        ]


