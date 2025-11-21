from odoo import http
from odoo.http import Response
from ..models.camera_device import buffer_dict

class CameraStream(http.Controller):

    @http.route('/mjpeg/<int:camera_id>', type='http', auth='public')
    def mjpeg(self, camera_id, **kwargs):
        def generate():
            while True:
                frame = buffer_dict.get(camera_id)
                if frame:
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
        return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')
