from odoo import models, fields, api
from odoo.exceptions import UserError


class TrainingTime(models.Model):
    _name = 'training.time'
    _description = 'Thời gian huấn luyện'
    _rec_name = 'time_id'

    time_id = fields.Many2one('training.day', string='Ngày')
    start_time = fields.Float(
        string="Thời gian bắt đầu",
        required=True, default=7.0,
        help="Giờ bắt đầu huấn luyện (chọn giờ và phút)"
    )
    end_time = fields.Float(
        string="Thời gian kết thúc",
        required=True, default=11.5,
        help="Giờ kết thúc huấn luyện (chọn giờ và phút)"
    )
    duration_hours = fields.Float(
        string="Số giờ huấn luyện",
        compute="_compute_duration_hours",
        store=True,
        digits=(6, 2),
        readonly=True
    )

    start_time_str = fields.Char(string='Giờ bắt đầu', compute='_compute_time_str', store=True)
    end_time_str = fields.Char(string='Giờ kết thúc', compute='_compute_time_str', store=True)
    time_range = fields.Char(string='Khoảng thời gian', compute='_compute_time_str', store=True)

    @api.constrains('start_time', 'end_time')
    def _check_time_range(self):
        for rec in self:
            # start_time < 7
            if rec.start_time < 7.0:
                raise UserError("Giờ bắt đầu không được trước 07:00.")

            # end_time > 18
            if rec.end_time > 18.0:
                raise UserError("Giờ kết thúc không được sau 18:00.")

            # start_time >= end_time
            if rec.start_time >= rec.end_time:
                raise UserError("Giờ bắt đầu phải nhỏ hơn giờ kết thúc.")

    @api.depends('start_time', 'end_time')
    def _compute_time_str(self):
        for record in self:
            if record.start_time:
                hours = int(record.start_time)
                minutes = int((record.start_time - hours) * 60)
                record.start_time_str = f"{hours:02d}:{minutes:02d}"
            else:
                record.start_time_str = ""

            if record.end_time:
                hours = int(record.end_time)
                minutes = int((record.end_time - hours) * 60)
                record.end_time_str = f"{hours:02d}:{minutes:02d}"
            else:
                record.end_time_str = ""

            if record.start_time_str and record.end_time_str:
                record.time_range = f"{record.start_time_str} - {record.end_time_str}"
            else:
                record.time_range = ""

    @api.depends('start_time', 'end_time')
    def _compute_duration_hours(self):
        for rec in self:
            if rec.start_time and rec.end_time and rec.end_time > rec.start_time:
                rec.duration_hours = rec.end_time - rec.start_time
            else:
                rec.duration_hours = 0.0
