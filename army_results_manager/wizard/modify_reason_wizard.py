# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ModifyReasonWizard(models.TransientModel):
    _name = "modify.reason.wizard"
    _description = "Wizard nhập lý do chỉnh sửa"

    reason = fields.Text(string="Lý do chỉnh sửa", required=True)
    training_plan_id = fields.Many2one('training.plan')

    def action_confirm(self):
        active_id = self.env.context.get("active_id")
        record = self.env["training.plan"].browse(active_id)
        if record:
            old_reason = record.reason_modify or ""
            new_reason = f"{old_reason}\n- {self.reason}" if old_reason else self.reason
            record.write({
                'state': 'to_modify',
                'reason_modify': new_reason,
            })
        return {'type': 'ir.actions.act_window_close'}


