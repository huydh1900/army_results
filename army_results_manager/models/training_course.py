from odoo import fields, models, api


class TrainingCourse(models.Model):
    _name = "training.course"
    _rec_name = 'name'
    _description = "Khóa huấn luyện"

    name = fields.Char(string="Tên khóa")
    department_id = fields.Many2one("hr.department", string="Đơn vị tổ chức")
    phase_id = fields.Many2one("training.phase", string="Các giai đoạn")
    start_date = fields.Date(string="Bắt đầu huấn luyện")
    end_date = fields.Date(string="Kết thúc huấn luyện")
    year = fields.Integer(string='Năm')
    total_hours = fields.Float(string='Tổng số giờ')
    lesson_ids = fields.One2many('training.lesson', 'course_id')
    plan_id = fields.Many2one('training.plan')
    mission_ids = fields.One2many('training.mission', 'course_id', string='Danh sách nhiệm vụ huấn luyện')
    student_ids = fields.Many2many('hr.employee', string='Học viên', domain="[('role', '=', 'student')]")
    student_count = fields.Integer(
        string='Số học viên',
        compute='_compute_student_count'
    )

    def _compute_student_count(self):
        for rec in self:
            rec.student_count = len(rec.student_ids)


    @api.constrains('phase_ids')
    @api.onchange('phase_ids')
    def _constrain_phase_ids(self):
        for rec in self:
            rec.total_hours = sum(line.total_hours for line in rec.phase_ids)

    def action_open_students(self):
        """Mở danh sách học viên của khóa huấn luyện"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Học viên',
            'res_model': 'hr.employee',  # hoặc model học viên của bạn
            'view_mode': 'tree,form',
            'domain': [('id', 'in', self.student_ids.ids)],
            'target': 'current',
        }