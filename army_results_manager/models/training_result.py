from odoo import models, fields, api
from odoo.exceptions import UserError
import requests
from openai import OpenAI


class TrainingResult(models.Model):
    _name = "training.result"
    _description = "Kết quả huấn luyện"
    _rec_name = "training_course_id"

    employee_id = fields.Many2one("hr.employee", string='Học viên', readonly=True)
    training_course_id = fields.Many2one("training.course", string="Môn học", readonly=True, ondelete='cascade')
    year = fields.Char(related="training_course_id.year", readonly=True)
    plan_name = fields.Char()
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

    # def action_generate_note_by_ai(self):
    #     """Chuyển đến controller để tạo nhận xét AI"""
    #     self.ensure_one()
    #
    #     return {
    #         'type': 'ir.actions.act_url',
    #         'url': f'/ai/generate_note/{self.id}',
    #         'target': 'self',  # Mở trong cùng tab
    #     }

    def action_generate_note_by_ai(self):
        # Lấy key 1 lần duy nhất
        openai_api_key = self.env['ir.config_parameter'].sudo().get_param('openai.api_key')
        if not openai_api_key:
            return

        # Khởi tạo client 1 lần duy nhất
        client = OpenAI(
            api_key=openai_api_key,
            base_url="https://openrouter.ai/api/v1"
        )

        # Cache prompt template để giảm thao tác string
        prompt_template = (
            "Bạn là cán bộ huấn luyện quân đội. Hãy viết nhận xét ngắn (1–2 câu)** "
            "về học viên có điểm {score} trong khóa huấn luyện {training_course_name}:\n"
            "Không nhắc lại điểm số, không mở đầu bằng “Học viên có điểm…”.\n"
            "Giữ giọng điệu trang nghiêm, nghiêm khắc phê bình, rút kinh nghiệm, điểm cao thì khen cố gắng phát huy, mang tính quân đội."
        )

        for rec in self.filtered(lambda r: r.result):
            try:
                prompt = prompt_template.format(score=rec.score, training_course_name = rec.training_course_id.name)
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": prompt}],
                )
                note_text = response.choices[0].message.content.strip()
                rec.note = note_text or "Không thể tạo nhận xét tự động."
            except Exception as e:
                rec.note = f"Không thể tạo nhận xét tự động (lỗi: {str(e)[:100]})."

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
