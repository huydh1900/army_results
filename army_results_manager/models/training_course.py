from odoo import fields, models, api


class TrainingCourse(models.Model):
    _name = "training.course"
    _rec_name = 'name'
    _description = "Khóa huấn luyện"

    name = fields.Char(string="Tên khóa")
    block_ids = fields.One2many('training.course.block', 'course_id', string="Khối huấn luyện")
    department_id = fields.Many2one("hr.department", string="Đơn vị tổ chức")
    type = fields.Selection([
        ('si_quan', 'Sĩ quan'),
        ('phan_doi', 'Phân đội'),
    ], required=True, string='Đối tượng huấn luyện')
    type_training = fields.Selection([
        ('common', 'Huấn luyện chung'),
        ('private', 'Huấn luyện riêng'),
    ], default='common', string="Loại huấn luyện")
    phase_id = fields.Many2one("training.phase", string="Các giai đoạn")
    start_date = fields.Date(string="Bắt đầu huấn luyện")
    end_date = fields.Date(string="Kết thúc huấn luyện")
    year = fields.Integer(string='Năm')
    total_hours = fields.Float(string='Tổng số giờ')
    total_hours_type_common = fields.Float(compute='_compute_hours_types')
    total_hours_type_private = fields.Float(compute='_compute_hours_types')
    lesson_ids = fields.One2many('training.lesson', 'course_id')
    plan_id = fields.Many2one('training.plan')
    competition_id = fields.Many2one('training.competition', string='Hội thi')


    def _compute_hours_types(self):
        for rec in self:
            common_hours = sum(
                rec.phase_ids.mapped('content_ids')
                .filtered(lambda c: c.type == 'common')
                .mapped('total_hours')
            )
            private_hours = sum(
                rec.phase_ids.mapped('content_ids')
                .filtered(lambda c: c.type == 'private')
                .mapped('total_hours')
            )
            rec.total_hours_type_common = common_hours
            rec.total_hours_type_private = (rec.total_hours or 0) - common_hours


    @api.constrains('phase_ids')
    @api.onchange('phase_ids')
    def _constrain_phase_ids(self):
        for rec in self:
            rec.total_hours = sum(line.total_hours for line in rec.phase_ids)