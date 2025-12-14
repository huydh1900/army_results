from odoo.exceptions import UserError
from odoo import fields, models


class ModifyReasonWizard(models.TransientModel):
    _name = "modify.reason.wizard"
    _description = "Wizard nhập lý do chỉnh sửa"

    reason = fields.Text(string="Lý do chỉnh sửa", required=True)
    training_schedule_id = fields.Many2one('training.schedule')

    def action_confirm(self):
        self.ensure_one()

        if not self.reason:
            raise UserError("Bạn phải nhập lý do chỉnh sửa trước khi xác nhận.")

        schedule = self.training_schedule_id or self.env['training.schedule'].browse(self.env.context.get("active_id"))

        if not schedule:
            raise UserError("Không tìm thấy kế hoạch huấn luyện.")

        schedule.sudo().write({'state': 'to_modify'})
        for plan in schedule.plan_ids:
            plan.sudo().write({'state': 'to_modify'})

        # Thêm lý do mới vào reason_modify, kèm ngày giờ hiện tại
        now_str = fields.Datetime.now().strftime('%d-%m-%Y %H:%M')
        new_entry = f"[{now_str}] {self.reason}"

        if schedule.reason_modify:
            schedule.reason_modify = f"{schedule.reason_modify}\n{new_entry}"
        else:
            schedule.reason_modify = new_entry

        return {'type': 'ir.actions.act_window_close'}
