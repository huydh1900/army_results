from odoo import models, fields, api
import threading
import logging
import subprocess
import datetime
import os
import time

_logger = logging.getLogger(__name__)

# Dictionary global
_active_streams = {}
_recording_processes = {}  # Lưu FFmpeg process
_recording_locks = {}  # Lock để tránh race condition


class CameraDevice(models.Model):
    _name = "camera.device"
    _rec_name = "name"

    name = fields.Char("Tên Camera")
    ip_address = fields.Char("IP Camera")
    username = fields.Char("User", default="admin")
    password = fields.Char("Password", default="")
    port = fields.Char("Port")
    is_streaming = fields.Boolean("Đang Stream", default=False)

    buffer_dict = {}
    mjpeg_url = fields.Char(compute="_compute_mjpeg_url")

    def _compute_mjpeg_url(self):
        for rec in self:
            rec.mjpeg_url = f"/mjpeg/{rec.id}"

    # ==================== START STREAM ====================
    def start_stream(self):
        self.ensure_one()
        _logger.info(f"[Camera {self.id}] Bắt đầu stream...")

        # if self.id in _active_streams:
        #     _logger.warning(f"[Camera {self.id}] Stream đã chạy rồi!")
        #     return {
        #         "type": "ir.actions.act_url",
        #         "url": self.mjpeg_url,
        #         "target": "new",
        #     }

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

        # return {
        #     "type": "ir.actions.act_url",
        #     "url": self.mjpeg_url,
        #     "target": "new",
        # }

    def stop_stream(self):
        self.ensure_one()
        _logger.info(f"[Camera {self.id}] Dừng stream...")
        _active_streams.pop(self.id, None)
        self.write({"is_streaming": False})
        CameraDevice.buffer_dict.pop(self.id, None)

    # ==================== START RECORDING ====================
    def start_recording(self):
        """Bắt đầu ghi video"""
        self.ensure_one()

        # Tạo lock nếu chưa có
        if self.id not in _recording_locks:
            _recording_locks[self.id] = threading.Lock()

        # Kiểm tra với lock
        with _recording_locks[self.id]:
            if self.id in _recording_processes:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'message': 'Camera đang ghi video rồi!',
                        'type': 'warning'
                    }
                }

            # Tạo tên file
            now = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"camera_{self.id}_{now}.mp4"

            output_dir = r"C:\CameraRecordings"
            os.makedirs(output_dir, exist_ok=True)

            filepath = os.path.join(output_dir, filename)

            rtsp_url = f"rtsp://{self.username}:{self.password}@{self.ip_address}/Streaming/Channels/101"

            # THÊM -use_wallclock_as_timestamps 1 để tránh lỗi timestamp
            cmd = [
                r"C:\Users\Administrator\Downloads\ffmpeg-8.0.1-essentials_build\bin\ffmpeg.exe",
                "-y",
                "-rtsp_transport", "tcp",
                "-use_wallclock_as_timestamps", "1",
                "-i", rtsp_url,
                "-c:v", "copy",
                "-an",
                "-movflags", "+faststart",
                filepath
            ]

            try:
                proc = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    stdin=subprocess.PIPE
                )

                _recording_processes[self.id] = {
                    'process': proc,
                    'filepath': filepath,
                    'filename': filename,
                    'start_time': time.time()
                }

                # CẬP NHẬT NGAY LẬP TỨC (không đợi commit)
                # self.write({'is_recording': True})
                self.env.cr.commit()  # Force commit ngay

                _logger.info(f"[Camera {self.id}] Bắt đầu ghi: {filename}")

                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'message': f'Đang ghi video: {filename}',
                        'type': 'success'
                    }
                }

            except Exception as e:
                _logger.error(f"[Camera {self.id}] Lỗi start recording: {e}")
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'message': f'Lỗi: {str(e)}',
                        'type': 'danger'
                    }
                }

    # ==================== STOP RECORDING ====================
    def stop_recording(self):
        """Dừng ghi video"""
        self.ensure_one()

        if self.id not in _recording_locks:
            _recording_locks[self.id] = threading.Lock()

        with _recording_locks[self.id]:
            if self.id not in _recording_processes:
                _logger.warning(f"[Camera {self.id}] Không có video đang ghi!")
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'message': 'Không có video đang ghi!',
                        'type': 'warning'
                    }
                }

            rec_data = _recording_processes[self.id]
            proc = rec_data['process']
            filepath = rec_data['filepath']
            filename = rec_data['filename']

            # CẬP NHẬT TRẠNG THÁI NGAY (trước khi thread chạy)
            # self.write({'is_recording': False})
            self.env.cr.commit()  # Force commit ngay

            # Chạy stop trong thread riêng
            threading.Thread(
                target=self._stop_recording_async,
                args=(proc, self.id, filepath, filename),
                daemon=True
            ).start()

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': f'Đang dừng ghi video: {filename}',
                    'type': 'info'
                }
            }

    def _stop_recording_async(self, proc, cam_id, filepath, filename):
        """Chạy trong thread riêng để đợi FFmpeg dừng"""
        try:
            _logger.info(f"[Camera {cam_id}] Gửi lệnh 'q' tới FFmpeg...")

            # Gửi 'q' để FFmpeg dừng GRACEFULLY (finalize video properly)
            proc.stdin.write(b'q')
            proc.stdin.flush()

            # Đợi tối đa 10 giây
            proc.wait(timeout=10)

            _logger.info(f"[Camera {cam_id}] FFmpeg đã dừng sạch")

        except subprocess.TimeoutExpired:
            _logger.warning(f"[Camera {cam_id}] FFmpeg không phản hồi, kill process")
            proc.kill()
            proc.wait()

        except Exception as e:
            _logger.error(f"[Camera {cam_id}] Lỗi khi dừng FFmpeg: {e}")
            try:
                proc.kill()
            except:
                pass

        finally:
            # Xóa khỏi dict
            with _recording_locks[cam_id]:
                _recording_processes.pop(cam_id, None)

            # Đợi một chút để file được flush
            time.sleep(1)

            # Kiểm tra file
            if os.path.exists(filepath):
                filesize = os.path.getsize(filepath)
                _logger.info(f"[Camera {cam_id}] Video đã lưu: {filepath} ({filesize} bytes)")

                # Tạo record trong database
                try:
                    with api.Environment.manage():
                        with self.env.registry.cursor() as new_cr:
                            new_env = api.Environment(new_cr, self.env.uid, self.env.context)
                            new_env['camera.video'].create({
                                'name': filename,
                                'camera_id': cam_id,
                                'filepath': filepath,
                                'filesize': filesize
                            })
                            new_cr.commit()
                            _logger.info(f"[Camera {cam_id}] Đã tạo record camera.video")
                except Exception as e:
                    _logger.error(f"[Camera {cam_id}] Không tạo được record: {e}")
            else:
                _logger.error(f"[Camera {cam_id}] File không tồn tại: {filepath}")

    # ==================== STREAM WORKER ====================
    @staticmethod
    def _stream_worker(cam):
        cam_id = cam["id"]
        rtsp_url = f"rtsp://{cam['username']}:{cam['password']}@{cam['ip_address']}/Streaming/Channels/101"

        _logger.info(f"[Camera {cam_id}] Kết nối RTSP: {rtsp_url}")

        cmd = [
            r"C:\Users\Administrator\Downloads\ffmpeg-8.0.1-essentials_build\bin\ffmpeg.exe",
            "-rtsp_transport", "tcp",
            "-i", rtsp_url,
            "-q:v", "5",
            "-r", "10",
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

        try:
            while cam_id in _active_streams:
                frame = CameraDevice._read_mjpeg_frame(proc.stdout)

                if frame:
                    CameraDevice.buffer_dict[cam_id] = frame
                    _logger.debug(f"[Camera {cam_id}] Frame mới: {len(frame)} bytes")

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
        SOI = b'\xff\xd8'
        EOI = b'\xff\xd9'

        chunk = stream.read(2)
        while chunk and chunk != SOI:
            chunk = chunk[1:] + stream.read(1)

        if not chunk:
            return None

        frame = SOI
        while True:
            byte = stream.read(1)
            if not byte:
                return None
            frame += byte
            if frame[-2:] == EOI:
                return frame
