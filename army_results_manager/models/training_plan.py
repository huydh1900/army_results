from odoo import fields, models, api
from odoo.exceptions import UserError


class TrainingPlan(models.Model):
    _name = "training.plan"
    _rec_name = 'name'
    _description = "Kế hoạch huấn luyện"

    plan_code = fields.Char(string='Mã kế hoạch', required=True)
    name = fields.Char(string='Tên kế hoạch', required=True)
    description = fields.Text(string="Mô tả")
    start_date = fields.Date(string="Thời gian bắt đầu", required=True)
    end_date = fields.Date(string="Thời gian kết thúc", required=True)
    participants_ids = fields.Many2many('hr.department', string="Đối tượng tham gia")
    state = fields.Selection([
        ('draft', 'Soạn thảo'),
        ('to_modify', 'Cần chỉnh sửa'),
        ('posted', 'Chờ duyệt'),
        ('approved', 'Đã duyệt'),
        ('cancel', 'Hủy'),
    ], string="Trạng thái", default="draft")
    location = fields.Char(string='Địa điểm')
    training_content = fields.Char(string='Nội dung huấn luyện')
    reason_modify = fields.Char(string='Lý do chỉnh sửa')
    course_ids = fields.One2many('training.course', 'plan_id')
    year = fields.Integer(string='Năm')
    total_hours = fields.Float(string='Số giờ', compute='_compute_total_hours', store=True)


    @api.depends('course_ids.total_hours')
    def _compute_total_hours(self):
        for rec in self:
            rec.total_hours = sum(line.total_hours for line in rec.course_ids)

    @api.constrains('start_date', 'end_date')
    def _check_start_date(self):
        for rec in self:
            if rec.start_date > rec.end_date:
                raise UserError('Ngày bắt đầu phải nhỏ hơn ngay kết thúc.')

    def action_post(self):
        for rec in self:
            rec.state = "posted"

    def action_approve(self):
        for rec in self:
            rec.state = "approved"

    def action_open_modify_wizard(self):
        return {
            "type": "ir.actions.act_window",
            "name": "Nhập lý do chỉnh sửa",
            "res_model": "modify.reason.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"active_id": self.id},
        }

    def action_cancel(self):
        for rec in self:
            rec.state = "cancel"
