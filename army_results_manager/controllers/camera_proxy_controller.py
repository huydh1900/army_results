from odoo import http
from odoo.http import request, Response
import requests
from requests.auth import HTTPDigestAuth

class CameraProxyController(http.Controller):

    @http.route('/camera/proxy/<int:camera_id>', type='http', auth='user')
    def camera_proxy(self, camera_id, **kwargs):
        # Lấy thông tin camera
        camera = request.env['camera.device'].sudo().browse(camera_id)
        if not camera.exists():
            return Response("Camera không tồn tại", status=404)

        # URL video stream (MJPEG/RTSP qua MJPEG)
        camera_url = f"http://{camera.ip_address}/axis-cgi/mjpg/video.cgi"

        try:
            # Gửi request Digest Auth đến camera
            resp = requests.get(
                camera_url,
                auth=HTTPDigestAuth(camera.username, camera.password),
                stream=True,
                timeout=10
            )

            # Nếu không thành công
            if resp.status_code != 200:
                return Response(f"Lỗi camera ({resp.status_code})", status=resp.status_code)

            # Trả stream về trình duyệt
            return Response(
                resp.iter_content(chunk_size=1024),
                content_type=resp.headers.get('Content-Type', 'video/x-motion-jpeg'),
                status=200
            )

        except requests.exceptions.RequestException as e:
            return Response(f"Lỗi kết nối: {str(e)}", status=500)

    @http.route('/camera/snapshot/<int:camera_id>', type='http', auth='user')
    def camera_snapshot(self, camera_id, **kwargs):
        camera = request.env['camera.device'].sudo().browse(camera_id)
        if not camera.exists():
            return Response("Camera không tồn tại", status=404)

        snapshot_url = f"http://{camera.ip_address}/axis-cgi/jpg/image.cgi"
        try:
            resp = requests.get(snapshot_url, auth=HTTPDigestAuth(camera.username, camera.password), timeout=10)
            if resp.status_code != 200:
                return Response(f"Lỗi camera ({resp.status_code})", status=resp.status_code)
            return Response(resp.content, content_type='image/jpeg', status=200)
        except requests.exceptions.RequestException as e:
            return Response(f"Lỗi kết nối: {str(e)}", status=500)

