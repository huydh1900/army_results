from odoo import fields, models, api
from odoo.exceptions import UserError
from datetime import date, timedelta


class TrainingPlan(models.Model):
    _name = "training.plan"
    _rec_name = 'name'
    _inherit = ['mail.thread']
    _description = "Khóa huấn luyện"

    plan_code = fields.Char(string='Mã', required=True)
    name = fields.Char(string='Khóa huấn luyện', required=True)
    description = fields.Text(string="Mô tả")
    start_date = fields.Date(string="Thời gian bắt đầu", required=True)
    end_date = fields.Date(string="Thời gian kết thúc", required=True)
    participants_ids = fields.Many2many('hr.department', string="Đơn vị quản lý", required=True)
    state = fields.Selection([
        ('draft', 'Soạn thảo'),
        ('to_modify', 'Cần chỉnh sửa'),
        ('posted', 'Chờ duyệt'),
        ('approved', 'Đã duyệt'),
        ('cancel', 'Hủy'),
    ], string="Trạng thái", default="draft", tracking=True)

    student_ids = fields.Many2many('hr.employee', string='Học viên', domain="[('role', '=', 'student')]", required=True)
    training_content = fields.Char(string='Nội dung huấn luyện')
    reason_modify = fields.Text(string='Lý do chỉnh sửa', tracking=True)
    course_ids = fields.One2many('training.course', 'plan_id')
    year = fields.Char(string='Năm', default=lambda self: str(date.today().year), required=True)
    total_hours = fields.Float(string='Số giờ', compute='_compute_total_hours', store=True)
    common_subject_ids = fields.One2many(
        'training.course',
        'plan_id',
        domain=[('is_common', '=', True)],
        context={'default_is_common': True},
        string='Môn huấn luyện chung'
    )

    schedule_id = fields.Many2one(
        "training.schedule",
        ondelete='cascade',
        string="Kế hoạch huấn luyện", required=True
    )

    # Môn huấn luyện riêng theo nhóm/đơn vị
    specific_subject_ids = fields.One2many(
        'training.course',
        'plan_id',
        domain=[('is_common', '=', False)],
        string='Môn huấn luyện riêng'
    )
    approver_id = fields.Many2one(related='schedule_id.approver_id', string='Cán bộ phê duyệt', readonly=True,
                                  store=True)
    count_rec_training_day = fields.Integer(compute='_compute_count_rec_training_day')

    def _compute_count_rec_training_day(self):
        TrainingDay = self.env['training.day']
        for rec in self:
            rec.count_rec_training_day = TrainingDay.search_count([('plan_id', '=', rec.id)])

    def action_open_training_day(self):
        self.ensure_one()
        tree_view_id = self.env.ref("army_results_manager.view_training_day_in_plan_tree").id
        form_view_id = self.env.ref("army_results_manager.view_training_day_form").id

        views = [
            (tree_view_id, 'tree'),
            (form_view_id, 'form'),
        ]
        return {
            "type": "ir.actions.act_window",
            "name": "Chi tiết bài học",
            "views": views,
            "res_model": "training.day",
            "domain": [('plan_id', '=', self.id)],
            "target": "current",
        }

    def unlink(self):
        user = self.env.user
        # Nếu user thuộc nhóm Cán bộ nhập liệu
        if user.has_group('army_results_manager.group_data_entry_officer'):
            for rec in self:
                if rec.state == 'approved':
                    raise UserError('Bạn không được phép xóa kế hoạch đã duyệt!')

        plan_ids = self.ids

        # Xoá training days trước khi gọi super()
        training_days = self.env['training.day'].search([('plan_id', 'in', plan_ids)])
        training_days.unlink()

        # Xoá kế hoạch
        res = super().unlink()

        return res

    @api.model
    def cron_generate_daily_warning(self):
        today = date.today()
        upcoming_days = 3  # số ngày trước khi bắt đầu mà bạn muốn cảnh báo
        upcoming_date = today + timedelta(days=upcoming_days)

        # Lọc các kế hoạch chưa duyệt và sắp bắt đầu
        plans = self.search([
            ("state", "in", ["draft", "posted", "to_modify"]),
            ("start_date", "<=", upcoming_date),
            ("start_date", ">=", today),
        ])

        if plans:
            message = (
                    "Các kế hoạch sắp đến ngày bắt đầu nhưng chưa được duyệt:\n" +
                    "\n".join([f"- {plan.name} (ngày {plan.start_date})" for plan in plans])
            )

        # Ghi log lại
        self.env["training.warning.log"].create({"message": message})
        return True

    @api.depends('course_ids.total_hours')
    def _compute_total_hours(self):
        for rec in self:
            rec.total_hours = sum(line.total_hours or 0.0 for line in rec.course_ids)

    @api.constrains('start_date', 'end_date')
    def _check_start_date(self):
        for rec in self:
            if rec.start_date > rec.end_date:
                raise UserError('Ngày bắt đầu phải nhỏ hơn ngay kết thúc.')

    def action_post(self):
        if not self.approver_id:
            raise UserError('Bạn phải điền người phê duyệt trước khi bấm Gửi duyệt!')
        elif not self.student_ids:
            raise UserError('Bạn phải điền học viên trước khi bấm Gửi duyệt!')

        count_training_day = self.env['training.day'].search([('plan_id', '=', self.id)])
        if len(count_training_day) == 0:
            raise UserError('Phải có ít nhất 1 bài học trong Kế hoạch!')

        self.write({'state': 'posted'})
        self.env['training.day'].search([
            ('plan_id', '=', self.id),
            ('state', '!=', 'approved'),
        ]).write({'state': 'posted'})

    def action_cancel(self):
        self.write({'state': 'cancel'})
        self.env['training.day'].search([
            ('plan_id', '=', self.id),
            ('state', '!=', 'approved'),
        ]).write({'state': 'cancel'})
