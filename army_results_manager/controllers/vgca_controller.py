# Trong model ir.attachment, thêm route public
from odoo import http
from odoo.http import request
import base64

class VGCAController(http.Controller):

    @http.route('/vgca/file/<int:attachment_id>', type='http', auth='public')
    def download_file(self, attachment_id, **kwargs):
        """Public endpoint để VGCA tải file"""
        attachment = request.env['ir.attachment'].sudo().browse(attachment_id)

        if not attachment.exists():
            return request.not_found()

        # Trả về file content
        return request.make_response(
            base64.b64decode(attachment.datas),
            headers=[
                ('Content-Type', attachment.mimetype),
                ('Content-Disposition', f'attachment; filename={attachment.name}')
            ]
        )