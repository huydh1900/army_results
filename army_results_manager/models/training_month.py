from odoo import models, fields, api
from datetime import date, timedelta
import calendar


class TrainingMonth(models.Model):
    _name = 'training.month'
    _rec_name = 'month'
    _description = 'Thời gian huấn luyện theo tháng'

    month = fields.Selection(
        [(str(i), f"Tháng {i}") for i in range(1, 13)],
        string="Tháng"
    )
    month_id = fields.Many2one('training.mission.line', string='Tên bài học')
    week_ids = fields.One2many('training.week', 'week_id', string='Thời gian huấn luyện theo tuần')
    total_hours = fields.Float(string='Số giờ')

    @api.constrains('week_ids')
    @api.onchange('week_ids')
    def _check_week_ids(self):
        for rec in self:
            if rec.week_ids:
                rec.total_hours = sum(line.total_hours for line in rec.week_ids)
            else:
                rec.total_hours = 0


class TrainingWeek(models.Model):
    _name = 'training.week'
    _rec_name = 'week'
    _description = 'Thời gian huấn luyện theo tuần'

    week_id = fields.Many2one('training.month', string='Tháng', readonly=True)
    week = fields.Selection(
        [(str(i), f"Tuần {i}") for i in range(1, 6)],
        string="Tuần"
    )
    total_hours = fields.Float(string='Số giờ')
    day_ids = fields.One2many('training.day', 'day_id', string='Thời gian huấn luyện theo ngày')

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
    ], string="Thứ", )

    @api.onchange('weekday')
    def _onchange_weekday(self):
        for rec in self:
            if rec.weekday and rec.day_id and rec.day_id.week_id:
                today = date.today()
                year = today.year
                month = int(rec.day_id.week_id.month)
                week_num = int(rec.day_id.week)
                weekday_map = {
                    '2': 0,  # Monday
                    '3': 1,
                    '4': 2,
                    '5': 3,
                    '6': 4,
                    '7': 5,
                    'cn': 6,  # Sunday
                }
                weekday_idx = weekday_map[rec.weekday]

                # Lấy ngày đầu tháng
                first_day = date(year, month, 1)
                # Tìm ngày đầu tiên đúng weekday trong tháng
                first_weekday = first_day + timedelta(
                    days=(weekday_idx - first_day.weekday() + 7) % 7
                )
                # Cộng thêm (week_num - 1) * 7 để ra tuần cần
                target_day = first_weekday + timedelta(weeks=week_num - 1)

                # Kiểm tra còn nằm trong tháng không
                last_day = date(year, month, calendar.monthrange(year, month)[1])
                if target_day <= last_day:
                    rec.day = target_day
                else:
                    rec.day = False
