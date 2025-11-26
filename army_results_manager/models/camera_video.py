from odoo import models, fields


class CameraVideo(models.Model):
    _name = "camera.video"
    _description = "Camera Recorded Videos"

    name = fields.Char("File Name")
    camera_id = fields.Many2one("camera.device", string="Camera")
    filepath = fields.Char("Full Path")
    filesize = fields.Integer("File Size (bytes)")

    # Tải file xuống từ server
    def action_download(self):
        return {
            'type': 'ir.actions.act_url',
            'url': f"/web/content?model=camera.video&id={self.id}&filename={self.name}&field=filepath",
            'target': 'self',
        }
