/** @odoo-module **/
import {Component, onMounted, useState} from "@odoo/owl";
import {useService} from "@web/core/utils/hooks";

export class TrainingResultComponent extends Component {
    setup() {
        this.orm = useService("orm");
        this.state = useState({units: []});
        this.state = useState({
            totalStudents: 0,
            goodStudents: 0,
            failStudents: 0,
            trainingStudents: 0,
            conclusion: "",
        });
        onMounted(() => this.countStudentSummary());
    }

    async countStudentSummary() {
        const summary = await this.orm.call("hr.employee", "count_student_summary", []);

        this.state.totalStudents = summary.total || 0;
        this.state.goodStudents = summary.good || 0;
        this.state.failStudents = summary.fail || 0;
        this.state.trainingStudents = summary.training || 0;

        this.generateConclusion();
    }

    generateConclusion() {
        const { totalStudents, goodStudents, failStudents, trainingStudents } = this.state;

        if (totalStudents === 0) {
            this.state.conclusion = "Chưa có dữ liệu học viên để đánh giá.";
            return;
        }

        const goodRate = ((goodStudents / totalStudents) * 100).toFixed(1);
        const failRate = ((failStudents / totalStudents) * 100).toFixed(1);
        const trainingRate = ((trainingStudents / totalStudents) * 100).toFixed(1);

        // 👉 Tạo kết luận động
        if (goodRate >= 80) {
            this.state.conclusion = `Tỷ lệ hoàn thành xuất sắc với ${goodRate}% đạt chuẩn.`;
        } else if (goodRate >= 60) {
            this.state.conclusion = `Kết quả khá tốt, ${goodRate}% học viên đạt chuẩn.`;
        } else {
            this.state.conclusion = `Tỷ lệ đạt chuẩn thấp (${goodRate}%), cần xem xét lại quá trình huấn luyện.`;
        }
    }

}

TrainingResultComponent.template = "army_results_manager.TrainingResultTemplate";
