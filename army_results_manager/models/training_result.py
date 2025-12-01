from odoo import models, fields, api
from openai import OpenAI
from odoo.exceptions import UserError
import requests

class TrainingResult(models.Model):
    _name = "training.result"
    _description = "Kết quả huấn luyện"
    _rec_name = "training_course_id"

    employee_id = fields.Many2one("hr.employee", string='Học viên', readonly=True)
    training_course_id = fields.Many2one("training.course", string="Khóa huấn luyện", readonly=True, ondelete='cascade')
    year = fields.Char(related="training_course_id.year", readonly=True)
    day_comment_ids = fields.One2many('training.day.comment', 'result_id')
    score = fields.Char(string="Điểm số")
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
    note = fields.Text(string='Nhận xét', tracking=True)

    def action_generate_note_by_ai(self):
        """Chuyển đến controller để tạo nhận xét AI"""
        self.ensure_one()
        
        return {
            'type': 'ir.actions.act_url',
            'url': f'/ai/generate_note/{self.id}',
            'target': 'self',  # Mở trong cùng tab
        }

    @api.onchange("score")
    def _onchange_score(self):
        for rec in self:
            try:
                score = float(rec.score)
            except ValueError:
                raise UserError("Điểm số nhập vào không cho phép là ký tự!")
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
