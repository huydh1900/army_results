import logging
import json
from odoo import http
from odoo.http import request, Response
from odoo.addons.web.controllers.dataset import DataSet  # Import Controller gốc

_logger = logging.getLogger(__name__)

# Ngưỡng chặn Integer 32-bit
MAX_INT32 = 2147483647
MIN_INT32 = -2147483648

class ArmyDataSet(http.Controller): # Kế thừa lớp DataSet gốc của Odoo

    @http.route(['/web/dataset/call_kw', '/web/dataset/call_kw/<path:path>'], type='json', auth="user")
    def call_kw(self, model, method, args, kwargs, path=None):
        """
        Ghi đè hàm call_kw để kiểm tra tràn số trước khi thực thi
        """
        try:
            # 1. Kiểm tra tràn số trong args (dạng list)
            if args:
                for arg in args:
                    if isinstance(arg, int) and (arg > MAX_INT32 or arg < MIN_INT32):
                        _logger.error(f"[Security] Tràn số phát hiện trong args: {arg} tại model {model}")
                        return {"jsonrpc": "2.0", "error": "Integer Overflow Detected"}

            # 2. Kiểm tra tràn số trong kwargs (dạng dict)
            if kwargs:
                for key, value in kwargs.items():
                    if isinstance(value, int) and (value > MAX_INT32 or value < MIN_INT32):
                        _logger.error(f"[Security] Tràn số phát hiện trong kwargs: {value} tại model {model}")
                        return {"jsonrpc": "2.0", "error": "Integer Overflow Detected"}

        except Exception as e:
            _logger.error(f"Lỗi kiểm tra bảo mật: {str(e)}")

        # 3. Nếu mọi thứ an toàn, gọi lại hàm gốc của Odoo
        return super(ArmyDataSet, self).call_kw(model, method, args, kwargs, path=path)