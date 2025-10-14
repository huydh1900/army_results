/** @odoo-module **/
import {Component, onMounted, useRef} from "@odoo/owl";
import {useService} from "@web/core/utils/hooks";

export class TrainTheUnitComponent extends Component {
    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
    }

    async getUnitItemData(){
        const data = await this.orm.call("training.plan", "get_participants_ids", []);
    }
}

TrainTheUnitComponent.template = "army_results_manager.TrainTheUnitTemplate";
