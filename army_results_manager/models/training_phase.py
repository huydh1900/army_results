from odoo import fields, models, api

class TrainingPhase(models.Model):
    _name = "training.phase"
    _description = "Giai đoạn huấn luyện"

    name = fields.Selection([
        ("gd1", "Giai đoạn 1: Huấn luyện cơ bản"),
        ("gd2", "Giai đoạn 2: Huấn luyện phân đoạn"),
        ("gd3", "Giai đoạn 3: Huấn luyện tổng hợp, nâng cao"),
        ("gd4", "Giai đoạn 4: Huấn luyện theo chiến thuật thi đấu"),
        ("gd5", "Giai đoạn 5: Thi đấu"),
        ("gd6", "Giai đoạn 6: Huấn luyện duy trì kỹ thuật sau thi đấu"),
    ], string="Tên giai đoạn", required=True)
    course_ids = fields.One2many("training.course", 'phase_id', string="Kế hoạch")
    start_date = fields.Date(string="Ngày bắt đầu")
    end_date = fields.Date(string="Ngày kết thúc")
    total_hours = fields.Float(string="Tổng số giờ")
    block_id = fields.Many2one('training.course.block', string="Khối huấn luyện")
    lesson_ids = fields.One2many('training.lesson', 'phase_id', string='Nội dung huấn luyện')
    competition_id = fields.Many2one('training.competition', string='Giai đoạn huấn luyện')
