/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component } from "@odoo/owl";

class VideoViewer extends Component {}
VideoViewer.template = "army_results_manager.VideoViewer";

registry.category("fields").add("video_viewer", VideoViewer);
