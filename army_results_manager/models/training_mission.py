from odoo import models, fields


class TrainingMission(models.Model):
    _name = 'training.mission'
    _description = 'Nhiệm vụ huấn luyện'

    name = fields.Char(string="Tên nhiệm vụ", required=True)
    description = fields.Text(string="Mô tả nhiệm vụ")
    total_hours = fields.Float(string='Số giờ')
    start_date = fields.Date(string="Thời gian bắt đầu")
    end_date = fields.Date(string="Thời gian kết thúc")
    plan_id = fields.Many2one('training.plan', string='Kế hoạch huấn luyện', readonly=True)
    participants_ids = fields.Many2many('hr.department', string="Đối tượng tham gia")
    material_ids = fields.One2many('training.material', 'mission_id', string="Tài liệu / Video")

