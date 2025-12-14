from odoo import http
from odoo.http import request, Response
import requests
from requests.auth import HTTPDigestAuth


class CameraProxyController(http.Controller):

    @http.route('/camera/proxy/<int:camera_id>', type='http', auth='user')
    def camera_proxy(self, camera_id, **kwargs):

        camera = request.env['camera.device'].sudo().browse(camera_id)
        if not camera.exists():
            return Response("Camera không tồn tại", status=404)

        camera_url = f"http://{camera.ip_address}/axis-cgi/mjpg/video.cgi"

        try:
            resp = requests.get(
                camera_url,
                auth=HTTPDigestAuth(camera.username, camera.password),
                stream=True,
                timeout=10
            )

            if resp.status_code != 200:
                return Response(
                    f"Lỗi camera ({resp.status_code})",
                    status=resp.status_code
                )

            def generate():
                for chunk in resp.iter_content(chunk_size=8192):
                    if chunk:
                        yield chunk

            return Response(
                generate(),  # ✅ stream generator
                headers={
                    "Content-Type": resp.headers.get(
                        "Content-Type",
                        "multipart/x-mixed-replace"
                    ),
                    "Cache-Control": "no-cache",
                    "Pragma": "no-cache",
                },
                status=200,
                direct_passthrough=True,
            )

        except requests.exceptions.RequestException as e:
            return Response(f"Lỗi kết nối: {str(e)}", status=500)