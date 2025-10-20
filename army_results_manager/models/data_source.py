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

                soup = BeautifulSoup(response.text, 'html.parser')
                print(soup)
                links = soup.find_all('a')

                for link in links:
                    url = link.get('href')
                    title = link.get('title')
                    text = link.text.strip()

                    print(f"Title: {title}, Text: {text}, Link: {url}")

                    try:
                        news = requests.get(url)
                        news_soup = BeautifulSoup(news.content, "html.parser")

                        # Lấy tất cả ảnh trong body bài viết
                        body_tag = news_soup.find("div", itemprop="articleBody")
                        images = []
                        if body_tag:
                            for img_tag in body_tag.find_all("img"):
                                src = img_tag.get("src")
                                if src:
                                    images.append(src)

                        print(f"Images ({len(images)}): {images}")
                        print("_________________________________________________________________")

                    except Exception as e:
                        print(f"Lỗi khi crawl {url}: {e}")
                # titles = soup.findAll('h3')
                # print(titles)

                # links = [link.find('a').attrs["href"] for link in titles]
                # # print(links)
                # articles = soup.find_all('div', class_='item-news')
                #
                # for link in links:
                #     news = requests.get(link)
                #     soup = BeautifulSoup(news.content, "html.parser")
                #     title = soup.find("h1", class_="post-title").text
                #     abstract = soup.find("h2", class_="sapo").text
                #     body = soup.find("div", id="main-detail-body")
                #     content = body.findChildren("p", recursive=False)[0].text + body.findChildren("p", recursive=False)[
                #         1].text
                #     image = body.find("img").attrs["src"]
                #     print("Tiêu đề: " + title)
                #     print("Tiêu đề: " + soup)
                #     # print("Mô tả: " + abstract)
                #     # print("Nội dung: " + content)
                #     # print("Ảnh minh họa: " + image)
                #     print("_________________________________________________________________________")

            except Exception as e:
                _logger.error(f"Lỗi khi thu thập dữ liệu từ {record.url}: {e}")
