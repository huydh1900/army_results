from odoo import models, fields


class TrainingTime(models.Model):
    _name = 'training.time'
    _description = 'Thời gian học'

    lesson_id = fields.Many2one('training.lesson', string='Nội dung', readonly=True)
    month = fields.Selection(
        [(str(i), f"Tháng {i}") for i in range(1, 13)],
        string="Tháng"
    )

    week = fields.Selection(
        [(str(i), f"Tuần {i}") for i in range(1, 6)],
        string="Tuần"
    )

    day = fields.Date(string="Ngày")
    total_hours = fields.Float(string='Số giờ')

