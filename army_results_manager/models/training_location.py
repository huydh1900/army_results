from odoo import models, fields, api


class TrainingLocation(models.Model):
    _name = "training.location"
    _rec_name = 'name'
    _description = "Vị trí huấn luyện"

    name = fields.Char("Tên khu vực", required=True)
