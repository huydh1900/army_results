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
        ('html', 'Trang web (HTML)'),
    ], string="Phương thức", required=True)
    category = fields.Selection([
        ('tin_tuc', 'Tin tức'),
        ('su_kien', 'Sự kiện'),
        ('thong_bao', 'Thông báo'),
    ], string='Loại tin cần thu thập', required=True)
    url = fields.Char(string='URL', required=True)
    active = fields.Boolean(string='Kích hoạt', default=True)
    last_collected = fields.Datetime(string='Lần thu thập gần nhất', readonly=True)

    def action_collect_now(self):
        self._collect_from_source()

    def _collect_from_source(self):
        """Thu thập dữ liệu từ nguồn"""
        for record in self:
            try:
                response = requests.get(record.url, timeout=10)
                response.raise_for_status()

                soup = BeautifulSoup(response.text, "html.parser")
                articles = soup.find_all("article")

                results = []
                for art in articles:
                    a_tag = art.find("a", href=True, title=True)
                    title = a_tag["title"].strip() if a_tag else ""
                    link = a_tag["href"].strip() if a_tag else ""

                    # Lấy ảnh trong bài
                    img_tag = art.find("img")
                    img_src = img_tag["src"].strip() if img_tag and img_tag.has_attr("src") else ""

                    if not img_src or not link:
                        continue

                    # 🔹 Lấy toàn bộ <p> trong trang chi tiết bài viết
                    description = ""
                    try:
                        article_page = requests.get(link, timeout=10)
                        article_page.raise_for_status()
                        article_soup = BeautifulSoup(article_page.text, "html.parser")

                        # Gộp tất cả các thẻ <p> trong nội dung bài
                        paragraphs = article_soup.find_all("p")
                        description = "\n".join(p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True))
                    except Exception as sub_e:
                        _logger.warning(f"Không thể lấy nội dung chi tiết từ {link}: {sub_e}")

                    results.append({
                        "title": title,
                        "source_id": self.id,
                        "link": link,
                        "image_url": img_src,
                        "description": description,
                        "category": "tin_tuc",
                    })

                Collected = self.env['collected.data']
                Collected.create(results)
            except Exception as e:
                _logger.error(f"Lỗi khi thu thập dữ liệu từ {record.url}: {e}")
