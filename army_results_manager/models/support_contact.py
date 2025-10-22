from odoo import models, fields, api
import base64
import io
import qrcode


class SupportContact(models.Model):
    _name = "support.contact"
    _rec_name = "name"
    _description = "Thông tin trợ giúp trực tuyến"

    name = fields.Char(string="Tên người phụ trách")
    position = fields.Char(string="Chức vụ")
    phone = fields.Char(string="Số điện thoại")
    email = fields.Char(string="Email")
    note = fields.Text(string="Ghi chú")
    zalo_qr = fields.Binary("Mã QR Zalo", compute="_compute_zalo_qr", store=True)

    @api.depends('phone')
    def _compute_zalo_qr(self):
        for record in self:
            if record.phone:
                # Tạo đường dẫn Zalo
                zalo_url = f"https://zalo.me/{record.phone.strip()}"

                # Tạo QR Code từ đường dẫn
                qr_img = qrcode.make(zalo_url)
                buffer = io.BytesIO()
                qr_img.save(buffer, format="PNG")
                qr_data = base64.b64encode(buffer.getvalue())

                record.zalo_qr = qr_data
            else:
                record.zalo_qr = False
