from odoo import fields, models, api


class TrainingCourse(models.Model):
    _name = "training.course"
    _description = "Nội dung huấn luyện"

    subject_line_id = fields.Many2one('training.subject.line', string="Môn học")
    total_hours = fields.Float(string='Tổng số giờ', compute='_compute_total_hours', store=True)
    plan_id = fields.Many2one('training.plan', ondelete='cascade')
    mission_ids = fields.One2many('training.mission', 'course_id', string='Danh sách nội dung huấn luyện')
    student_count = fields.Integer(
        string='Số học viên',
        compute='_compute_student_count'
    )
    state = fields.Selection([
        ('draft', 'Soạn thảo'),
        ('approved', 'Đã duyệt'),
    ], string="Trạng thái", default="draft")
    participants_ids = fields.Many2many('hr.department', string="Đối tượng tham gia")
    participant_category_id = fields.Many2one('training.category', string='Thành phần tham gia')
    responsible_level_id = fields.Many2one('training.category', string='Cấp phụ trách')
    measure = fields.Char(string="Biện pháp tiến hành")
    year = fields.Char(related='plan_id.year', store=True)
    is_common = fields.Boolean('Là môn chung', default=False)
    student_ids = fields.Many2many(
        'hr.employee',
        'course_id',
        'employee_id',
        'training_course_student_rel',
        string='Học viên',
        domain="[('role', '=', 'student')]",
        compute='_compute_student_ids',
        inverse='_inverse_student_ids',
        store=True,
    )
    training_officer_ids = fields.Many2many(
        'hr.employee',
        'training_course_officer_rel',
        'course_id',
        'employee_id',
        required=True,
        string='Cán bộ phụ trách huấn luyện',
        domain="[('role', '=', 'training_officer')]")

    approver_id = fields.Many2one('hr.employee', related='plan_id.approver_id', store=True)
    type = fields.Selection([
        ('squad', 'Phân đội'),
        ('officer', 'Sĩ quan')
    ], string="Loại huấn luyện", required=True, default="squad"
    )
    attachment_ids = fields.Many2many(
        'ir.attachment',
        string='Tài liệu mẫu',
    )

    def name_get(self):
        result = []
        for rec in self:
            name = rec.subject_line_id.name or "(Không có môn)"
            result.append((rec.id, name))
        return result

    @api.onchange('type')
    @api.constrains('type')
    def onchange_type(self):
        for rec in self:
            # Tìm các bài học phù hợp type + môn
            lessons = self.env['training.lesson'].search([
                ('type', '=', rec.type),
                ('subject_line_id', '=', rec.subject_line_id.id)
            ])
            # # Xóa danh sách mission cũ
            rec.mission_ids = [(5, 0, 0)]
            subject_attachments = self.env['ir.attachment'].search([
                ('res_model', '=', 'training.subject.line'),
                ('res_id', '=', self.subject_line_id.id),
            ])

            rec.attachment_ids = [(6, 0, subject_attachments.ids)]

            # Tạo danh sách mission mới
            missions_vals = []
            for lesson in lessons:
                # Lấy tất cả attachment của lesson

                # Chuẩn bị dữ liệu mission
                missions_vals.append(
                    (0, 0, {
                        'name': lesson.name,
                        'lesson_id': lesson.id,
                    })
                )

            # Gán vào mission_ids
            rec.mission_ids = missions_vals

    @api.depends('is_common', 'plan_id.student_ids')
    def _compute_student_ids(self):
        for rec in self:
            if rec.is_common and rec.plan_id:
                # Môn chung: lấy từ kế hoạch
                rec.student_ids = rec.plan_id.student_ids
            else:
                # Môn riêng: giữ nguyên dữ liệu đã nhập
                rec.student_ids = rec.student_ids

    def _inverse_student_ids(self):
        """Cho phép chỉnh sửa student_ids nếu không phải môn chung."""
        for rec in self:
            if not rec.is_common:
                pass  # cho phép lưu như bình thường

    def action_open_result_training(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Kết quả huấn luyện',
            'res_model': 'training.result',
            'view_mode': 'tree,form',
            'domain': [('employee_id', 'in', self.student_ids.ids), ('training_course_id', '=', self.id)],
            'target': 'current',
        }

    @api.depends('mission_ids', 'mission_ids.total_hours')
    def _compute_total_hours(self):
        for rec in self:
            if rec.mission_ids:
                rec.total_hours = sum(
                    line.total_hours or 0.0 for line in rec.mission_ids if not line.exclude_main_training)
            else:
                rec.total_hours = 0

    def _compute_student_count(self):
        for rec in self:
            rec.student_count = len(rec.student_ids)

    def action_detail(self):
        self.ensure_one()
        if self.plan_id.state in ['approved', 'posted']:
            context = {'edit': False}
        else:
            context = {'edit': True}

        return {
            'type': 'ir.actions.act_window',
            'name': 'Khóa huấn luyện',
            'res_model': 'training.course',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'current',
            'context': context,
        }

    def action_open_students(self):
        """Mở danh sách học viên của khóa huấn luyện"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Học viên',
            'res_model': 'hr.employee',
            'view_mode': 'tree,form',
            'domain': [
                ('id', 'in', self.student_ids.ids),
            ],
            'context': {
                'create': False,
                'delete': False,
            },
            'target': 'current',
        }
