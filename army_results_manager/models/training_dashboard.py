from odoo import models, fields, api

class TrainingDashboard(models.Model):
    _name = "training.dashboard"
    _description = "Training Dashboard (Kế hoạch huấn luyện)"

    name = fields.Char("Tên Dashboard", default="Thống kê huấn luyện")

    @api.model
    def get_dashboard_data(self):
        """Lấy dữ liệu cho Dashboard"""
        # Ví dụ: Thống kê số lượng kế hoạch huấn luyện
        plans = self.env['training.plan'].search_count([])
        results = self.env['training.result'].read_group(
            [], ['score:avg'], ['unit_id']
        )
        top_units = sorted(results, key=lambda x: x['score'], reverse=True)[:5]

        return {
            'total_plans': plans,
            'top_units': top_units,
        }
