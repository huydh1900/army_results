from odoo.addons.web_enterprise.models import ir_http

def no_expiration_info():
    """Tắt hoàn toàn việc kiểm tra hạn database"""
    return None

# Ghi đè hàm check của Odoo Enterprise
ir_http._get_db_expiration_info = no_expiration_info
