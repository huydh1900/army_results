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
    training_course_ids = fields.Many2many(
        'training.course',
        'training_course_department_rel',
        'department_id',
        'course_id',
        string="Kế hoạch huấn luyện"
    )
    document_count = fields.Integer(string="Số tài liệu", compute="_compute_document_count")
    subject_ids = fields.Many2many(
        "training.subject",
        string="Môn học"
    )

    @api.onchange('training_course_ids')
    @api.constrains('training_course_ids')
    def _onchange_training_course_ids(self):
        if self.training_course_ids:
            all_subjects = self.training_course_ids.mapped('training_subject_ids')
            self.subject_ids = [(6, 0, all_subjects.ids)]
        else:
            self.subject_ids = [(5, 0, 0)]

    def _compute_document_count(self):
        for rec in self:
            # missions = self.env['training.mission'].search([('participants', 'in', rec.id)])
            # attachments = missions.mapped('training_mission_by_week_ids.attachment_ids')
            rec.document_count = 0

    def action_view_documents(self):
        self.ensure_one()
        # Lấy tất cả mission có department này tham gia
        # missions = self.env['training.mission'].search([('participants', 'in', self.id)])
        # attachments = missions.mapped('training_mission_by_week_ids.attachment_ids')
        # return {
        #     'name': 'Tài liệu',
        #     'type': 'ir.actions.act_window',
        #     'res_model': 'ir.attachment',
        #     'views': [(self.env.ref('army_results_manager.view_ir_attachment_custom_tree').id, 'tree'),
        #               (False, 'form')],
        #     # 'domain': [('id', 'in', attachments.ids)],
        #     'context': dict(self.env.context, default_res_model=self._name, default_res_id=self.id),
        # }

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
            'views': [(self.env.ref('hr.view_employee_tree').id, 'tree'),
                      (self.env.ref('hr.view_employee_form').id, 'form')],
            'domain': [('role', '=', 'commanding_officer'), ('department_id', '=', self.id)],
        }

    def action_view_training_officer(self):
        return {
            'name': 'Cán bộ Phụ trách Huấn luyện',
            'type': 'ir.actions.act_window',
            'res_model': 'hr.employee',
            'view_mode': 'tree,form',
            'views': [(self.env.ref('hr.view_employee_tree').id, 'tree'),
                      (self.env.ref('hr.view_employee_form').id, 'form')],
            'domain': [('role', '=', 'training_officer'), ('department_id', '=', self.id)],
        }

    def action_view_student(self):
        return {
            'name': 'Học viên',
            'type': 'ir.actions.act_window',
            'res_model': 'hr.employee',
            'view_mode': 'tree,form',
            'views': [(self.env.ref('hr.view_employee_tree').id, 'tree'),
                      (self.env.ref('hr.view_employee_form').id, 'form')],
            'domain': [('role', '=', 'student'),('department_id', '=', self.id), ]
        }
