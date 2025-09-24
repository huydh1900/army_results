from odoo import models, fields


class TrainingSubject(models.Model):
    _name = 'training.subject'
    _rec_name = 'name'
    _description = 'Môn học'

    name = fields.Char("Tên môn học", required=True)
    code = fields.Char("Mã môn học")



