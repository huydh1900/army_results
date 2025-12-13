from odoo import models, api


class ResUsers(models.Model):
    _inherit = 'res.users'

    @api.model
    def create(self, vals):
        if "lang" not in vals and self.env.ref("base.lang_vi_VN", raise_if_not_found=False):
            vals["lang"] = "vi_VN"
        return super().create(vals)
