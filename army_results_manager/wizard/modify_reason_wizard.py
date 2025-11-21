# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.exceptions import UserError
from odoo import fields, models


class ModifyReasonWizard(models.TransientModel):
    _name = "modify.reason.wizard"
    _description = "Wizard nhập lý do chỉnh sửa"

    reason = fields.Text(string="Lý do chỉnh sửa", required=True)
    training_plan_id = fields.Many2one('training.plan')

    def action_confirm(self):
        self.ensure_one()

        if not self.reason:
            raise UserError("Bạn phải nhập lý do chỉnh sửa trước khi xác nhận.")
        active_id = self.env.context.get("active_id")
        record = self.sudo().env["training.day"].browse(active_id)

        record.write({
            'state': 'to_modify',
            'reason_modify': self.reason
        })

        plan = record.plan_id
        if plan:
            day_str = record.day.strftime('%d-%m-%Y') if record.day else 'Chưa xác định ngày'
            new_note = f"{day_str}: {self.reason}"

            # Nếu plan.reason_modify đã có nội dung, thêm xuống dòng mới
            if plan.reason_modify:
                updated_note = f"{plan.reason_modify}\n{new_note}"
            else:
                updated_note = new_note

            plan.sudo().write({
                'state': 'to_modify',
                'reason_modify': updated_note,
            })

        return {'type': 'ir.actions.act_window_close'}
