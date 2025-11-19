from odoo import fields, models, api


class PreviewReportPdfWizard(models.TransientModel):
    _name = "preview.report.pdf.wizard"
    _description = "Preview report PDF Wizard"

    sender_id = fields.Many2one('hr.employee', string="Người gửi", readonly=True)
    attachment_ids = fields.Many2many(
        'ir.attachment',
        string='Tài liệu PDF',
        domain=[('mimetype', '=', 'application/pdf')], readonly=True
    )