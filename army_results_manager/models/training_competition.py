from odoo import fields, models, api


class TrainingCompetition(models.Model):
    _name = "training.competition"
    _rec_name = 'name'
    _description = "Quản lý hội thi"

    name = fields.Char(string="Tên hội thi", required=True)
    year = fields.Integer(string="Năm tổ chức")
    start_date = fields.Date(string="Bắt đầu huấn luyện")
    end_date = fields.Date(string="Kết thúc huấn luyện")
    phase_ids = fields.One2many('training.phase', 'competition_id', string='Giai đoạn huấn luyện')