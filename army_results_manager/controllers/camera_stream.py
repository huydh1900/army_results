from odoo import http
from odoo.http import request


class CameraController(http.Controller):

    @http.route('/mjpeg/<int:camera_id>', type='http', auth='user')
    def stream_mjpeg(self, camera_id):
        """Trả về MJPEG stream"""
        CameraDevice = request.env['camera.device']

        def generate():
            while True:
                frame = CameraDevice.buffer_dict.get(camera_id)
                if frame:
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
                else:
                    # Nếu chưa có frame, chờ
                    import time
                    time.sleep(0.1)

        return request.make_response(
            generate(),
            headers=[('Content-Type', 'multipart/x-mixed-replace; boundary=frame')]
        )
