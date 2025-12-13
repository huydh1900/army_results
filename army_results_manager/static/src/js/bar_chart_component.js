/** @odoo-module **/
import {Component, onMounted, useRef} from "@odoo/owl";
import {useService} from "@web/core/utils/hooks";

export class BarChartComponent extends Component {
    setup() {
        this.canvasRef = useRef("canvasRef");
        this.orm = useService("orm");
        this.actionService = useService("action");

        onMounted(() => this.renderChart());
    }

    async renderChart() {
        const ctx = this.canvasRef.el.getContext("2d");

        if (!window.Chart) {
            console.error("Chart.js chưa load!");
            return;
        }
        const chartData = await this.orm.call("training.schedule", "get_training_state_summary", []);

        const data = {
            labels: chartData.map(d => d.label),
            datasets: [{
                data: chartData.map(d => d.value),
                backgroundColor: [
                    "rgba(107, 114, 128, 1)",  // draft
                    "rgba(234, 179, 8, 1)",    // to_modify
                    "rgba(245, 107, 87, 0.8)", // not_done
                    "rgba(37, 99, 235, 1)",    // posted
                    "rgba(22, 163, 74, 1)",    // approved
                    "rgba(220, 38, 38, 1)"     // cancel
                ],
            }],
        };

        const options = {
            responsive: true,
            plugins: {
                legend: {display: false},
                tooltip: {enabled: true},
            },
            onClick: (event, elements) => {
                const el = elements?.[0];
                if (!el) return;
                const index = el.index;
                const clickedState = chartData?.[index]?.state;
                if (clickedState) this.filterByState(clickedState);
            },
            y: {
                beginAtZero: true,
                grid: {display: true},
                ticks: {
                    stepSize: 1,
                    precision: 0,
                },
            },
        };

        new Chart(ctx, {type: "bar", data, options});
    }

    filterByState(state) {
        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: "Kế hoạch huấn luyện",
            res_model: "training.schedule",
            views: [[false, "list"], [false, "form"]],
            domain: [["state", "=", state]],
        });
    }
}

BarChartComponent.template = "army_results_manager.BarChartTemplate";
