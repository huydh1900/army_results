from odoo import models, fields


class TrainingSubject(models.Model):
    _name = 'training.subject'
    _rec_name = 'name'
    _description = 'Môn học'

    name = fields.Char("Tên môn học", required=True)
    code = fields.Char("Mã môn học")
    type_training = fields.Selection([
        ('common_training', 'Huấn luyện chung'),
        ('private_training', 'Huấn luyện riêng'),
    ], string="Loại huấn luyện")



