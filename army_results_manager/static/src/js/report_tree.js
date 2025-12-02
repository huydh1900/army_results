/** @odoo-module */
import {ListController} from "@web/views/list/list_controller";
import {registry} from '@web/core/registry';
import {listView} from '@web/views/list/list_view';
import {useService} from "@web/core/utils/hooks";

const {useState, onWillStart, onMounted} = owl;

export class ReportListController extends ListController {
    setup() {
        super.setup();
        this.actionService = useService("action");
        this.state = useState({
            countWait: 0,
            countWaitPlan: 0,
            countSigned: 0,
            countSignedPlan: 0,
            cameras: [],
        });
        onWillStart(async () => {
            await this.fetchDocumentCounts();
        });
    }

    async loadCameras() {
        this.state.cameras = await this.env.services.orm.searchRead(
            "camera.device",
            [],
            ["id", "name", "ip_address"]
        );

        // Convert to stream URL
        this.state.cameras = this.state.cameras.map(c => {
            return {
                ...c,
                stream_url: `/camera/proxy/7`
            };
        });
    }

    OnOpenWizard() {
        this.actionService.doAction({
            type: 'ir.actions.act_window',
            res_model: 'print.word.wizard',
            name: 'In Báo cáo',
            view_mode: "form",
            target: "new",
            views: [[false, "form"]],
            context: {
                'active_model': 'training.day',
            }
        });
    }

    openFullscreen() {
        const records = this.model.root.records;

        const cameras = records.map(r => {
            const id = r.resId;
            return {
                id: id,
                name: r.data.name,
                stream_url: `/camera/proxy/${id}`,
            };
        });

        this.actionService.doAction({
            type: "ir.actions.client",
            tag: "camera.fullscreen",
            params: {
                cameras: cameras || [],
            },
        });

    }


    async fetchDocumentCounts() {
        const uid = this.env.services.user.userId;

        const countWait = await this.orm.call('ir.attachment', 'search_count', [
            [['is_signed', '=', false], ['create_uid', '=', uid]]
        ]);

        const countWaitPlan = await this.orm.call('ir.attachment', 'search_count', [
            [['is_signed', '=', false], ['approver_id.user_id', '=', uid]]
        ]);

        const countSigned = await this.orm.call('ir.attachment', 'search_count', [
            [['is_signed', '=', true], ['create_uid', '=', uid]]
        ]);

        const countSignedPlan = await this.orm.call('ir.attachment', 'search_count', [
            [['is_signed', '=', true], ['create_uid', '=', uid]]
        ]);

        this.state.countWait = countWait;
        this.state.countWaitPlan = countWaitPlan;
        this.state.countSigned = countSigned;
        this.state.countSignedPlan = countSignedPlan;
    }

    viewWaitDocuments() {
        const uid = this.env.services.user.userId;

        this.actionService.doAction({
            type: 'ir.actions.act_window',
            res_model: 'ir.attachment',
            name: 'Văn bản chờ ký',
            views: [["", "tree"], ["", "form"]],
            view_mode: 'tree,form',
            domain: [
                ['is_signed', '=', false],
                ['create_uid', '=', uid],
            ],
            context: {
                create: false,
                edit: false,
            }
        });
    }

    viewWaitDocumentsPlan() {
        const uid = this.env.services.user.userId;

        this.actionService.doAction({
            type: 'ir.actions.act_window',
            res_model: 'ir.attachment',
            name: 'Văn bản chờ ký',
            views: [["", "tree"], ["", "form"]],
            view_mode: 'tree,form',
            domain: [
                ['is_signed', '=', false],
                ['approver_id.user_id', '=', uid],
            ],
            context: {
                create: false,
                edit: false,
                delete: false
            }
        });
    }

    viewSignedDocumentsPlan() {
        const uid = this.env.services.user.userId;

        this.actionService.doAction({
            type: 'ir.actions.act_window',
            res_model: 'ir.attachment',
            name: 'Văn bản đã ký',
            views: [["", "tree"], ["", "form"]],
            view_mode: 'tree,form',
            domain: [
                ['is_signed', '=', true],
                ['approver_id.user_id', '=', uid],
            ],
        });
    }

    viewSignedDocuments() {
        const uid = this.env.services.user.userId;

        this.actionService.doAction({
            type: 'ir.actions.act_window',
            res_model: 'ir.attachment',
            name: 'Văn bản đã ký',
            views: [["", "tree"], ["", "form"]],
            view_mode: 'tree,form',
            domain: [
                ['is_signed', '=', true],
                ['create_uid', '=', uid],
            ],
        });
    }

}

registry.category("views").add("button_in_tree", {
    ...listView,
    Controller: ReportListController,
    buttonTemplate: "button_report.ListView.Buttons",
});