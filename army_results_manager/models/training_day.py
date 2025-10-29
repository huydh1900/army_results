from odoo import models, fields, api
from datetime import datetime


class TrainingDay(models.Model):
    _name = 'training.day'
    _description = 'Thời gian huấn luyện theo tháng'

    time_ids = fields.One2many('training.time', 'time_id')
    comment_ids = fields.One2many('training.day.comment', 'day_id', string="Nhận xét học viên")

    mission_line_id = fields.Many2one('training.mission.line', string='Nhiệm vụ huấn luyện')

    student_ids = fields.Many2many('hr.employee', string='Học viên', compute='_compute_student_ids', store=True)

    month = fields.Integer(string="Tháng", readonly=True)
    day = fields.Date(string="Ngày")
    week = fields.Integer(string="Tuần", readonly=True)
    year = fields.Char(related='mission_line_id.mission_id.course_id.year', store=True)
    month_name = fields.Char(string="Tên tháng", compute='_compute_name', store=True)
    week_name = fields.Char(string="Tên tuần", compute='_compute_name', store=True)
    day_name = fields.Char(string="Tên ngày", compute='_compute_name', store=True)
    mission_name = fields.Char(related='mission_line_id.mission_id.name', store=True)
    lesson_name = fields.Char(related='mission_line_id.name', store=True)
    plan_name = fields.Char(related='mission_line_id.mission_id.course_id.plan_id.name', store=True)
    subject_code = fields.Char(related='mission_line_id.mission_id.subject_id.code', store=True)
    weekday = fields.Char(string="Thứ", compute='_compute_name', store=True)
    total_hours = fields.Float(string='Số giờ', compute='_compute_total_hours', store=True)

    @api.model
    def create(self, vals):
        record = super(TrainingDay, self).create(vals)
        # Khi tạo xong training.day, tự sinh nhận xét cho học viên
        if record.student_ids:
            comments = [
                {
                    'day_id': record.id,
                    'student_id': student.id,
                    'mission_name': record.mission_name,
                    'lesson_name': record.lesson_name,
                    'year': record.year,
                }
                for student in record.student_ids
            ]
            self.env['training.day.comment'].create(comments)
        return record

    @api.depends('month', 'week')
    def _compute_name(self):
        weekday_map = {
            0: 'Thứ Hai',
            1: 'Thứ Ba',
            2: 'Thứ Tư',
            3: 'Thứ Năm',
            4: 'Thứ Sáu',
            5: 'Thứ Bảy',
            6: 'Chủ Nhật',
        }
        for rec in self:
            rec.month_name = f"Tháng {rec.month}" if rec.month else ''
            rec.week_name = f"Tuần {rec.week}" if rec.week else ''
            rec.day_name = rec.day.strftime('%d-%m-%Y') if rec.day else ''
            rec.weekday = weekday_map[rec.day.weekday()] if rec.day else ''

    def name_get(self):
        result = []
        for rec in self:
            if rec.day:
                # Format lại ngày theo kiểu DD-MM-YYYY
                name = rec.day.strftime('%d-%m-%Y')
            else:
                name = "Không có ngày"
            result.append((rec.id, name))
        return result

    @api.depends('time_ids.duration_hours')
    def _compute_total_hours(self):
        for rec in self:
            rec.total_hours = sum(line.duration_hours or 0.0 for line in rec.time_ids)

    @api.onchange('day')
    def _onchange_day(self):
        """Tự động cập nhật tháng và tuần khi chọn ngày"""
        if self.day:
            # Lấy tháng dạng số nguyên (1–12)
            self.month = self.day.month

            # Tính tuần trong tháng
            first_day_of_month = self.day.replace(day=1)
            days_diff = (self.day - first_day_of_month).days
            self.week = (days_diff // 7) + 1
        else:
            self.month = False
            self.week = False

    @api.depends('mission_line_id.student_ids')
    def _compute_student_ids(self):
        for rec in self:
            rec.student_ids = rec.mission_line_id.student_ids

    def action_detail(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Theo tháng',
            'res_model': 'training.day',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'current',
        }


class TrainingDayComment(models.Model):
    _name = 'training.day.comment'
    _description = 'Nhận xét học viên theo ngày'

    day_id = fields.Many2one('training.day', string='Ngày huấn luyện', ondelete='cascade')
    student_id = fields.Many2one('hr.employee', string="Học viên", required=True)
    comment = fields.Text(string='Nhận xét')
    day_date = fields.Date(related='day_id.day', store=True, string='Ngày')
    day_date_char = fields.Char(string='Ngày', compute='_compute_day_date_char', store=True)
    course_name = fields.Char(related='day_id.mission_line_id.mission_id.course_id.name', store=True)
    mission_name = fields.Char()
    lesson_name = fields.Char()
    year = fields.Char()

    @api.depends('day_date')
    def _compute_day_date_char(self):
        for rec in self:
            if rec.day_date:
                rec.day_date_char = rec.day_date.strftime("%d/%m/%Y")
            else:
                rec.day_date_vn = ''

    @api.depends('day_id.day', 'employee_id.name')
    def name_get(self):
        result = []
        for rec in self:
            vn_date = ''
            if rec.day_id.day:
                vn_date = datetime.strftime(rec.day_id.day, "%d-%m-%Y")
            name = f"{vn_date} - {rec.employee_id.name or ''}"
            result.append((rec.id, name))
        return result
