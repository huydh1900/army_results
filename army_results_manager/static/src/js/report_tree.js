/** @odoo-module */
import {ListController} from "@web/views/list/list_controller";
import {registry} from '@web/core/registry';
import {listView} from '@web/views/list/list_view';
import {useService} from "@web/core/utils/hooks";

export class ReportListController extends ListController {
    setup() {
        super.setup();
        this.actionService = useService("action");
    }

    OnOpenWizard() {
        this.actionService.doAction({
            type: 'ir.actions.act_window',
            res_model: 'print.word.wizard',
            name: 'In Báo cáo',
            view_mode: "form",
            target: "new",
            views: [[false, "form"]],
        });
    }
}

registry.category("views").add("button_in_tree", {
    ...listView,
    Controller: ReportListController,
    buttonTemplate: "button_report.ListView.Buttons",
});