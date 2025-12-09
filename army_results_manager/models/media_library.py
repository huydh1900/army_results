from odoo import models, fields, api


class MediaLibrary(models.Model):
    _name = "media.library"
    _description = "Quản lý hình ảnh, video"
    _order = "create_date desc"

    name = fields.Char("Tên file", required=True)
    media_type = fields.Selection([
        ("image", "Ảnh"),
        ("video", "Video"),
    ], string="Loại", required=True, default="image")

    attachment_id = fields.Many2one(
        "ir.attachment",
        string="Tập tin đính kèm",
        ondelete="cascade"
    )

    # URL TRỰC TIẾP - NHANH NHẤT
    file_url = fields.Char(
        string="URL Download",
        compute="_compute_file_url",
        store=True
    )

    data = fields.Binary(
        related="attachment_id.datas",
        string="File",
        readonly=True
    )

    mimetype = fields.Char(
        related="attachment_id.mimetype",
        string="MIME Type",
        readonly=True
    )

    filesize = fields.Integer(
        related="attachment_id.file_size",
        string="Kích thước (bytes)",
        readonly=True
    )

    # Upload cho ảnh
    upload_file = fields.Binary("Tải ảnh lên")
    upload_filename = fields.Char("Tên file upload")

    # Upload cho video - dùng URL
    video_url = fields.Char("URL Video (YouTube, Vimeo, ...)")

    # ==========================================
    # Tạo URL trực tiếp
    # ==========================================
    @api.depends("attachment_id")
    def _compute_file_url(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        for rec in self:
            if rec.attachment_id:
                rec.file_url = f"{base_url}/web/content/{rec.attachment_id.id}?download=true"
            else:
                rec.file_url = False

    # ==========================================
    # Tạo attachment
    # ==========================================
    def _create_attachment(self):
        self.ensure_one()

        # CHỈ XỬ LÝ ẢNH - upload_file
        if self.media_type == "image":
            if not self.upload_file or not self.upload_filename:
                return

            filename_lower = self.upload_filename.lower()

            # Xác định mimetype cho ảnh
            mimetype_map = {
                (".jpg", ".jpeg"): "image/jpeg",
                (".png",): "image/png",
                (".gif",): "image/gif",
                (".webp",): "image/webp",
                (".bmp",): "image/bmp",
            }

            mimetype = "image/jpeg"  # default

            for exts, mime in mimetype_map.items():
                if filename_lower.endswith(exts):
                    mimetype = mime
                    break

            # Tạo attachment cho ảnh
            attachment = self.env["ir.attachment"].create({
                "name": self.upload_filename,
                "datas": self.upload_file,
                "res_model": self._name,
                "res_id": self.id,
                "type": "binary",
                "mimetype": mimetype,
                "public": True,
            })

            self.write({
                "attachment_id": attachment.id,
                "name": self.upload_filename,
                "upload_file": False,
                "upload_filename": False,
            })

        # XỬ LÝ VIDEO - chỉ lưu URL
        elif self.media_type == "video":
            if not self.video_url:
                return

            # Với video, không tạo attachment, chỉ lưu URL
            if not self.name or self.name == "New":
                self.name = "Video: " + self.video_url[:50]

    @api.model
    def create(self, vals):
        if not vals.get("name"):
            if vals.get("upload_filename"):
                vals["name"] = vals["upload_filename"]
            elif vals.get("video_url"):
                vals["name"] = "Video: " + vals["video_url"][:50]

        rec = super().create(vals)
        rec._create_attachment()
        return rec

    def write(self, vals):
        res = super().write(vals)

        # Chỉ tạo attachment khi upload ảnh mới
        if vals.get("upload_file") and self.media_type == "image":
            self._create_attachment()

        # Cập nhật tên khi thay đổi video URL
        if vals.get("video_url") and self.media_type == "video":
            if not vals.get("name"):
                self.name = "Video: " + self.video_url[:50]

        return res

    # ==========================================
    # DOWNLOAD
    # ==========================================
    def action_download(self):
        self.ensure_one()

        # Nếu là video URL - không có download
        if self.media_type == "video" and self.video_url:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "message": "Video URL không thể tải xuống. Vui lòng xem trực tiếp.",
                    "type": "info",
                }
            }

        # Nếu là ảnh - download bình thường
        if not self.file_url:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "message": "Không có file để tải",
                    "type": "warning",
                }
            }

        return {
            "type": "ir.actions.act_url",
            "url": self.file_url,
            "target": "self",
        }

    # ==========================================
    # XEM FILE
    # ==========================================
    def action_view(self):
        self.ensure_one()

        # Nếu là video URL - mở trực tiếp
        if self.media_type == "video" and self.video_url:
            return {
                "type": "ir.actions.act_url",
                "url": self.video_url,
                "target": "new",
            }

        # Nếu là ảnh - xem từ attachment
        if not self.attachment_id:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "message": "Không có file để xem",
                    "type": "warning",
                }
            }

        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        view_url = f"{base_url}/web/content/{self.attachment_id.id}"

        return {
            "type": "ir.actions.act_url",
            "url": view_url,
            "target": "new",
        }

    # ==========================================
    # COPY LINK
    # ==========================================
    def action_copy_link(self):
        self.ensure_one()

        # Nếu là video URL
        if self.media_type == "video" and self.video_url:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "Link video đã sao chép!",
                    "message": f"Link: {self.video_url}",
                    "type": "success",
                    "sticky": False,
                }
            }

        # Nếu là ảnh
        if not self.file_url:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "message": "Không có file",
                    "type": "warning",
                }
            }

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Link đã sao chép!",
                "message": f"Link: {self.file_url}",
                "type": "success",
                "sticky": False,
            }
        }