from odoo import models, fields, api
import threading
import subprocess
import logging

_logger = logging.getLogger(__name__)

# Dictionary global để kiểm soát thread
_active_streams = {}


class CameraDevice(models.Model):
    _name = "camera.device"
    _rec_name = "name"

    name = fields.Char("Tên Camera")
    ip_address = fields.Char("IP Camera")
    username = fields.Char("User", default="admin")
    password = fields.Char("Password", default="")
    port = fields.Char("Port")
    is_streaming = fields.Boolean("Đang Stream", default=False)

    buffer_dict = {}  # Lưu frame MJPEG

    mjpeg_url = fields.Char(compute="_compute_mjpeg_url")

    def _compute_mjpeg_url(self):
        for rec in self:
            rec.mjpeg_url = f"/mjpeg/{rec.id}"

    def start_stream(self):
        self.ensure_one()
        _logger.info(f"[Camera {self.id}] Bắt đầu stream...")

        if self.id in _active_streams:
            _logger.warning(f"[Camera {self.id}] Stream đã chạy rồi!")
            return {
                "type": "ir.actions.act_url",
                "url": self.mjpeg_url,
                "target": "new",
            }

        # Đánh dấu đang stream
        self.write({"is_streaming": True})
        _active_streams[self.id] = True

        camera_data = {
            "id": self.id,
            "ip_address": self.ip_address,
            "username": self.username,
            "password": self.password,
        }

        t = threading.Thread(target=self._stream_worker, args=(camera_data,), daemon=True)
        t.start()

        return {
            "type": "ir.actions.act_url",
            "url": self.mjpeg_url,
            "target": "new",
        }

    def stop_stream(self):
        self.ensure_one()
        _logger.info(f"[Camera {self.id}] Dừng stream...")
        _active_streams.pop(self.id, None)
        self.write({"is_streaming": False})
        CameraDevice.buffer_dict.pop(self.id, None)

    @staticmethod
    def _stream_worker(cam):
        """Worker thread đọc RTSP và ghi vào buffer"""
        cam_id = cam["id"]
        rtsp_url = (
            f"rtsp://{cam['username']}:{cam['password']}@"
            f"{cam['ip_address']}/Streaming/Channels/101"
        )

        _logger.info(f"[Camera {cam_id}] Kết nối RTSP: {rtsp_url}")

        cmd = [
            r"C:\Users\Administrator\Downloads\ffmpeg-8.0.1-essentials_build\bin\ffmpeg.exe",
            "-rtsp_transport", "tcp",
            "-i", rtsp_url,
            "-q:v", "5",
            "-r", "10",  # 10 FPS
            "-vf", "scale=640:360",
            "-f", "mjpeg",
            "-"
        ]

        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=10 ** 8
            )
            _logger.info(f"[Camera {cam_id}] FFmpeg PID: {proc.pid}")
        except Exception as e:
            _logger.error(f"[Camera {cam_id}] Không khởi động được FFmpeg: {e}")
            return

        # Đọc MJPEG frames
        try:
            while cam_id in _active_streams:
                # Đọc đến khi thấy JPEG marker
                frame = CameraDevice._read_mjpeg_frame(proc.stdout)

                if frame:
                    CameraDevice.buffer_dict[cam_id] = frame
                    _logger.debug(f"[Camera {cam_id}] Frame mới: {len(frame)} bytes")
                else:
                    _logger.warning(f"[Camera {cam_id}] Frame rỗng")

                # Kiểm tra FFmpeg còn sống không
                if proc.poll() is not None:
                    stderr = proc.stderr.read().decode(errors="ignore")
                    _logger.error(f"[Camera {cam_id}] FFmpeg crash:\n{stderr}")
                    break

        except Exception as e:
            _logger.error(f"[Camera {cam_id}] Lỗi đọc stream: {e}")
        finally:
            proc.terminate()
            proc.wait()
            _active_streams.pop(cam_id, None)
            CameraDevice.buffer_dict.pop(cam_id, None)
            _logger.info(f"[Camera {cam_id}] Stream đã dừng")

    @staticmethod
    def _read_mjpeg_frame(stream):
        """Đọc 1 JPEG frame hoàn chỉnh từ MJPEG stream"""
        SOI = b'\xff\xd8'  # Start of Image
        EOI = b'\xff\xd9'  # End of Image

        # Tìm SOI
        chunk = stream.read(2)
        while chunk and chunk != SOI:
            chunk = chunk[1:] + stream.read(1)

        if not chunk:
            return None

        # Đọc đến EOI
        frame = SOI
        while True:
            byte = stream.read(1)
            if not byte:
                return None
            frame += byte
            if frame[-2:] == EOI:
                return frame