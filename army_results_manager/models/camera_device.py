from odoo import models, fields, api
import threading
import cv2
import time

buffer_dict = {}  # lưu MJPEG frame cho từng camera


class CameraDevice(models.Model):
    _name = "camera.device"
    _rec_name = "name"
    _description = "Thiết bị Camera"

    name = fields.Char("Tên camera", required=True)
    ip_address = fields.Char("IP camera", required=True)
    username = fields.Char("Tên đăng nhập", default="admin")
    password = fields.Char("Mật khẩu", default="")
    mjpeg_port = fields.Integer(default=5000)
    mjpeg_url = fields.Char(compute="_compute_mjpeg_url")
    buffer_dict = {}
    # location_id = fields.Char()

    thread_active = fields.Boolean(default=False)

    @api.depends('mjpeg_port')
    def _compute_mjpeg_url(self):
        for rec in self:
            rec.mjpeg_url = f"http://127.0.0.1:{rec.mjpeg_port}/mjpeg/{rec.id}"

    def start_stream(self):
        for rec in self:
            if rec.thread_active:
                continue
            rec.thread_active = True

            # Lấy dữ liệu cần thiết ra ngoài recordset (thread-safe)
            camera_data = {
                'id': rec.id,
                'ip_address': rec.ip_address,
                'username': rec.username,
                'password': rec.password,
            }

            # Tạo thread cho camera
            t = threading.Thread(target=self._stream_buffer_thread, args=(camera_data,))
            t.daemon = True
            t.start()

    def _stream_buffer_thread(self, camera_data):
        camera_id = camera_data['id']
        rtsp_url = f"rtsp://{camera_data['username']}:{camera_data['password']}@{camera_data['ip_address']}/Streaming/Channels/101"

        cap = cv2.VideoCapture(rtsp_url)
        if not cap.isOpened():
            # Không kết nối được camera
            return

        while True:
            # Kiểm tra thread_active trong database mỗi vòng lặp
            try:
                rec_active = self.env['camera.device'].browse(camera_id).thread_active
            except Exception:
                # Nếu db closed, dừng thread
                break

            if not rec_active:
                break

            ret, frame = cap.read()
            if ret:
                ret2, jpeg = cv2.imencode('.jpg', frame)
                if ret2:
                    buffer_dict[camera_id] = jpeg.tobytes()

            # Giới hạn tốc độ vòng lặp, tránh quá tải CPU
            time.sleep(0.05)  # ~20 FPS

        cap.release()
        # Dọn sạch buffer khi dừng
        if camera_id in buffer_dict:
            del buffer_dict[camera_id]



    def stop_stream(self):
        for rec in self:
            rec.thread_active = False
            if rec.id in buffer_dict:
                del buffer_dict[rec.id]

    def _stream_buffer(self, rec):
        rtsp_url = f"rtsp://{rec.username}:{rec.password}@{rec.ip_address}/Streaming/Channels/101"
        cap = cv2.VideoCapture(rtsp_url)
        while rec.thread_active:
            ret, frame = cap.read()
            if ret:
                ret2, jpeg = cv2.imencode('.jpg', frame)
                if ret2:
                    buffer_dict[rec.id] = jpeg.tobytes()
        cap.release()
