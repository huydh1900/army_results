from odoo import api, fields, models, _

class TrainingPlanCourseLine(models.Model):
    _name = "training.plan.course.line"
    _description = "Line khóa huấn luyện trong kế hoạch"

    plan_id = fields.Many2one('training.plan', string="Kế hoạch")
    course_id = fields.Many2one('training.course', string="Khóa huấn luyện")
    year = fields.Integer(string="Năm", related='course_id.year')
    total_hours = fields.Float(string="Số giờ dự kiến", related='course_id.total_hours')

