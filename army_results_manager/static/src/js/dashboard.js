/** @odoo-module */
import {registry} from "@web/core/registry"
import { Component } from "@odoo/owl";
import {useService} from "@web/core/utils/hooks";
import {BarChartComponent} from "./bar_chart_component";
import {TrainTheUnitComponent} from "./train_the_unit_component";
import {TrainingResultComponent} from "./training_result_component";

export class Dashboard extends Component {
    setup() {
        this.rpc = useService("rpc");
    }

}

Dashboard.template = "army_results_manager.DashboardTemplate"
Dashboard.components = {
    BarChartComponent,
    TrainTheUnitComponent,
    TrainingResultComponent
};
registry.category("actions").add("army_dashboard", Dashboard)