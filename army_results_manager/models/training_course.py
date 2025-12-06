from odoo import fields, models, api


class TrainingCourse(models.Model):
    _name = "training.course"
    _rec_name = 'name'
    _description = "Nội dung huấn luyện"

    name = fields.Char(string="Nội dung huấn luyện")
    subject_line_id = fields.Many2one('training.subject.line', string="Danh sách môn học")
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

    @api.model
    def get_list_course(self):
        data = []
        courses = self.search([('state', '=', 'approved')])
        for course in courses:
            total_mission = len(course.mission_ids)
            done_mission = len(course.mission_ids.filtered(lambda m: m.state == 'done'))
            percent_done = round((done_mission / total_mission) * 100, 2) if total_mission else 0

            data.append({
                'name': course.name,
                'id': course.id,
                'percent_done': percent_done,
            })
        return data

    def _compute_student_count(self):
        for rec in self:
            rec.student_count = len(rec.student_ids)

    def action_detail(self):
        self.ensure_one()
        if self.plan_id.state in ['approved','posted']:
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

    def write(self, vals):
        res = super().write(vals)
        if vals.get('student_ids') or vals.get('mission_ids'):
            self._sync_students_to_results()
        return res

    def _sync_students_to_results(self):
        """Đồng bộ học viên và kết quả huấn luyện (tối ưu cho số lượng lớn)."""
        Result = self.env['training.result']

        for rec in self:
            # Lấy danh sách ID học viên hiện tại
            current_ids = set(rec.student_ids.ids)

            # Lấy tất cả employee_id của result hiện có cho khóa này
            existing_results = Result.search([('training_course_id', '=', rec.id)])
            existing_ids = set(existing_results.mapped('employee_id.id'))

            # Xóa kết quả của học viên không còn trong danh sách
            remove_ids = existing_ids - current_ids
            if remove_ids:
                Result.search([
                    ('training_course_id', '=', rec.id),
                    ('employee_id', 'in', list(remove_ids))
                ]).unlink()

            # Thêm mới cho học viên chưa có
            add_ids = current_ids - existing_ids
            if add_ids:
                # Tạo danh sách dữ liệu hàng loạt
                vals_list = [
                    {'training_course_id': rec.id, 'employee_id': sid}
                    for sid in add_ids
                ]
                Result.create(vals_list)

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
