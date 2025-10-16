/** @odoo-module **/
import {Component, onMounted, useState} from "@odoo/owl";
import {useService} from "@web/core/utils/hooks";

export class TrainTheUnitComponent extends Component {
    setup() {
        this.orm = useService("orm");
        this.state = useState({units: []});
        onMounted(() => this.getUnitItemData());
    }

    async getUnitItemData() {
        const data = await this.orm.call("training.course", "get_list_course", []);
        this.state.units = data;
    }

    getProgressColor(percent) {
        if (percent < 40) return "progress_red";
        if (percent < 80) return "progress_yellow";
        return "progress_green";
    }
}

TrainTheUnitComponent.template = "army_results_manager.TrainTheUnitTemplate";
