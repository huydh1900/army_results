from odoo import models, fields


class TrainingLesson(models.Model):
    _name = 'training.lesson'
    _rec_name = 'name'
    _description = 'Nội dung huấn luyện'

    name = fields.Char("Tên nội dung", required=True)
    total_hours = fields.Float(string='Số giờ')
    course_id = fields.Many2one('training.course', string='Tên khóa huấn luyện', readonly=True)
    section_id = fields.Many2one('training.section', string='Chương')
    time_ids = fields.One2many('training.time', 'lesson_id', string='Thời gian huân luyện')
    phase_id = fields.Many2one('training.phase')



