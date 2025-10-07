from odoo import models, fields, api


class TrainingMission(models.Model):
    _name = 'training.mission'
    _description = 'Nhiệm vụ huấn luyện'

    name = fields.Char(string="Tên nhiệm vụ", required=True)
    description = fields.Text(string="Mô tả nhiệm vụ")
    total_hours = fields.Float(string='Số giờ', compute='_compute_total_hours', store=True)
    start_date = fields.Date(string="Thời gian bắt đầu")
    end_date = fields.Date(string="Thời gian kết thúc")
    participants_ids = fields.Many2many('hr.department', string="Đối tượng tham gia")
    material_ids = fields.One2many('training.material', 'mission_id', string="Tài liệu / Video")
    course_id = fields.Many2one('training.course')
    student_ids = fields.Many2many('hr.employee', string='Học viên')
    state = fields.Selection([
        ('draft', 'Dự thảo'),
        ('in_progress', 'Đang thực hiện'),
        ('done', 'Hoàn thành'),
        ('cancel', 'Hủy')
    ], string='Trạng thái', default='draft')
    mission_line_ids = fields.One2many('training.mission.line', 'mission_id', string='Chi tiết nhiệm vụ huấn luyện')
    exclude_main_training = fields.Boolean(
        string="Không tính vào thời gian huấn luyện chính khóa",
        default=False
    )
    type_training = fields.Selection([
        ('common_training', 'Huấn luyện chung'),
        ('private_training', 'Huấn luyện riêng'),
    ], string="Loại huấn luyện")
    subject_id = fields.Many2one('training.subject', string="Môn học")

    @api.depends('mission_line_ids.total_hours')
    def _compute_total_hours(self):
        for rec in self:
            rec.total_hours = sum(line.total_hours for line in rec.mission_line_ids)

    def action_in_progress(self):
        self.write({'state': 'in_progress'})

    def action_done(self):
        self.write({'state': 'done'})

    def action_cancel(self):
        self.write({'state': 'cancel'})

    def action_reset_draft(self):
        self.write({'state': 'draft'})


class TrainingMissionLine(models.Model):
    _name = 'training.mission.line'
    _description = 'Chi tiết nhiệm vụ huấn luyện'

    mission_id = fields.Many2one('training.mission', string='Nhiệm vụ', readonly=True)
    name = fields.Char(string="Tên bài học", required=True)
    total_hours = fields.Float(string='Số giờ')
    start_date = fields.Date(string="Thời gian bắt đầu")
    end_date = fields.Date(string="Thời gian kết thúc")
    month_ids = fields.One2many('training.month', 'month_id', string='Thời gian huấn luyện theo tháng')

    @api.constrains('month_ids', 'month_ids.total_hours')
    @api.onchange('month_ids')
    def _check_month_ids(self):
        for rec in self:
            if rec.month_ids:
                rec.total_hours = sum(line.total_hours for line in rec.month_ids)
            else:
                rec.total_hours = 0

