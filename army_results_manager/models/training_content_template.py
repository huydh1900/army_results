from odoo import models, fields


class TrainingContentTemplate(models.Model):
    _name = 'training.content.template'
    _rec_name = 'name'
    _description = 'Khung nội dung huấn luyện'

    name = fields.Char("Tên nội dung", required=True)
    type = fields.Selection([
        ('si_quan', 'Sĩ quan'),
        ('phan_doi', 'Phân đội'),
    ], required=True, string='Đối tượng huấn luyện')
    line_ids = fields.One2many('training.content.template.line', 'content_template_id')

class TrainingContentTemplateLine(models.Model):
    _name = 'training.content.template.line'
    _rec_name = 'name'
    _description = 'Chi tiết khung nội dung huấn luyện'

    name = fields.Char(string="Bài học", required=True)
    section_id = fields.Many2one('training.section', string='Chương học')
    content_template_id = fields.Many2one('training.content.template')





