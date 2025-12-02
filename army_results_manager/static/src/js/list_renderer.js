/** @odoo-module **/
import {ListRenderer} from "@web/views/list/list_renderer";
import {patch} from "@web/core/utils/patch";
import {useService} from "@web/core/utils/hooks";

patch(ListRenderer.prototype, "training_day_patch", {
    setup() {
        this._super();
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.actionService = useService("action");
        this.effect = useService('effect');
    },

    async ApprovedTrainingDay(group) {
        if (!group || !group.groupDomain) {
            this.notification.add("Không tìm thấy nhóm để duyệt.", {type: "warning"});
            return;
        }

        const domain = group.groupDomain;
        const count = group.count || 0;
        const core = require('web.core');
        const _t = core._t;

        try {
            await this.orm.call("training.day", "action_approve_by_domain", [], {domain});
            this.effect.add({
                type: 'rainbow_man',
                fadeout: "fast",
                message: _.str.sprintf(_t("Đã duyệt %s bản ghi thành công!"), count),
            });

        } catch (err) {
            console.error("Error approving by domain:", err);
        }
        this.actionService.doAction({
            'type': 'ir.actions.client',
            'tag': 'soft_reload',
        });
    },

});
