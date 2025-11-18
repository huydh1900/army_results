# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'
    openai_api_key = fields.Char(
        string="OpenAI API Key",
        config_parameter='openai.api_key'
    )
class ResUsers(models.Model):
    _inherit = 'res.users'

    signature_file = fields.Binary("Tệp chữ ký")
    signature_filename = fields.Char("Tên tệp chữ ký")



