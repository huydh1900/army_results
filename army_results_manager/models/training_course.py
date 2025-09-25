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


    @api.constrains('phase_ids')
    @api.onchange('phase_ids')
    def _constrain_phase_ids(self):
        for rec in self:
            rec.total_hours = sum(line.total_hours for line in rec.phase_ids)