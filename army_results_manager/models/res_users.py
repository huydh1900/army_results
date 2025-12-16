from odoo import models, api, fields


class ResUsers(models.Model):
    _inherit = 'res.users'

    @api.model
    def create(self, vals):
        # Nếu không có ngôn ngữ được chỉ định khi tạo user mới
        if "lang" in vals and vals["lang"] == "en_US":
            # Kiểm tra xem ngôn ngữ tiếng Việt đã được cài đặt chưa
            lang_vi = self.env.ref("base.lang_vi_VN", raise_if_not_found=False)
            vals["lang"] = "vi_VN"  # mặc định tiếng Việt
        return super(ResUsers, self).create(vals)
