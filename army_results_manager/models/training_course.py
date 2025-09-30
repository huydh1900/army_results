from odoo import fields, models, api


class TrainingCourse(models.Model):
    _name = "training.course"
    _rec_name = 'name'
    _description = "Khóa huấn luyện"

    name = fields.Char(string="Tên khóa")
    start_date = fields.Date(string="Bắt đầu huấn luyện")
    end_date = fields.Date(string="Kết thúc huấn luyện")
    total_hours = fields.Float(string='Tổng số giờ', compute='_compute_total_hours', store=True)
    plan_id = fields.Many2one('training.plan')
    mission_ids = fields.One2many('training.mission', 'course_id', string='Danh sách nội dung huấn luyện')
    student_ids = fields.Many2many('hr.employee', string='Học viên', domain="[('role', '=', 'student')]")
    student_count = fields.Integer(
        string='Số học viên',
        compute='_compute_student_count'
    )

    @api.depends('mission_ids', 'mission_ids.total_hours')
    def _compute_total_hours(self):
        for rec in self:
            if rec.mission_ids:
                rec.total_hours = sum(line.total_hours for line in rec.mission_ids if not line.exclude_main_training)
            else:
                rec.total_hours = 0


    def _compute_student_count(self):
        for rec in self:
            rec.student_count = len(rec.student_ids)

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