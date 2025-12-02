# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request, Response
import json
import logging
import os
from datetime import datetime

_logger = logging.getLogger(__name__)


class VGCAController(http.Controller):

    @http.route('/vgca/upload', type='http', auth='public', methods=['POST'], csrf=False)
    def vgca_upload_handler(self, **kwargs):
        try:
            upload_dir = r"C:\vgca_upload"
            os.makedirs(upload_dir, exist_ok=True)

            file_data = None
            file_name = None

            # Lấy file từ plugin
            for field_name in ['uploadfile','file','File','FileData','uploadedFile','fileToUpload']:
                if field_name in request.httprequest.files:
                    uploaded_file = request.httprequest.files[field_name]
                    file_data = uploaded_file.read()
                    file_name = uploaded_file.filename
                    break

            if not file_data:
                return Response(json.dumps({
                    'Status': False,
                    'Message': "Không nhận được file upload!",
                    'FileName': "",
                    'FileServer': ""
                }), content_type='application/json', status=400)

            # Tạo tên file mới
            base_name, _ext = os.path.splitext(file_name)
            ext = ".pdf"
            date_str = datetime.now().strftime("_%d%m%Y")

            signed_file_name = f"{base_name}_signed{date_str}{ext}"
            server_path = os.path.join(upload_dir, signed_file_name)

            # Lưu file
            with open(server_path, 'wb') as f:
                f.write(file_data)

            # URL download
            file_url = f"{request.httprequest.host_url}vgca/download/{signed_file_name}"

            return Response(json.dumps({
                'Status': True,
                'Message': "",
                'FileName': signed_file_name,
                'FileServer': file_url
            }), content_type='application/json')

        except Exception as e:
            return Response(json.dumps({
                'Status': False,
                'Message': str(e),
                'FileName': "",
                'FileServer': ""
            }), content_type='application/json', status=500)

    @http.route('/vgca/download/<filename>', type='http', auth='public')
    def vgca_download(self, filename, **kwargs):
        try:
            temp_dir = r"C:\vgca_upload"
            file_path = os.path.join(temp_dir, filename)

            if not os.path.exists(file_path):
                return Response("File not found", status=404)

            with open(file_path, 'rb') as f:
                data = f.read()

            headers = [
                ('Content-Type', 'application/pdf'),
                ('Content-Disposition', f'attachment; filename="{filename}"'),
                ('Content-Length', str(len(data)))
            ]

            return Response(data, headers=headers)

        except Exception as e:
            return Response(str(e), status=500)
