from odoo import models, fields

class CollectedData(models.Model):
    _name = 'collected.data'
    _description = 'Dữ liệu thu thập'

    title = fields.Char(string='Tiêu đề / Link', required=True)
    content = fields.Text(string='Nội dung')
    source_id = fields.Many2one('data.source', string='Nguồn', ondelete='cascade')
    collected_date = fields.Datetime(string='Ngày thu thập', default=fields.Datetime.now)
