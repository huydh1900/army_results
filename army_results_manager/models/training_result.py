from odoo import models, fields, api
from odoo.exceptions import UserError
import requests


class TrainingResult(models.Model):
    _name = "training.result"
    _description = "Kết quả huấn luyện"
    _rec_name = "training_course_id"

    employee_id = fields.Many2one("hr.employee", string='Học viên', readonly=True)
    training_course_id = fields.Many2one("training.course", string="Môn học", readonly=True, ondelete='cascade')
    year = fields.Char(related="training_course_id.year", readonly=True, store=True)
    plan_id = fields.Many2one(related="training_course_id.plan_id", readonly=True, store=True)
    plan_name = fields.Char(related="plan_id.name", readonly=True, store=True)
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
    note_tmp = fields.Text(compute='_compute_note_tmp', store=True)

    @api.depends('day_comment_ids.comment')
    def _compute_note_tmp(self):
        for rec in self:
            comments = rec.day_comment_ids.mapped('comment')
            rec.note_tmp = "\n".join(c for c in comments if c)

    def action_generate_note_by_ai(self):
        """Tạo nhận xét AI trực tiếp, chỉ cập nhật khi thành công"""
        self.ensure_one()

        # Lấy domain server (ví dụ: http://118.70.177.132:8000)
        domain = self.env['ir.config_parameter'].sudo().get_param('openai.api_key')

        if not domain:
            self.note = 'Lỗi: Chưa cấu hình server domain!'
            return

        if not self.employee_id:
            self.note = 'Lỗi: Học viên không hợp lệ!'
            return

        fastapi_url = f"{domain}/api/summarize_from_db/{self.employee_id.id}"
        payload = {
            "table": "public.training_result",
            "training_course_id": self.training_course_id,
            "plan_id": self.plan_id
        }

        try:
            response = requests.post(fastapi_url, json=payload, timeout=30)
            data = response.json()

            if data.get("status") == "success":
                self.note = data.get("summary", "Không có nội dung nhận xét")
            else:
                self.note = 'Không thể tạo nhận xét AI. Vui lòng thử lại sau.'
        except Exception:
            self.note = 'Không thể tạo nhận xét AI. Vui lòng thử lại sau.'

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
