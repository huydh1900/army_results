from odoo import models, fields, api

class MediaLibrary(models.Model):
    _name = "media.library"
    _description = "Quản lý hình ảnh, video camera"
    _order = "create_date desc"
    _rec_name = "name"

    name = fields.Char(
        string="Tên thư mục",
        required=True
    )

    location_id = fields.Many2one(
        'training.location',
        string='Khu vực giám sát',
        required=True
    )

    location_name = fields.Char(related='location_id.name')

    camera_id = fields.Many2one(
        'camera.device',
        string='Camera',
        required=True,
        domain="[('location_id','=',location_id)]"
    )

    active =fields.Boolean(default=True)

    attachment_ids = fields.Many2many(
        'ir.attachment',
        string='Hình ảnh, video',
        required=True
    )

    description = fields.Text(string="Mô tả")

    @api.onchange('location_id')
    def _onchange_location_id(self):
        """Đổi khu vực thì reset camera"""
        self.camera_id = False
