from odoo import models, fields, api


class TrainingResult(models.Model):
    _name = "training.result"
    _description = "Kết quả huấn luyện"
    _rec_name = "employee_id"  # Hiển thị tên theo cán bộ

    employee_id = fields.Many2one("hr.employee", string='Học viên')
    training_course_id = fields.Many2one("training.course", string="Khóa huấn luyện")
    score = fields.Float(string="Điểm số", digits=(6, 2), group_operator=None)
    result = fields.Selection(
        [
            ("pass", "Đạt"),
            ("fail", "Không đạt"),
            ("excellent", "Xuất sắc"),
            ("good", "Khá"),
            ("average", "Trung bình"),
        ],
        string="Xếp loại",
    )
    note = fields.Char(string='Nhận xét')

    @api.onchange("score")
    def _onchange_score(self):
        for rec in self:
            score = rec.score or 0
            if score >= 8:
                rec.result = "excellent"
            elif score >= 7:
                rec.result = "good"
            elif score >= 5:
                rec.result = "pass"
            elif score >= 4:
                rec.result = "average"
            else:
                rec.result = "fail"
