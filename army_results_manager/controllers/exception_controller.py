from odoo import http
from odoo.http import request
import json


class ExceptionController(http.Controller):

    @http.route('/web/dataset/call_kw/web_tour.tour/get_consumed_tours', type='json', auth='user', methods=['POST'],
                csrf=True)
    def get_consumed_tours(self, **kwargs):
        try:
            raw = request.httprequest.data
            data = json.loads(raw)

            # 1. Bổ sung kiểm tra loại dữ liệu (type) và giá trị của 'jsonrpc'
            jsonrpc_val = data.get('jsonrpc')

            # Đảm bảo 'jsonrpc' tồn tại, là kiểu chuỗi (string) VÀ có giá trị là '2.0'
            # Nếu nó là một số nguyên lớn, hàm .get() sẽ nhận giá trị số và
            # kiểm tra isinstance(jsonrpc_val, str) sẽ thất bại, dẫn đến trả về lỗi
            if not (jsonrpc_val and isinstance(jsonrpc_val, str) and jsonrpc_val == '2.0'):
                return {'success': False, 'error': 'Định dạng dữ liệu không hợp lệ.'}

        except Exception:
            # Xử lý các lỗi khác như JSON không hợp lệ, lỗi IO, v.v.
            return {'success': False, 'error': 'Có lỗi xảy ra, vui lòng thử lại'}

    @http.route('/web/webclient/translations/<path:mods>', type='http', auth="none", methods=['GET'])
    def translations_loader(self, mods=None, lang=None, mods_js=False, mods_xml=False):
        try:
            MAX_MODS_LENGTH = 1024
            if mods and len(mods) > MAX_MODS_LENGTH:
                # Trả về lỗi 400 mà không hiển thị traceback
                return request.make_response("Bad Request.", status=400)

        except Exception:
            # Bắt bất kỳ lỗi nào khác và trả về lỗi 500 an toàn
            return request.make_response("Internal Server Error.", status=500)
