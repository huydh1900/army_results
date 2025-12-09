/** @odoo-module **/
import {Component, onMounted, useRef} from "@odoo/owl";
import {useService} from "@web/core/utils/hooks";

export class TopUnitTrainingComponent extends Component {
    setup() {
        this.canvasRef = useRef("canvasRef");
        this.orm = useService("orm");
        this.actionService = useService("action");

        onMounted(() => this.renderChart());
    }

    async renderChart() {
        const ctx = this.canvasRef.el.getContext("2d");

        if (!window.Chart) {
            return;
        }
        const chartData = await this.orm.call(
            "hr.employee",
            "get_top_department_training",
            []
        );

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

}

TopUnitTrainingComponent.template = "army_results_manager.TopUnitTrainingTemplate";
