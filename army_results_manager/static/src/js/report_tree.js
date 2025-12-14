/** @odoo-module */
import {ListController} from "@web/views/list/list_controller";
import {registry} from '@web/core/registry';
import {listView} from '@web/views/list/list_view';
import {useService} from "@web/core/utils/hooks";

const {useState, onWillStart} = owl;

export class ReportListController extends ListController {
    setup() {
        super.setup();
        this.actionService = useService("action");
        this.user = useService("user");
        this.isStudent = false;
        this.state = useState({
            countWait: 0,
            countWaitPlan: 0,
            countSigned: 0,
            countSignedPlan: 0,
            cameras: [],
        });
        onWillStart(async () => {
            await this.fetchDocumentCounts();
            this.isStudent = await this.user.hasGroup(
                "army_results_manager.group_training_student"
            );
        });
    }

    OnOpenWizardPrint() {
        this.actionService.doAction({
            type: 'ir.actions.act_window',
            res_model: 'print.score.wizard',
            name: 'In kết quả huấn luyện',
            view_mode: "form",
            target: "new",
            views: [[false, "form"]],
            context: {
                'active_model': 'training.result',
            }
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

    async openFullscreen(rows, cols) {
        const totalSlots = rows * cols;
        const records = this.model.root.records;
        const cameraIds = records.map(r => r.resId);
        const camerasData = await this.env.services.orm.searchRead(
            "camera.device",
            [["id", "in", cameraIds]],
            ["id", "name", "ip_address"]
        );

        // Chuyển dữ liệu camera
        let cameras = records.map(r => {
            const cam = camerasData.find(c => c.id === r.resId);
            return {
                id: r.resId,
                empty: false,
                name: cam ? cam.name : r.data.name,
                mjpeg_url: `/camera/proxy/${r.resId}`,
                axis_url: cam ? `http://${cam.ip_address}` : "#",
            };
        });

        // Thêm slot trống nếu thiếu
        while (cameras.length < totalSlots) {
            cameras.push({
                id: `empty_${cameras.length}`,
                empty: true,
            });
        }

        // Giới hạn số camera đúng totalSlots
        cameras = cameras.slice(0, totalSlots);

        // Mở fullscreen view
        this.actionService.doAction({
            type: "ir.actions.client",
            tag: "camera.fullscreen",
            params: {cameras, rows, cols},
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
            [['is_signed', '=', true], ['approver_id.user_id', '=', uid]]
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
        console.log(this.state)

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
            context: {
                edit: false,
            }
        });
    }

}

registry.category("views").add("button_in_tree", {
    ...listView,
    Controller: ReportListController,
    buttonTemplate: "button_report.ListView.Buttons",
});