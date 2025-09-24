from odoo import api, fields, models, _

class TrainingCategory(models.Model):
    _name = "training.category"
    _description = "Danh mục Thành phần tham gia / Cấp phụ trách"

    name = fields.Char(string="Tên", required=True)
    code = fields.Char(string="Mã")
