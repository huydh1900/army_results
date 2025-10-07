from odoo import api, fields, models, _


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

        # Nếu có default_course thì tạo sẵn một dòng result_ids
        if course_id:
            res['result_ids'] = [(0, 0, {
                'training_course_id': course_id,
                # thêm các field mặc định khác của training.result nếu cần
            })]

        return res


class Employee(models.Model):
    _inherit = "hr.employee"

    is_training_officer = fields.Boolean(
        string="Cán bộ chỉ huy",
        default=False,
    )