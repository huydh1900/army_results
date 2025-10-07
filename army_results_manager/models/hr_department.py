# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class Department(models.Model):
    _inherit = ['hr.department']

    commanding_officer_count = fields.Integer(
        string="Số CB chỉ huy", compute='_compute_employee_counts')
    training_officer_count = fields.Integer(
        string="Số CB phụ trách huấn luyện", compute="_compute_employee_counts")
    student_count = fields.Integer(
        string="Số học viên theo khóa", compute="_compute_employee_counts")
    training_course_count = fields.Integer(
        string="Số khóa huấn luyện", compute="_compute_training_course_counts")
    document_count = fields.Integer(string="Số tài liệu", compute="_compute_document_count")
    province_id = fields.Many2one(
        'res.country.state',
        string="Địa điểm",
        domain="[('country_id', '=', 241)]"
    )

    def _compute_training_course_counts(self):
        course_data = self.env['training.course'].read_group(
            domain=[('participants_ids', 'in', self.ids)],
            fields=['participants_ids'],
            groupby=['participants_ids']
        )
        count_map = {data['participants_ids'][0]: data['participants_ids_count'] for data in course_data}
        for rec in self:
            rec.training_course_count = count_map.get(rec.id, 0)

    def action_view_training_course(self):
        self.ensure_one()
        return {
            'name': 'Khóa huấn luyện',
            'type': 'ir.actions.act_window',
            'res_model': 'training.course',
            'view_mode': 'tree,form',
            'views': [(self.env.ref('army_results_manager.view_training_course_tree').id, 'tree'),
                      (self.env.ref('army_results_manager.view_training_course_form').id, 'form')],
            'domain': [('participants_ids', 'in', self.id)],
        }

    def _compute_employee_counts(self):
        for rec in self:
            rec.commanding_officer_count = self.env['hr.employee'].search_count([
                ('role', '=', 'commanding_officer'),
                ('department_id', '=', self.id)
            ])
            rec.training_officer_count = self.env['hr.employee'].search_count([
                ('role', '=', 'training_officer'),
                ('department_id', '=', self.id)
            ])
            rec.student_count = self.env['hr.employee'].search_count([
                ('role', '=', 'student'),
                ('department_id', '=', self.id)
            ])

    def action_view_commanding_officer(self):
        return {
            'name': 'Cán bộ chỉ huy',
            'type': 'ir.actions.act_window',
            'res_model': 'hr.employee',
            'view_mode': 'tree,form',
            'views': [
                (self.env.ref('hr.view_employee_tree').id, 'tree'),
                (self.env.ref('hr.view_employee_form').id, 'form')
            ],
            'domain': [
                ('role', '=', 'commanding_officer'),
                ('department_id', '=', self.id)
            ],
            'context': {
                'default_role': 'commanding_officer',
                'default_department_id': self.id
            },
        }

    def action_view_training_officer(self):
        return {
            'name': 'Cán bộ Phụ trách Huấn luyện',
            'type': 'ir.actions.act_window',
            'res_model': 'hr.employee',
            'view_mode': 'tree,form',
            'views': [
                (self.env.ref('hr.view_employee_tree').id, 'tree'),
                (self.env.ref('hr.view_employee_form').id, 'form')
            ],
            'domain': [
                ('role', '=', 'training_officer'),
                ('department_id', '=', self.id)
            ],
            'context': {
                'default_role': 'training_officer',
                'default_department_id': self.id
            },
        }

    def action_view_student(self):
        return {
            'name': 'Học viên',
            'type': 'ir.actions.act_window',
            'res_model': 'hr.employee',
            'view_mode': 'tree,form',
            'views': [(self.env.ref('hr.view_employee_tree').id, 'tree'),
                      (self.env.ref('hr.view_employee_form').id, 'form')],
            'domain': [('role', '=', 'student'), ('department_id', '=', self.id), ]
        }
