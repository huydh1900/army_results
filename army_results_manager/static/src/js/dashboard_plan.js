/** @odoo-module **/

import { Component, onMounted } from "@odoo/owl";
import { registry } from "@web/core/registry";

// Import Chart.js
import Chart from "https://cdn.jsdelivr.net/npm/chart.js";

class DashboardPlan extends Component {
    setup() {
        onMounted(() => {
            this.renderChart();
        });
    }

    renderChart() {
        const ctx = document.getElementById("trainingPlanChart").getContext("2d");
        new Chart(ctx, {
            type: "bar",
            data: {
                labels: ["Xuất sắc", "Khá", "Trung bình", "Yếu"],
                datasets: [{
                    label: "Tỉ lệ",
                    data: [30, 50, 15, 5],  // <- sau này bạn thay bằng dữ liệu thật từ backend
                    backgroundColor: [
                        "rgba(40, 167, 69, 0.8)",   // xanh lá
                        "rgba(0, 123, 255, 0.8)",   // xanh dương
                        "rgba(255, 193, 7, 0.8)",   // vàng
                        "rgba(220, 53, 69, 0.8)"    // đỏ
                    ]
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { position: "right" }
                },
                scales: {
                    y: { beginAtZero: true, max: 100 }
                }
            }
        });
    }
}

DashboardPlan.template = "army_results_manager.DashboardPlan";
registry.category("actions").add("army_results_manager.dashboard_plan", DashboardPlan);

export default DashboardPlan;
