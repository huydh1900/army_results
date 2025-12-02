# -*- coding: utf-8 -*-
from odoo import models, api, fields
from odoo.http import request
import logging
import pytz

_logger = logging.getLogger(__name__)


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    is_signed = fields.Boolean(default=False, string="Đã ký", readonly=True)
    approver_id = fields.Many2one('hr.employee', string='Cán bộ phê duyệt', readonly=True)

    def action_sign_document(self):
        return {
            "type": "ir.actions.client",
            "tag": "digital_signature_action",
            "target": "new",
            "params": {
                "attachment_id": self.id,
            },
        }

    @api.model
    def mark_signed(self, attachment_id):
        """Cập nhật trạng thái đã ký"""
        record = self.browse(attachment_id)
        record.sudo().write({"is_signed": True})

    @api.model
    def vgca_sign_msg(self, attachment_id):
        """Bước 1: Chuẩn bị URL và JWT Token để VGCA ký file"""
        try:
            _logger.info("=== VGCA_SIGN_MSG (Bước 1: Chuẩn bị URL) ===")
            attachment = self.browse(attachment_id)

            _logger.info(f"Set attachment {attachment.id} to public")

            # Bước 1.2: Tạo URL public
            base_url = request.httprequest.host_url.rstrip("/")
            file_url = f"{base_url}/web/content/{attachment.id}"
            upload_handler_url = f"{base_url}/vgca/upload"

            issued_date = pytz.timezone('Asia/Ho_Chi_Minh')
            # Chuẩn bị response
            result = {
                'success': True,
                'attachment_id': attachment.id,
                'file_name': attachment.name,
                'file_url': file_url,
                'upload_handler': upload_handler_url,
                'doc_number': '001/2024/QD',
                'issued_date': issued_date,
            }

            _logger.info(f"Result: {result}")
            return result

        except Exception as e:
            _logger.error(f"Error: {e}", exc_info=True)
            return {'error': str(e)}
