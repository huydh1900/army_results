from odoo import models, fields, api


class TrainingSubject(models.Model):
    _name = 'training.subject'
    _rec_name = 'name'
    _description = 'Chuyên đề'

    name = fields.Char("Chuyên đề", required=True)
    code = fields.Char("Mã chủ đề")
    type_training = fields.Selection([
        ('common_training', 'Huấn luyện chung'),
        ('private_training', 'Huấn luyện riêng'),
    ], string="Loại huấn luyện", readonly=True)
    line_ids = fields.One2many('training.subject.line', 'subject_id', string='Tên môn học')


class TrainingSubjectLine(models.Model):
    _name = 'training.subject.line'
    _rec_name = 'name'
    _description = 'Môn học'

    name = fields.Char("Tên môn học", required=True)
    code = fields.Char("Mã môn học")
    subject_id = fields.Many2one('training.subject', string="Chủ đề")
    lesson_ids = fields.One2many('training.lesson', 'subject_line_id', string='Tên bài học')
    type_training = fields.Selection(related='subject_id.type_training', store=True, string="Loại huấn luyện")
    stage_ids = fields.One2many('training.stage', 'subject_line_id', string="Giai đoạn")
    attachment_ids = fields.Many2many(
        'ir.attachment',
        string='Tài liệu, bài tập huấn luyện mẫu',
    )

    def write(self, vals):
        if 'attachment_ids' in vals:
            # Lấy danh sách attachment hiện tại
            old_attachments = self.attachment_ids
            # Lấy id attachment mới (nếu là command 6)
            new_ids = set()
            for cmd in vals['attachment_ids']:
                if isinstance(cmd, (list, tuple)) and cmd[0] == 6:
                    new_ids = set(cmd[2])

            # Những attachment nào cũ không còn trong danh sách mới -> xóa
            to_unlink = old_attachments.filtered(lambda att: att.id not in new_ids)
            if to_unlink:
                to_unlink.unlink()
        return super().write(vals)

    @api.onchange('stage_ids')
    def _onchange_stage_ids(self):
        if self.stage_ids:
            # Lấy tất cả lesson_ids từ các stage
            lesson_records = self.stage_ids.mapped('lesson_ids')

            # Gán lại vào lesson_ids trên subject_line
            self.lesson_ids = [(6, 0, lesson_records.ids)]
        else:
            # Nếu xóa hết stage → xóa luôn lesson_ids
            self.lesson_ids = [(5, 0, 0)]


class TrainingLesson(models.Model):
    _name = 'training.lesson'
    _rec_name = 'name'
    _description = 'Bài học'

    code = fields.Char("Mã bài học")
    name = fields.Text(string='Tên nhiệm vụ (Bài học)')
    type = fields.Selection([
        ('squad', 'Phân đội'),
        ('officer', 'Sĩ quan')
    ], string="Loại huấn luyện", required=True, default='squad')
    subject_line_id = fields.Many2one('training.subject.line', string='Tên môn học')
    type_training = fields.Selection(related='subject_line_id.type_training', store=True, string="Loại huấn luyện")
    stage_id = fields.Many2one('training.stage', string='Giai đoạn')
    resource_ids = fields.One2many('training.resource', 'lesson_id')


class TrainingStage(models.Model):
    _name = 'training.stage'
    _rec_name = 'display_name'
    _description = 'Giai đoạn huấn luyện'

    name = fields.Selection([
        ('gd_1', 'Giai đoạn 1: Huấn luyện cơ bản'),
        ('gd_2', 'Giai đoạn 2: Huấn luyện phân đoạn'),
        ('gd_3', 'Giai đoạn 3: Huấn luyện tổng hợp, nâng cao'),
        ('gd_4', 'Giai đoạn 4: Huấn luyện theo chiến thuật thi đấu'),
        ('gd_5', 'Giai đoạn 5: Thi đấu'),
    ], string="Giai đoạn")
    subject_line_id = fields.Many2one('training.subject.line', string='Môn học')
    lesson_ids = fields.One2many('training.lesson', 'stage_id', string='Tên bài học')
    display_name = fields.Char(
        compute='_compute_display_name',
        store=False
    )

    @api.depends('name', 'subject_line_id.name')
    def _compute_display_name(self):
        for rec in self:
            # Lấy danh sách selection
            selection_list = rec._fields['name'].selection

            # Tìm label tương ứng với value
            stage_label = dict(selection_list).get(rec.name, '')

            # Lấy tên môn học
            subject_name = rec.subject_line_id.name or ''

            # Ghép chuỗi theo yêu cầu
            if stage_label and subject_name:
                rec.display_name = f"{stage_label} - {subject_name}"
            else:
                rec.display_name = stage_label or subject_name
