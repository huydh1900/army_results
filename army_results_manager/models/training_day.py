from odoo.exceptions import UserError
from odoo import models, fields, api


class TrainingDay(models.Model):
    _name = 'training.day'
    _description = 'Thời gian huấn luyện theo tháng'
    _order = 'day asc'

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
    state = fields.Selection([
        ('draft', 'Soạn thảo'),
        ('to_modify', 'Cần chỉnh sửa'),
        ('posted', 'Chờ duyệt'),
        ('approved', 'Đã duyệt'),
        ('cancel', 'Hủy'),
    ], string="Trạng thái", default="draft", tracking=True)
    mission_id = fields.Many2one(related='mission_line_id.mission_id', store=True)
    mission_name = fields.Char(related='mission_id.name', store=True)
    lesson_name = fields.Char(related='mission_line_id.name', store=True)
    course_id = fields.Many2one(related='mission_line_id.mission_id.course_id', store=True)
    course_name = fields.Char(related='course_id.name', store=True)
    subject_code = fields.Char(related='mission_line_id.mission_id.subject_id.code', store=True)
    type_training = fields.Selection(related='mission_line_id.mission_id.subject_id.type_training', store=True)
    weekday = fields.Char(string="Thứ", compute='_compute_name', store=True)
    total_hours = fields.Float(string='Số giờ', compute='_compute_total_hours', store=True, group_operator=False)
    plan_id = fields.Many2one(
        'training.plan',
        related='mission_line_id.mission_id.course_id.plan_id',
        store=True
    )
    plan_name = fields.Char(related='plan_id.name', store=True)
    type_plan = fields.Selection(related='plan_id.type', store=True)
    training_officer_ids = fields.Many2many(
        'hr.employee',
        'training_day_rel',
        'day_id',
        'employee_id',
        string='Giảng viên',
        related='mission_line_id.training_officer_ids',
    )
    reason_modify = fields.Text(string='Lý do chỉnh sửa')
    approver_id = fields.Many2one(related='plan_id.approver_id', store=True)
    attachment_id = fields.Many2one('ir.attachment', string="Tài liệu PDF", domain=[('mimetype', '=', 'application/pdf')],required=True, ondelete='cascade')
    datas = fields.Binary(related='attachment_id.datas', readonly=False)

    def action_open_modify_wizard(self):
        return {
            "type": "ir.actions.act_window",
            "name": "Nhập lý do chỉnh sửa",
            "res_model": "modify.reason.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"active_id": self.id},
        }

    @api.model
    def action_sign_report(self, domain):
        records = self.search(domain)
        print(records)
        # if records:
        #     pdf = records[0].attachment_ids[0]
        #     print(pdf.id)
        #
        # #  Tìm template gắn với attachment
        #     template = self.env['sign.template'].search([
        #         ('attachment_id', '=', pdf.id + 1)
        #     ], limit=1)
        #
        #     if not template:
        #         raise UserError("Template ký chưa được tạo. Hãy bấm 'Tạo mẫu ký' trước!")
        #
        #     request = self.env['sign.send.request'].create({
        #         'template_id': template.id,
        #         'filename': template.attachment_id.name,
        #         'subject': f"Ký báo cáo {self.display_name}",
        #         'signer_id': self.approver_id.id,
        #     })
        #
        #     return request.sign_directly()



    @api.model
    def action_approve_by_domain(self, domain):
        """Duyệt tất cả bản ghi trong domain và tự động cập nhật plan nếu toàn bộ ngày đã duyệt."""
        records = self.search(domain)
        if not records:
            return

        records.write({'state': 'approved'})

        # Tạo nhận xét cho tất cả học viên theo ngày
        comment_vals = []
        for rec in records:
            for student in rec.student_ids:
                # 1. Lấy hoặc tạo TrainingResult cho học viên trong khóa đó
                result = self.env['training.result'].search([
                    ('employee_id', '=', student.id),
                    ('training_course_id', '=', rec.mission_line_id.mission_id.course_id.id)
                ], limit=1)

                if not result:
                    result = self.env['training.result'].create({
                        'employee_id': student.id,
                        'training_course_id': rec.mission_line_id.mission_id.course_id.id,
                    })
                comment_vals.append({
                    'day_id': rec.id,
                    'day_date': rec.day.strftime('%d-%m-%Y'),
                    'result_id': result.id,
                    'student_id': student.id,
                    'mission_name': rec.mission_name,
                    'lesson_name': rec.lesson_name,
                    'year': rec.year,
                })

        if comment_vals:
            self.env['training.day.comment'].create(comment_vals)

        # Lấy tất cả plan_id liên quan
        plan_ids = records.mapped('plan_id').filtered(lambda p: p)

        for plan in plan_ids:
            # Lấy toàn bộ ngày thuộc plan đó
            all_days = self.search([('plan_id', '=', plan.id)])
            # Lấy những ngày đã duyệt
            approved_days = all_days.filtered(lambda d: d.state == 'approved')

            # Nếu tất cả ngày đã duyệt → cập nhật plan
            if len(all_days) == len(approved_days):
                plan.write({'state': 'approved'})

    @api.depends('month', 'week', 'mission_line_id', 'day')
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
    _rec_name = 'student_id'
    _description = 'Nhận xét học viên theo ngày'

    day_id = fields.Many2one('training.day', string='Ngày huấn luyện', ondelete='cascade')
    student_id = fields.Many2one('hr.employee', string="Học viên", required=True)
    comment = fields.Text(string='Nhận xét', compute='_compute_comment', store=True)
    day_date = fields.Char(string='Ngày')
    result_id = fields.Many2one('training.result', ondelete='cascade')
    course_name = fields.Char(related='day_id.mission_line_id.mission_id.course_id.name', store=True)
    mission_name = fields.Char()
    lesson_name = fields.Char(string='Tên bài học')
    year = fields.Char()
    score = fields.Char(string="Điểm số")
    strength = fields.Text(string='Điểm mạnh')
    weakness = fields.Text(string='Điểm yếu')
    video = fields.Binary(string="Video", attachment=True)

    @api.depends('strength', 'weakness')
    def _compute_comment(self):
        for rec in self:
            parts = []
            if rec.strength:
                parts.append(rec.strength.strip())
            if rec.weakness:
                parts.append(rec.weakness.strip())
            rec.comment = '\n'.join(parts) if parts else ''

    def action_open_comment(self):
        """Mở form nhận xét học viên."""
        self.ensure_one()
        view_id = self.env.ref('army_results_manager.view_training_day_comment_form').id

        return {
            'type': 'ir.actions.act_window',
            'name': 'Nhận xét học viên',
            'res_model': 'training.day.comment',
            'view_mode': 'form',
            'view_id': view_id,
            'res_id': self.id,
            'target': 'new',
            'context': {'default_student_id': self.student_id.id},
        }
