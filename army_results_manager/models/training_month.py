from odoo import models, fields, api
from datetime import date, timedelta
from datetime import datetime

from odoo16.odoo16.odoo.exceptions import UserError


class TrainingMonth(models.Model):
    _name = 'training.month'
    _description = 'Thời gian huấn luyện theo tháng'

    month = fields.Selection(
        [(str(i), f"Tháng {i}") for i in range(1, 13)],
        string="Tháng", required=True,
    )
    month_id = fields.Many2one('training.mission.line', string='Tên bài học')
    week_ids = fields.One2many('training.week', 'week_id', string='Thời gian huấn luyện theo tuần')
    total_hours = fields.Float(string='Số giờ')
    student_ids = fields.Many2many('hr.employee', string='Học viên', compute='_compute_student_ids', store=True)

    @api.depends('month_id.student_ids')
    def _compute_student_ids(self):
        for rec in self:
            rec.student_ids = rec.month_id.student_ids

    def name_get(self):
        result = []
        for record in self:
            name = dict(self._fields['month'].selection).get(record.month, record.month)
            result.append((record.id, name))
        return result

    @api.constrains('week_ids')
    @api.onchange('week_ids')
    def _check_week_ids(self):
        for rec in self:
            if rec.week_ids:
                rec.total_hours = sum(line.total_hours for line in rec.week_ids)
            else:
                rec.total_hours = 0

    def action_detail(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Theo tháng',
            'res_model': 'training.month',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'current',
        }


class TrainingWeek(models.Model):
    _name = 'training.week'
    _description = 'Thời gian huấn luyện theo tuần'

    week_id = fields.Many2one('training.month', string='Tháng', readonly=True)
    week = fields.Selection(
        [(str(i), f"Tuần {i}") for i in range(1, 6)],
        string="Tuần", required=True,
    )
    total_hours = fields.Float(string='Số giờ')
    day_ids = fields.One2many('training.day', 'day_id', string='Thời gian huấn luyện theo ngày')
    student_ids = fields.Many2many('hr.employee', string='Học viên', compute='_compute_student_ids', store=True)
    month_id_name = fields.Char(string="Tên bài học", related='week_id.month_id.name',store=True)

    @api.depends('week_id.student_ids')
    def _compute_student_ids(self):
        for rec in self:
            rec.student_ids = rec.week_id.student_ids

    def name_get(self):
        result = []
        for record in self:
            name = dict(self._fields['week'].selection).get(record.week, record.week)
            result.append((record.id, name))
        return result

    def action_detail(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Theo tuần',
            'res_model': 'training.week',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'current',
        }

    @api.constrains('day_ids')
    @api.onchange('day_ids')
    def _check_day_ids(self):
        for rec in self:
            if rec.day_ids:
                rec.total_hours = sum(line.total_hours for line in rec.day_ids)
            else:
                rec.total_hours = 0


class TrainingDay(models.Model):
    _name = 'training.day'
    _description = 'Thời gian huấn luyện theo ngày'

    day_id = fields.Many2one('training.week', string='Tuần', readonly=True)
    day = fields.Date(string="Ngày")
    total_hours = fields.Float(string='Số giờ')
    weekday = fields.Selection([
        ('2', 'Thứ 2'),
        ('3', 'Thứ 3'),
        ('4', 'Thứ 4'),
        ('5', 'Thứ 5'),
        ('6', 'Thứ 6'),
        ('7', 'Thứ 7'),
        ('cn', 'Chủ nhật'),
    ], string="Thứ", required=True)
    student_ids = fields.Many2many('hr.employee', string='Học viên', compute='_compute_student_ids', store=True)
    line_ids = fields.One2many('training.day.line', 'day_id', string='Chi tiết kết quả')
    day_id_name = fields.Char(string="Tên bài học", related='day_id.month_id_name',store=True)

    @api.model
    def create(self, vals):
        record = super().create(vals)
        if record.day and record.student_ids:
            for student in record.day_id.student_ids:
                self.env['training.day.line'].create({
                    'day_id': record.id,
                    'employee_id': student.id,
                })
        return record

    @api.depends('day_id')
    def _compute_student_ids(self):
        for rec in self:
            rec.student_ids = rec.day_id.student_ids

    @api.onchange('weekday')
    def _onchange_weekday(self):
        weekday_map = {
            '2': 0,  # Monday
            '3': 1,
            '4': 2,
            '5': 3,
            '6': 4,
            '7': 5,
            'cn': 6,  # Sunday
        }

        for rec in self:
            week_id = rec.day_id.week_id if rec.day_id else False
            if not (rec.weekday and rec.day_id and week_id):
                rec.day = False
                continue

            try:
                year = date.today().year
                iso_week_num = int(rec.day_id.week)  # Tuần ISO
                weekday_idx = weekday_map.get(rec.weekday)
                if weekday_idx is None:
                    rec.day = False
                    continue

                # === Tìm ngày Thứ Hai của tuần ISO ===
                # ISO week 1 của năm có thể bắt đầu từ tháng trước
                first_week_monday = date.fromisocalendar(year, iso_week_num, 1)
                target_day = date.fromisocalendar(year, iso_week_num, weekday_idx + 1)

                # === Kiểm tra hợp lệ ===
                start_week = first_week_monday
                end_week = start_week + timedelta(days=6)

                if not (start_week <= target_day <= end_week):
                    raise UserError(
                        f"Thứ bạn chọn không nằm trong tuần {iso_week_num} của năm {year}.\n"
                        f"Tuần này bắt đầu từ {start_week.strftime('%d/%m/%Y')} "
                        f"đến {end_week.strftime('%d/%m/%Y')}."
                    )

                rec.day = target_day

            except ValueError:
                # Nếu tuần vượt ngoài phạm vi ISO hợp lệ (1–52 hoặc 53)
                raise UserError(
                    f"Tuần {rec.day_id.week} không hợp lệ cho năm {year}."
                )
            except UserError:
                raise
            except Exception:
                rec.day = False

class TrainingDayLine(models.Model):
    _name = 'training.day.line'
    _description = 'Kết quả huấn luyện trong ngày'

    day_id = fields.Many2one('training.day', string='Ngày huấn luyện', ondelete='cascade')
    employee_id = fields.Many2one('hr.employee', string='Học viên', required=True)
    note = fields.Char(string='Nhận xét')
    day_date = fields.Date(related='day_id.day', store=True, string='Ngày')
    day_date_char = fields.Char(string='Ngày', compute='_compute_day_date_char', store=True)
    day_id_name = fields.Char(string="Tên bài học", related='day_id.day_id_name',store=True)

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

