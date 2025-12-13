from odoo import models, fields, api
import requests
from requests.auth import HTTPDigestAuth
from odoo.exceptions import UserError


class CameraDevice(models.Model):
    _name = "camera.device"
    _rec_name = "name"

    serial_number = fields.Char(string="Serial Number")
    name = fields.Char("Tên Camera")
    ip_address = fields.Char("Địa chỉ Ip")
    username = fields.Char("User", default="admin")
    password = fields.Char("Password", default="")
    port = fields.Char("Port")
    location_id = fields.Many2one('training.location', string='Tên khu vực')
    connection_ok = fields.Boolean(default=False)
    state = fields.Selection([
        ('ok', 'Hoạt động bình thường'),
        ('not_connect', 'Chưa kết nối'),
        ('error', 'Lỗi kết nối'),
    ], string="Trạng thái", default="not_connect")

    # def check_camera_status_digest(self):
    #     username = self.username
    #     password = self.password
    #     ip_address = self.ip_address
    #
    #     api_url = f"http://{ip_address}/axis-cgi/basicdeviceinfo.cgi"
    #
    #     headers = {
    #         "Content-Type": "application/json",
    #         "Accept": "application/json",
    #     }
    #
    #     payload = {
    #         "apiVersion": "1.0",
    #         "method": "getAllProperties",
    #     }
    #
    #     try:
    #         response = requests.post(
    #             api_url,
    #             auth=HTTPDigestAuth(username, password),
    #             headers=headers,
    #             json=payload,
    #             timeout=10
    #         )
    #
    #         if response.status_code == 401:
    #             self.write({'state': 'error', 'connection_ok': False})
    #             self.state = 'error'
    #             raise UserError("Tài khoản hoặc mật khẩu không đúng.")
    #
    #         elif response.status_code != 200:
    #             self.write({'state': 'error', 'connection_ok': False})
    #             raise UserError(f"Kết nối thất bại (HTTP {response.status_code}): {response.text}")
    #
    #         try:
    #             res_json = response.json()
    #             if "error" in res_json:
    #                 self.write({'state': 'error', 'connection_ok': False})
    #                 raise UserError(f"Lỗi từ camera: {res_json['error']}")
    #
    #         except ValueError:
    #             self.write({'state': 'error', 'connection_ok': False})
    #             raise UserError(f"Camera trả về dữ liệu không hợp lệ: {response.text}")
    #
    #         # ✔ KẾT NỐI THÀNH CÔNG
    #         self.write({'state': 'ok', 'connection_ok': True})
    #
    #         return {
    #             "type": "ir.actions.client",
    #             "tag": "display_notification",
    #             "params": {
    #                 "title": "Thành công",
    #                 "message": "Kết nối camera thành công!",
    #                 "type": "success",
    #                 "sticky": False,
    #             }
    #         }
    #
    #     except requests.exceptions.RequestException as e:
    #         self.write({'state': 'error', 'connection_ok': False})
    #         raise UserError(f"Không thể kết nối đến camera: {str(e)}")

    def check_camera_status_digest(self):
        username = self.username
        password = self.password
        ip_address = self.ip_address

        # API đúng để kiểm tra kết nối
        api_url = f"http://{ip_address}/axis-cgi/param.cgi?action=list"

        try:
            response = requests.get(
                api_url,
                auth=HTTPDigestAuth(username, password),
                timeout=10
            )

            # Sai tài khoản
            if response.status_code == 401:
                self.write({'state': 'error', 'connection_ok': False})
                raise UserError("Tài khoản hoặc mật khẩu không đúng.")

            # Camera trả lỗi khác
            elif response.status_code != 200:
                self.write({'state': 'error', 'connection_ok': False})
                raise UserError(f"Kết nối thất bại (HTTP {response.status_code})")

            # ✔ Kết nối OK
            self.write({'state': 'ok', 'connection_ok': True})

            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "Thành công",
                    "message": "Kết nối camera thành công!",
                    "type": "success",
                    "sticky": False,
                }
            }

        except requests.exceptions.RequestException as e:
            self.write({'state': 'error', 'connection_ok': False})
            raise UserError(f"Không thể kết nối đến camera: {str(e)}")

    def view_camera(self):
        if not self.ip_address:
            raise UserError("Chưa có địa chỉ IP camera.")

        return {
            "type": "ir.actions.act_url",
            "url": f"http://{self.ip_address}",
            "target": "new",
        }

    # def view_camera(self):
        # return {
        #     "type": "ir.actions.act_url",
        #     "url": f"/camera/proxy/{self.id}",
        #     "target": "new",
        # }

