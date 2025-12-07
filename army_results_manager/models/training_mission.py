from odoo import models, fields, api


class TrainingMission(models.Model):
    _name = 'training.mission'
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
        ('in_progress', 'Đang thực hiện'),
        ('done', 'Hoàn thành'),
        ('cancel', 'Hủy')
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

    def action_in_progress(self):
        self.sudo().write({'state': 'in_progress'})

    def action_done(self):
        self.sudo().write({'state': 'done'})

    def action_cancel(self):
        self.sudo().write({'state': 'cancel'})

    def action_reset_draft(self):
        self.sudo().write({'state': 'draft'})

