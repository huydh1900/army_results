from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError


class TrainingSchedule(models.Model):
    _name = "training.schedule"
    _description = "Kế hoạch huấn luyện"
    _inherit = ['mail.thread']
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

    plan_type = fields.Selection(
        [
            ("week", "Kế hoạch tuần"),
            ("month", "Kế hoạch tháng"),
            ("year", "Kế hoạch năm"),
        ],
        string="Loại kế hoạch",
        required=True,
        default="year"
    )

    # Tháng – dùng cho kế hoạch tháng hoặc tuần
    month_number = fields.Selection(
        [(str(i), f"Tháng {i}") for i in range(1, 13)],
        string="Tháng"
    )

    # Tuần trong tháng
    week_number = fields.Selection(
        [(str(i), f"Tuần {i}") for i in range(1, 6)],
        string="Tuần trong tháng",
        help="Tuần của tháng (1–5)"
    )

    state = fields.Selection([
        ('draft', 'Soạn thảo'),
        ('to_modify', 'Cần chỉnh sửa'),
        ('posted', 'Chờ duyệt'),
        ('approved', 'Đã duyệt'),
        ('cancel', 'Hủy'),
    ], string="Trạng thái", default="draft", tracking=True)

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
    reason_modify = fields.Text(string='Lý do chỉnh sửa', tracking=True)

    def action_need_edit(self):
        return {
            "type": "ir.actions.act_window",
            "name": "Nhập lý do chỉnh sửa",
            "res_model": "modify.reason.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"active_id": self.id},
        }

    def unlink(self):
        for rec in self:
            if rec.state == "approved":
                raise UserError("Không thể xóa kế hoạch đã được duyệt.")
        return super(TrainingSchedule, self).unlink()

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

    @api.constrains("plan_type", "month_number", "week_number")
    def _check_plan_type(self):
        for rec in self:
            # Theo tuần => cần: năm + tháng + tuần
            if rec.plan_type == "week":
                if not rec.month_number:
                    raise ValidationError("Kế hoạch theo tuần phải chọn tháng.")
                if not rec.week_number:
                    raise ValidationError("Kế hoạch theo tuần phải chọn tuần trong tháng.")

    @api.onchange("plan_type")
    def _onchange_plan_type(self):
        if self.plan_type == "year":
            self.month_number = False
            self.week_number = False

        elif self.plan_type == "month":
            self.week_number = False

        elif self.plan_type == "week":
            # ensure month is required, but don't delete it
            pass

    def action_submit(self):
        self.write({"state": "posted"})

    def action_approve(self):
        self.write({"state": "approved"})

    def action_cancel(self):
        self.write({"state": "cancel"})
