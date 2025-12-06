from odoo import models, fields


class TrainingSubject(models.Model):
    _name = 'training.subject'
    _rec_name = 'name'
    _description = 'Chủ đề'

    name = fields.Char("Chủ đề", required=True)
    code = fields.Char("Mã chủ đề")
    type_training = fields.Selection([
        ('common_training', 'Huấn luyện chung'),
        ('private_training', 'Huấn luyện riêng'),
    ], string="Loại huấn luyện")
    line_ids = fields.One2many('training.subject.line', 'subject_id', string='Tên môn học')


class TrainingSubjectLine(models.Model):
    _name = 'training.subject.line'
    _rec_name = 'name'
    _description = 'Môn học'

    name = fields.Char("Tên môn học", required=True)
    code = fields.Char("Mã môn học")
    subject_id = fields.Many2one('training.subject', string="Chủ đề")
    lesson_ids = fields.One2many('training.lesson', 'subject_line_id', string='Tên bài học')

class TrainingLesson(models.Model):
    _name = 'training.lesson'
    _rec_name = 'name'
    _description = 'Bài học'

    code = fields.Char("Mã bài học")
    name = fields.Char(string='Tên bài học')
    type = fields.Selection([
        ('squad', 'Phân đội'),
        ('officer', 'Sĩ quan')
    ], string="Loại huấn luyện", required=True, default='squad')
    subject_line_id = fields.Many2one('training.subject.line', string='Tên môn học')
