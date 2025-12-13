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
    reason_modify = fields.Text(string='Lý do chỉnh sửa', tracking=True, readonly=True)
    approver_id = fields.Many2one('hr.employee', string='Cán bộ phê duyệt', required=True,
                                  domain=[('role', '=', 'commanding_officer')])

    def write(self, vals):
        for rec in self:
            if rec.state == 'to_modify':
                # Nếu là Cán bộ chỉ huy
                if self.env.user.has_group('army_results_manager.group_training_commander'):
                    # Chỉ cho phép ghi chatter
                    allowed_fields = {
                        'message_ids',
                        'message_follower_ids',
                        'activity_ids',
                    }

                    # Nếu sửa field nghiệp vụ → chặn
                    forbidden = set(vals) - allowed_fields
                    if forbidden:
                        raise UserError(
                            "Kế hoạch đang ở trạng thái Cần chỉnh sửa. Cán bộ chỉ huy chỉ được phép ghi chú hoặc nhắn tin.")
        return super().write(vals)

    @api.model
    def get_training_state_summary(self):
        """Trả dữ liệu tổng hợp theo state"""
        states = [
            ('draft', 'Soạn thảo'),
            ('to_modify', 'Cần chỉnh sửa'),
            ('not_done', 'Chưa hoàn thành'),
            ('posted', 'Chờ duyệt'),
            ('approved', 'Đã duyệt'),
            ('cancel', 'Hủy'),
        ]
        result = []
        for state, label in states:
            count = self.search_count([('state', '=', state)])
            result.append({'state': state, 'label': label, 'value': count})
        return result

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
            if rec.state != "cancel" and rec.state != "draft":
                raise UserError("Bạn phải Hủy kế hoạch trước khi xóa!")
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
            pass

    def action_submit(self):
        if not self.plan_ids:
            raise UserError('Phải có ít nhất 1 khóa huấn luyện trước khi Gửi duyệt!')

        for rec in self:
            for plan in rec.plan_ids:
                plan.action_post()
                plan.write({"state": "posted"})

        self.write({"state": "posted"})

    def action_approve(self):
        action = self.sudo().env.ref('army_results_manager.action_training_day_posted').read()[0]
        action['target'] = 'current'
        return action

    def action_cancel(self):
        for rec in self:
            for plan in rec.plan_ids:
                plan.action_cancel()
        self.write({"state": "cancel"})
