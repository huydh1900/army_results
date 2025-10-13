from odoo import models, fields


class TrainingComment(models.Model):
    _name = 'training.comment'
    _description = 'Nhận xét'

    week_id = fields.Many2one('training.week', string="Tuần", ondelete='cascade')
    day_id = fields.Many2one('training.day', string="Ngày huấn luyện", ondelete='cascade')
    note = fields.Char("Nhận xét")
    employee_id = fields.Many2one('hr.employee')



