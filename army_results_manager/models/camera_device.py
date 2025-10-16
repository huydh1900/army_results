from odoo import models, fields, api
import requests

class CameraDevice(models.Model):
    _name = "camera.device"
    _rec_name = "name"
    _description = "Thiết bị Camera"

    name = fields.Char("Tên camera", required=True)
    location_id = fields.Many2one("training.location", string='Địa điểm')
    stream_url = fields.Char("Đường dẫn luồng video", readonly=True)
    ip_address = fields.Char(string="Địa chỉ IP", required=True)
    username = fields.Char(string="Tên đăng nhập")
    password = fields.Char(string="Mật khẩu")
    department_id = fields.Many2one('hr.department', string='Thuộc đơn vị')

    def action_view_camera(self):
        return

    def action_test_connect_camera(self):
        return

