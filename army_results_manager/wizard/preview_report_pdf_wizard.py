from odoo import fields, models, api


class PreviewReportPdfWizard(models.TransientModel):
    _name = "preview.report.pdf.wizard"
    _description = "Preview report PDF Wizard"

    sender_id = fields.Many2one('hr.employee', string="Người gửi", readonly=True)
    attachment_ids = fields.Many2many(
        'ir.attachment',
        'preview_report_pdf_wizard_attachment_rel',
        'wizard_id', 'attachment_id',
        string='Tài liệu PDF',
        domain=[('mimetype', '=', 'application/pdf')],
        readonly=True,
    )

    attachment_ids_approved = fields.Many2many(
        'ir.attachment',
        'preview_report_pdf_wizard_attachment_approved_rel',  #
        'wizard_id', 'attachment_id',
        string='Tài liệu PDF (Đã ký)',
        domain=[('mimetype', '=', 'application/pdf')],
    )
