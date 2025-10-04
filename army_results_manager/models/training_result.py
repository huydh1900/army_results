from odoo import models, fields, api


class TrainingResult(models.Model):
    _name = "training.result"
    _description = "Kết quả huấn luyện"
    _rec_name = "employee_id"  # Hiển thị tên theo cán bộ

    employee_id = fields.Many2one(
        comodel_name="hr.employee",
        string="Cán bộ",
        required=True,
    )
    training_course_id = fields.Many2one(
        comodel_name="training.course",
        string="Kế hoạch huấn luyện",
        required=True,
    )
    subject_id = fields.Many2one(
        comodel_name="training.subject",
        string="Môn học",
        required=True,
    )
    identification_id = fields.Char(
        string="Mã định danh",
        required=False,
    )
    score = fields.Float(
        string="Điểm số",
        digits=(6, 2),
    )
    result = fields.Selection(
        [
            ("pass", "Đạt"),
            ("fail", "Không đạt"),
            ("excellent", "Xuất sắc"),
            ("good", "Khá"),
            ("average", "Trung bình"),
        ],
        string="Kết quả",
    )

    # Hàm tính kết quả dựa trên điểm
    @api.onchange("score")
    def _onchange_score(self):
        for rec in self:
            if rec.score:
                if rec.score >= 8:
                    rec.result = "excellent"
                elif rec.score >= 7:
                    rec.result = "good"
                elif rec.score >= 5:
                    rec.result = "pass"
                else:
                    rec.result = "fail"
