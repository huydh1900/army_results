from odoo import fields, models, api
from odoo.exceptions import UserError


class PreviewReportPdfWizard(models.TransientModel):
    _name = "preview.report.pdf.wizard"
    _description = "Preview report PDF Wizard"