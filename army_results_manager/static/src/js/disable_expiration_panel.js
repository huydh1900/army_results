/** @odoo-module **/

import { registry } from "@web/core/registry";

// Gỡ component cảnh báo hết hạn DB khỏi hệ thống
registry.category("main_components").remove("database_expiration_panel");
