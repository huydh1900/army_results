from odoo import http
from odoo.http import request
import requests

class AIController(http.Controller):

    @http.route('/ai/generate_note/<int:record_id>', type='http', auth='user')
    def generate_note(self, record_id):
        """Tạo nhận xét AI cho học viên"""
        
        # Lấy record
        record = request.env['training.result'].sudo().browse(record_id)
        if not record.exists():
            return request.redirect(f'/web#id={record_id}&model=training.result&view_type=form')
        
        # Lấy domain từ settings
        domain = request.env['ir.config_parameter'].sudo().get_param('openai.api_key')
        if not domain:
            record.write({'note': 'Lỗi: Chưa cấu hình Domain trong Settings!'})
            return request.redirect(f'/web#id={record_id}&model=training.result&view_type=form')
        
        if not record.employee_id:
            record.write({'note': 'Lỗi: Học viên không hợp lệ!'})
            return request.redirect(f'/web#id={record_id}&model=training.result&view_type=form')
        
        # Gọi API FastAPI
        fastapi_url = f"{domain}/api/summarize_from_db/{record.employee_id.id}"
        payload = {"table": "training_result"}
        
        try:
            response = requests.post(fastapi_url, json=payload, timeout=30)
            data = response.json()
            
            if data.get("status") == "success":
                summary = data.get("summary", "Không có nội dung nhận xét")
                record.write({'note': summary})
            else:
                record.write({'note': 'Lỗi: API không trả về kết quả hợp lệ!'})
                
        except requests.exceptions.Timeout:
            record.write({'note': 'Lỗi: Hết thời gian chờ kết nối đến server AI!'})
        except requests.exceptions.ConnectionError:
            record.write({'note': 'Lỗi: Không thể kết nối đến server AI!'})
        except Exception as e:
            record.write({'note': f'Lỗi: {str(e)}'})
        
        # Redirect về form view
        # Lấy URL gốc từ HTTP referer
        referer = request.httprequest.referrer
        if referer and '/web#' in referer:
            # Redirect về đúng URL gốc
            return request.redirect(referer)
        else:
            # Fallback: redirect về list view
            return request.redirect('/web#model=training.result&view_type=list')