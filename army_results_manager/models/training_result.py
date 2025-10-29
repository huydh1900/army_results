from odoo import models, fields, api
from openai import OpenAI


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
    note = fields.Text(string='Nhận xét')

    def action_generate_note_by_ai(self):
        # Lấy key 1 lần duy nhất
        openai_api_key = self.env['ir.config_parameter'].sudo().get_param('openai.api_key')
        if not openai_api_key:
            self.write({'note': "Chưa cấu hình OpenAI API Key."})
            return

        # Khởi tạo client 1 lần duy nhất
        client = OpenAI(
            api_key=openai_api_key,
            base_url="https://openrouter.ai/api/v1"
        )

        # Cache prompt template để giảm thao tác string
        prompt_template = (
            "Bạn là cán bộ huấn luyện quân đội. Hãy viết nhận xét ngắn (1–2 câu)** "
            "về học viên có điểm {score} trong khóa huấn luyện:\n"
            "Không nhắc lại điểm số, không mở đầu bằng “Học viên có điểm…”.\n"
            "Giữ giọng điệu trang nghiêm, nghiêm khắc phê bình, rút kinh nghiệm, điểm cao thì khen cố gắng phát huy, mang tính quân đội."
        )

        for rec in self.filtered(lambda r: r.result):
            try:
                prompt = prompt_template.format(score=rec.score)
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
