/** @odoo-module **/

import {Component} from "@odoo/owl";
import {registry} from "@web/core/registry";

export class CameraFullScreen extends Component {
    setup() {
    }
}

CameraFullScreen.template = "camera_fullscreen_view"
registry.category("actions").add("camera.fullscreen", CameraFullScreen);