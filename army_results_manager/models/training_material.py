from odoo import models, fields

class TrainingMaterial(models.Model):
    _name = 'training.material'
    _description = 'Tài liệu / Video huấn luyện'

    name = fields.Char(string="Tên tài liệu", required=True)
    file = fields.Binary(string="File đính kèm", attachment=True)
    mission_id = fields.Many2one('training.mission', string="Nhiệm vụ huấn luyện", readonly=True)
    type = fields.Selection([('doc', 'Tài liệu'), ('video', 'Video')], string="Loại")
    video = fields.Binary(string="Video", attachment=True)