from odoo import models, fields, api
from odoo.exceptions import UserError
from datetime import date


class TrainingMission(models.Model):
    _name = 'training.mission'
    _inherit = ['mail.thread']
    _description = 'Bài huấn luyện'

    name = fields.Char(string="Tên bài học")
    description = fields.Text(string="Mô tả")
    total_hours = fields.Float(string='Số giờ', compute='_compute_total_hours', store=True)
    participants_ids = fields.Many2many('hr.department', string="Đối tượng tham gia")
    material_ids = fields.One2many('training.material', 'mission_id', string="Tài liệu / Video")
    course_id = fields.Many2one('training.course', ondelete='cascade')
    student_ids = fields.Many2many('hr.employee', string='Học viên', compute='_compute_student_ids', store=True)
    state = fields.Selection([
        ('draft', 'Dự thảo'),
        ('approved', 'Đã duyệt'),
    ], string='Trạng thái', default='draft')
    exclude_main_training = fields.Boolean(
        string="Không tính vào thời gian huấn luyện chính khóa",
        default=False
    )
    training_officer_ids_domain = fields.Binary(compute='_compute_training_officer_ids_domain')
    training_officer_ids = fields.Many2many(
        'hr.employee',
        'training_mission_rel',
        'mission_id',
        'employee_id',
        string='Giảng viên',
        required=True,
    )
    lesson_id = fields.Many2one('training.lesson', string="Tên bài học")
    day_ids = fields.One2many('training.day', 'mission_id', string='Thời gian huấn luyện', ondelete='cascade')
    camera_ids = fields.Many2many('camera.device', string="Camera giám sát")
    location_ids = fields.Many2many('training.location', string='Địa điểm')
    camera_count = fields.Integer(compute='_compute_camera_count')
    start_date = fields.Date(string="Thời gian bắt đầu")
    end_date = fields.Date(string="Thời gian kết thúc")
    percent_done = fields.Float(string="Tiến độ (%)", default=0.0)

    @api.model
    def cron_update_mission_progress(self):
        """Cập nhật % tiến độ theo thời gian của nhiệm vụ."""
        today = date.today()

        missions = self.search([
            ('state', '=', 'approved'),
            ('start_date', '<=', today),
        ])

        for mission in missions:
            start = mission.start_date
            end = mission.end_date

            # Tránh chia cho 0
            if start and end and start != end:
                total_range = (end - start).days
                passed_days = (today - start).days

                if passed_days < 0:
                    percent_done = 0
                else:
                    percent_done = min(100, round((passed_days / total_range) * 100, 2))
            else:
                percent_done = 100

            mission.sudo().write({
                'percent_done': percent_done
            })

    @api.model
    def get_list_mission(self):
        data = []
        missions = self.search([('state', '=', 'approved')])
        for mission in missions:
            data.append({
                'name': mission.name,
                'id': mission.id,
                'percent_done': mission.percent_done,
            })
        return data

    @api.constrains('start_date', 'end_date')
    def _check_start_date(self):
        if self.start_date > self.end_date:
            raise UserError('Ngày bắt đầu phải nhỏ hơn Ngày kết thúc!')

    @api.depends('camera_ids')
    def _compute_camera_count(self):
        for rec in self:
            rec.camera_count = len(rec.camera_ids)

    def action_open_camera(self):
        if self.camera_count == 0:
            raise UserError("Không có camera được gán cho vị trí huấn luyện này!")

        return {
            "type": "ir.actions.act_window",
            "name": "Danh mục camera",
            "res_model": "camera.device",
            "view_mode": "tree",
            "domain": [('id', '=', self.camera_ids.ids)],
            "target": "new",
            'context': {
                'create': False,
                'delete': False,
                'default_action': 'camera_device_view',
            },
        }

    @api.onchange('location_ids')
    def _onchange_location_ids(self):
        """Tự động điền danh sách camera thuộc các địa điểm đã chọn"""
        if not self.location_ids:
            self.camera_ids = [(5, 0, 0)]  # clear
            return

        cameras = self.env['camera.device'].search([
            ('location_id', 'in', self.location_ids.ids)
        ])

        self.camera_ids = [(6, 0, cameras.ids)]

    @api.depends('course_id.training_officer_ids', 'course_id')
    def _compute_training_officer_ids_domain(self):
        for rec in self:
            rec.training_officer_ids_domain = rec.course_id.training_officer_ids.ids

    @api.depends('course_id.student_ids')
    def _compute_student_ids(self):
        for rec in self:
            rec.student_ids = rec.course_id.student_ids

    def action_detail(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Danh sách nội dung huấn luyện',
            'res_model': 'training.mission',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'current',
        }

    @api.depends('day_ids.total_hours')
    def _compute_total_hours(self):
        for rec in self:
            rec.total_hours = sum(line.total_hours or 0.0 for line in rec.day_ids)
