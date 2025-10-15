from odoo import models, fields, api
import requests
from bs4 import BeautifulSoup
import logging

_logger = logging.getLogger(__name__)

class DataSource(models.Model):
    _name = 'data.source'
    _description = 'Nguồn thu thập thông tin'

    name = fields.Char(string='Tên nguồn', required=True)
    source_type = fields.Selection([
        ('rss', 'RSS Feed'),
        ('api', 'Webservice (API)'),
    ], string="Phương thức", required=True)
    category = fields.Selection([
        ('tin_tuc', 'Tin tức'),
        ('su_kien', 'Sự kiện'),
        ('thong_bao', 'Thông báo'),
    ], string='Loại tin cần thu thập', required=True)
    url = fields.Char(string='URL', required=True, default='https://vnexpress.net/')
    active = fields.Boolean(string='Kích hoạt', default=True)
    last_collected = fields.Datetime(string='Lần thu thập gần nhất', readonly=True)

    # ==============================
    # ========== THU THẬP ==========
    # ==============================

    def _collect_from_source(self):
        """Thu thập link bài viết từ VnExpress theo category."""
        try:
            response = requests.get(self.url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')

            links = set()
            for a in soup.find_all('a', href=True):
                href = a['href']
                # Loại bỏ link không phải bài báo
                if href.startswith('https://timkiem.vnexpress.net') and href.count('/') > 3:
                    # Tùy theo category mà lọc
                    if self.category == 'tin_tuc' and '?q=tin%20tức' in href:
                        links.add(href)
                    elif self.category == 'su_kien' and '/su-kien' in href:
                        links.add(href)
                    elif self.category == 'thong_bao' and '/thong-bao' in href:
                        links.add(href)
                    elif self.category not in ['tin_tuc', 'su_kien', 'thong_bao']:
                        links.add(href)

            for link in links:
                self.env['collected.data'].create({
                    'title': link,
                    'content': '',
                    'source_id': self.id,
                })

            self.last_collected = fields.Datetime.now()
            _logger.info(f"✅ Thu thập {len(links)} link từ {self.url} ({self.category})")

        except Exception as e:
            _logger.error(f"❌ Lỗi khi thu thập từ {self.url}: {e}")

    def action_collect_now(self):
        """Gọi từ nút thủ công."""
        for src in self:
            src._collect_from_source()

    @api.model
    def collect_data_cron(self):
        """Hàm gọi từ cron (tự động) để thu thập tất cả nguồn đang active."""
        sources = self.search([('active', '=', True)])
        for src in sources:
            src._collect_from_source()
