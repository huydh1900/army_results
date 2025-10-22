from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)

class TrainingWarningLog(models.Model):
    _name = "training.warning.log"
    _description = "Nhật ký cảnh báo huấn luyện"

    date = fields.Datetime("Ngày tạo", default=fields.Datetime.now)
    message = fields.Text("Nội dung cảnh báo")

