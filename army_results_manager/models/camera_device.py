from odoo import models, fields, api
import requests
from requests.auth import HTTPDigestAuth
from odoo.exceptions import UserError


class CameraDevice(models.Model):
    _name = "camera.device"
    _rec_name = "name"

    name = fields.Char("Tên Camera", required=True)
    ip_address = fields.Char("Địa chỉ Ip", required=True)
    username = fields.Char("User", default="admin")
    password = fields.Char("Password", default="")
    location_id = fields.Many2one('training.location', string='Tên khu vực')
    connection_ok = fields.Boolean(default=False)
    state = fields.Selection([
        ('not_connect', 'Chưa kết nối'),
        ('ok', 'Hoạt động'),
        ('error', 'Lỗi kết nối'),
    ], string="Trạng thái", default="not_connect")
    media_ids = fields.One2many(
        'media.library',
        'camera_id',
        string='Thư viện media'
    )

    _sql_constraints = [
        (
            'unique_camera_ip',
            'unique(ip_address)',
            'Địa chỉ IP camera đã tồn tại!'
        ),
    ]

    def check_camera_status_digest(self):
        self.ensure_one()

        api_url = f"http://{self.ip_address}/axis-cgi/param.cgi?action=list"

        try:
            response = requests.get(
                api_url,
                auth=HTTPDigestAuth(self.username, self.password),
                timeout=5
            )

            if response.status_code == 401:
                self.write({
                    'state': 'error',
                    'connection_ok': False
                })
                return {
                    "type": "ir.actions.client",
                    "tag": "display_notification",
                    "params": {
                        "title": "Lỗi",
                        "message": "Tài khoản hoặc mật khẩu không đúng",
                        "type": "danger",
                        "sticky": False,
                        "next": {"type": "ir.actions.client", "tag": "soft_reload"},
                    }
                }

            # ❌ Lỗi khác
            if response.status_code != 200:
                self.write({
                    'state': 'error',
                    'connection_ok': False
                })
                return {
                    "type": "ir.actions.client",
                    "tag": "display_notification",
                    "params": {
                        "title": "Lỗi",
                        "message": f"Kết nối thất bại (HTTP {response.status_code})",
                        "type": "danger",
                        "sticky": False,
                        "next": {"type": "ir.actions.client", "tag": "soft_reload"},
                    }
                }

            # ✅ OK
            self.write({
                'state': 'ok',
                'connection_ok': True
            })

            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "Thành công",
                    "message": "Kết nối camera thành công!",
                    "type": "success",
                    "sticky": False,
                    "next": {"type": "ir.actions.client", "tag": "soft_reload"},
                }
            }

        except requests.exceptions.RequestException as e:
            self.write({
                'state': 'error',
                'connection_ok': False
            })
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "Lỗi",
                    "message": f"Không thể kết nối đến camera: {str(e)}",
                    "type": "danger",
                    "sticky": False,
                    "next": {"type": "ir.actions.client", "tag": "soft_reload"},
                }
            }

    def view_camera(self):
        if not self.ip_address:
            raise UserError("Chưa có địa chỉ IP camera.")

        return {
            "type": "ir.actions.act_url",
            "url": f"http://{self.ip_address}",
            "target": "new",
        }


