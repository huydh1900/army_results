from odoo import fields, models, api
from odoo.exceptions import UserError

class TrainingPlan(models.Model):
    _name = "training.plan"
    _rec_name = 'name'
    _description = "Kế hoạch huấn luyện"

    plan_code = fields.Char(string='Mã kế hoạch', required=True)
    name = fields.Char(string='Tên kế hoạch', required=True)
    description = fields.Text(string="Mô tả")
    type = fields.Selection([
        ('squad', 'Phân đội'),
        ('officer', 'Sĩ quan')
    ], string="Loại huấn luyện", required=True, default='squad'
    )
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
    location_id = fields.Many2one('training.location', string='Địa điểm')
    training_content = fields.Char(string='Nội dung huấn luyện')
    reason_modify = fields.Char(string='Lý do chỉnh sửa')
    course_ids = fields.One2many('training.course', 'plan_id')
    year = fields.Integer(string='Năm')
    total_hours = fields.Float(string='Số giờ', compute='_compute_total_hours', store=True)
    camera_ids = fields.Many2many('camera.device', string="Camera giám sát")
    camera_count = fields.Integer(compute='_compute_camera_count')

    @api.depends('location_id')
    def _compute_camera_count(self):
        for rec in self:
            rec.camera_count = self.env['camera.device'].search_count([
                ('location_id', '=', rec.location_id.id)
            ])

    def action_open_camera(self):
        if self.camera_count == 0:
            raise UserError("Không có camera được gán cho vị trí huấn luyện này!")

        return {
            "type": "ir.actions.act_window",
            "name": "Danh mục camera",
            "res_model": "camera.device",
            "view_mode": "tree",
            "domain": [('location_id', '=', self.location_id.id)],
            "target": "new",
            'context': {
                'create': False,
                'delete': False,
            },
        }

    @api.depends('course_ids.total_hours')
    def _compute_total_hours(self):
        for rec in self:
            rec.total_hours = sum(line.total_hours for line in rec.course_ids)

    @api.constrains('start_date', 'end_date')
    def _check_start_date(self):
        for rec in self:
            if rec.start_date > rec.end_date:
                raise UserError('Ngày bắt đầu phải nhỏ hơn ngay kết thúc.')

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

    @api.model
    def action_open_training_chart(self):
        """Trả action để render biểu đồ"""
        data = self.env["training.plan"].get_training_state_summary()
        return {
            "type": "ir.actions.client",
            "tag": "training_bar_chart",
            "context": {"chart_data": data},
        }

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

    def action_print_word(self):
        return {
            "type": "ir.actions.act_window",
            "name": "Chọn phụ lục",
            "res_model": "print.word.wizard",
            "view_mode": "form",
            "target": "new",
        }
