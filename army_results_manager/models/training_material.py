import mimetypes

from odoo import models, fields, api

class TrainingMaterial(models.Model):
    _name = 'training.material'
    _description = 'Tài liệu / Video huấn luyện'

    name = fields.Char(string="Tên tài liệu", required=True)
    file = fields.Binary(string="File đính kèm", attachment=True)
    mission_id = fields.Many2one('training.mission', string="Nhiệm vụ huấn luyện", readonly=True)
    type = fields.Selection([('doc', 'Tài liệu'), ('video', 'Video')], string="Loại")
    video = fields.Binary(string="Video", attachment=True)


class TrainingResource(models.Model):
    _name = 'training.resource'
    _description = 'Tài liệu / Bài tập Huấn luyện mẫu'
    _rec_name = 'name'

    name = fields.Char("Tên tài liệu", required=True)

    # Liên kết đến bài học
    lesson_id = fields.Many2one(
        'training.lesson',
        string='Bài học',
    )

    type = fields.Selection([
        ('document', 'Tài liệu'),
        ('video', 'Video hướng dẫn'),
    ], string="Loại", default='document')

    file = fields.Binary("Tệp đính kèm")
    video = fields.Binary(string="Video", attachment=True)
    description = fields.Text("Mô tả")
    day_comment_id = fields.Many2one('training.day.comment')
