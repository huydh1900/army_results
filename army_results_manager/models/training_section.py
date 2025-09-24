from odoo import fields, models, api


class TrainingSection(models.Model):
    _name = "training.section"
    _rec_name = 'name'
    _description = "Tên chương"

    name = fields.Char(string="Tên chương")
