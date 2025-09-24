from odoo import api, fields, models, _


class HrEmployeePrivate(models.Model):
    _inherit = ['hr.employee']

    training_expertise = fields.Char(string="Chuyên môn huấn luyện")
    coaching_experience = fields.Char(string="Kinh nghiệm huấn luyện")
    appointment_date = fields.Date(string="Ngày nhận chức")
    training_course_id = fields.Many2one('training.course', string="Kế hoạch huấn luyện")
    role = fields.Selection([
        ('commanding_officer', 'Cán bộ chỉ huy'),
        ('training_officer', 'Cán bộ phụ trách huấn luyện'),
        ('student', 'Học viên'),
    ], string="Vai trò")
    # training_result_ids = fields.One2many(
    #     'training.result',
    #     'employee_id',
    #     string="Kết quả huấn luyện"
    # )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        role = self.env.context.get('role')
        department_id = self.env.context.get('department_id')
        res['department_id'] = department_id
        if role == 'commanding_officer':
            res['role'] = 'commanding_officer'
        elif role == 'training_officer':
            res['role'] = 'training_officer'
        else:
            res['role'] = 'student'
        return res
