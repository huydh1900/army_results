from odoo import models, fields, api
import base64

class ResCompany(models.Model):
    _inherit = "res.company"

    favicon = fields.Binary("Favicon", attachment=True,
                            default=lambda self: self._default_favicon())

    @api.model
    def _default_favicon(self):
        with open("army_results_manager/static/src/img/logo.png", "rb") as f:
            return base64.b64encode(f.read())
