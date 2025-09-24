/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component } from "@odoo/owl";
import { ActionContainer } from "@web/webclient/actions/action_container";
import { View } from "@web/views/view";
import { ControlPanel } from "@web/search/control_panel/control_panel";


export class TrainingPlan extends Component {
    static components = { ActionContainer };
}

TrainingPlan.template = "army_results_manager.TrainingPlanTemplate";
TrainingPlan.components = {ControlPanel, View};

registry.category("actions").add("training_plan", TrainingPlan);
