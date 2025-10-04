/** @odoo-module **/
import { Component, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";

class TrainingDashboard extends Component {
    setup() {
       
    }
}

// Template phải khớp với t-name trong XML
TrainingDashboard.template = "army_results_manager.TrainingDashboardTemplate";

// Đăng ký action, phải khớp với tag trong ir.actions.client
registry.category("actions").add("training_dashboard_action", TrainingDashboard);

export default TrainingDashboard;
