from odoo import models, fields, api
from odoo.exceptions import ValidationError


class TrainingSchedule(models.Model):
    _name = "training.schedule"
    _description = "Kế hoạch huấn luyện"
    _order = "start_date desc"

    name = fields.Char(
        string="Tên kế hoạch",
        required=True
    )

    year = fields.Char(
        string="Năm huấn luyện",
        required=True,
        default=lambda self: fields.Date.today().year
    )

    start_date = fields.Date(
        string="Ngày bắt đầu",
        required=True
    )

    end_date = fields.Date(
        string="Ngày kết thúc",
        required=True
    )

    description = fields.Text(string="Mô tả")

    duration_days = fields.Integer(
        string="Thời lượng (ngày)",
        compute="_compute_duration",
        store=True
    )

    plan_ids = fields.One2many(
        "training.plan",
        "schedule_id",
        string="Các khóa huấn luyện"
    )

    # --- COMPUTE ---
    @api.depends("start_date", "end_date")
    def _compute_duration(self):
        for rec in self:
            if rec.start_date and rec.end_date:
                delta = rec.end_date - rec.start_date
                rec.duration_days = delta.days + 1
            else:
                rec.duration_days = 0

    # --- VALIDATION ---
    @api.constrains("start_date", "end_date")
    def _check_date(self):
        for rec in self:
            if rec.start_date and rec.end_date and rec.end_date < rec.start_date:
                raise ValidationError("Ngày kết thúc phải lớn hơn ngày bắt đầu.")
