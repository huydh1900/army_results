/** @odoo-module **/
import { Component, onMounted, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class WarningImportantComponent extends Component {
    setup() {
        this.orm = useService("orm");
        this.state = useState({ warnings: [] });

        onMounted(() => this.getDailyWarnings());
    }

    async getDailyWarnings() {
        try {
            const logs = await this.orm.searchRead(
                "training.warning.log",
                [],
                ["date", "message"]
            );

            // Sắp xếp log mới nhất lên đầu
            logs.sort((a, b) => new Date(b.date) - new Date(a.date));

            // Gán dữ liệu vào state để OWL tự cập nhật UI
            this.state.warnings = logs;
            console.log(this.state.warnings)
        } catch (error) {
            console.error("Lỗi khi tải cảnh báo:", error);
        }
    }
}

WarningImportantComponent.template = "army_results_manager.WarningImportantTemplate";
