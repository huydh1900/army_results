/** @odoo-module **/

import {Component} from "@odoo/owl";
import {registry} from "@web/core/registry";

export class CameraFullScreen extends Component {
    setup() {
    }

    openCamera(cam) {
        // ví dụ: mở tab mới
        window.open(cam.stream_url, "_blank");
    }
// http://10.0.70.2/camera/index.html
}

CameraFullScreen.template = "camera_fullscreen_view"
registry.category("actions").add("camera.fullscreen", CameraFullScreen);