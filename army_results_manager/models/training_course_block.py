from odoo import fields, models, api

class TrainingCourseBlock(models.Model):
    _name = "training.course.block"
    _rec_name = "type"
    _description = "Khối huấn luyện (Sĩ quan / Phân đội)"

    type = fields.Selection([
        ('si_quan', 'Sĩ quan'),
        ('phan_doi', 'Phân đội'),
    ], required=True, string='Loại huấn luyện')

    course_id = fields.Many2one('training.course', string="Kế hoạch", readonly=True)
    phase_ids = fields.One2many('training.phase', 'block_id', string="Các giai đoạn")
