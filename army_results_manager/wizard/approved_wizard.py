from odoo import fields, models, api
from datetime import date
from odoo.exceptions import UserError


class ApprovedWizard(models.TransientModel):
    _name = "approved.wizard"
    _description = "Wizard chọn để duyệt kế hoạch theo tuần/tháng/năm"

    report_type = fields.Selection([
        ('week', 'Theo tuần'),
        ('month', 'Theo tháng'),
        ('year', 'Theo năm'),
    ], string="Loại kế hoạch", required=True, default='week')

    year = fields.Char(string="Năm", default=lambda self: date.today().year)
    month = fields.Selection([
        ('1', 'Tháng 1'), ('2', 'Tháng 2'), ('3', 'Tháng 3'),
        ('4', 'Tháng 4'), ('5', 'Tháng 5'), ('6', 'Tháng 6'),
        ('7', 'Tháng 7'), ('8', 'Tháng 8'), ('9', 'Tháng 9'),
        ('10', 'Tháng 10'), ('11', 'Tháng 11'), ('12', 'Tháng 12'),
    ], string="Tháng")

    week = fields.Selection([
        ('1', 'Tuần 1'), ('2', 'Tuần 2'),
        ('3', 'Tuần 3'), ('4', 'Tuần 4'), ('5', 'Tuần 5'),
    ], string="Tuần")

    @api.onchange('report_type')
    def _onchange_report_type(self):
        if self.report_type:
            self.week = self.month = False

    def action_approved(self):
        Day = self.env['training.day']

        # Tạo domain tìm kiếm linh hoạt theo loại báo cáo
        domain = [('year', '=', self.year)]
        if self.report_type == 'week':
            domain.append(('week', '=', self.week))
            domain.append(('month', '=', self.month))
        elif self.report_type == 'month':
            domain.append(('month', '=', self.month))
        # report_type == 'year' thì chỉ cần lọc theo năm

        results = Day.search(domain)

        if not results:
            raise UserError("Không có bản ghi nào phù hợp để duyệt!")

        # Cập nhật trạng thái duyệt
        results.write({'state': 'approved'})

        return {
            'effect': {
                'fadeout': 'slow',
                'message': f"Đã duyệt {len(results)} bản ghi thành công!",
                'type': 'rainbow_man',
            }
        }
