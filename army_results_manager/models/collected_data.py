from odoo import models, fields

class CollectedData(models.Model):
    _name = 'collected.data'
    _rec_name = 'title'
    _description = 'Dữ liệu thu thập'

    title = fields.Char("Tiêu đề")
    link = fields.Char("Liên kết")
    description = fields.Text("Mô tả")
    category = fields.Selection([
        ("tin_tuc", "Tin tức"),
        ("su_kien", "Sự kiện"),
        ("thong_bao", "Thông báo"),
    ], string="Loại tin")
    source_id = fields.Many2one("data.source", string="Nguồn")
    collected_date = fields.Datetime(default=fields.Datetime.now, string="Thời gian")
    image_url = fields.Char("Ảnh (URL)")
