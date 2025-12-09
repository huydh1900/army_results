from docxtpl import DocxTemplate
from docx import Document
import base64
from odoo import models, fields
from odoo.modules.module import get_module_resource
import tempfile
import os


class PrintScoreWizard(models.TransientModel):
    _name = "print.score.wizard"
    _description = "Wizard chọn mẫu in kết quả khóa huấn luyện"

    plan_id = fields.Many2one("training.plan", string="Tên khóa huấn luyện", required=True)
    course_id = fields.Many2one('training.course', string='Môn học')

    def action_print_score(self):
        self.ensure_one()

        # ==== LẤY FILE TEMPLATE WORD ====
        template_path = get_module_resource(
            'army_results_manager', 'static', 'src', 'word', 'phieu_ket_qua.docx'
        )

        # ==== LẤY DỮ LIỆU TỪ training.result ====
        result_records = self.env['training.result'].search([
            ('plan_name', '=', self.plan_id.name),
            ('training_course_id', '=', self.course_id.id)
        ])

        # Chuẩn bị danh sách học viên
        students_list = []
        for index, rec in enumerate(result_records, start=1):
            student = rec.employee_id

            rank_label = dict(rec._fields['result'].selection).get(rec.result, "")
            students_list.append({
                'id': index,
                'shsq': student.identification_id or "",
                'full_name': student.name or "",
                'score': rec.score or "",
                'rank': rank_label,
                'note': "",
            })


        # ==== 1. RENDER CÁC BIẾN TEXT BẰNG DOXCTPL ====
        tpl = DocxTemplate(template_path)

        result_map = dict(self.env['training.result']._fields['result'].selection)

        # Khởi tạo bộ đếm
        result_counter = {
            "Không đạt": 0,
            "Đạt": 0,
            "Trung bình": 0,
            "Khá": 0,
            "Xuất sắc": 0,
        }

        total = len(result_records) if result_records else 1

        for rec in result_records:
            label = result_map.get(rec.result, "")
            if label in result_counter:
                result_counter[label] += 1

        # Tính %
        result_percent = {
            label: round((count / total) * 100, 2)
            for label, count in result_counter.items()
        }

        # Ghép thành chuỗi để đưa vào Word
        summary_result = (
            f"Không đạt: {result_percent['Không đạt']}%, "
            f"Đạt: {result_percent['Đạt']}%, "
            f"TB: {result_percent['Trung bình']}%, "
            f"Khá: {result_percent['Khá']}%, "
            f"Giỏi: {result_percent['Xuất sắc']}%"
        )

        context = {
            'plan_name': self.plan_id.name,
            'plan_code': self.plan_id.plan_code,
            'course_name': self.course_id.display_name,
            'year': self.plan_id.year,
            'training_officers': ', '.join(self.course_id.training_officer_ids.mapped('name')),
            'total_student': len(result_records),
            'summary_result': summary_result,
        }

        tpl.render(context)

        # Lưu file tạm sau render biến text
        tmp_docx_path = tempfile.NamedTemporaryFile(delete=False, suffix=".docx").name
        tpl.save(tmp_docx_path)

        # ==== 2. MỞ LẠI FILE WORD → CHÈN BẢNG HỌC VIÊN ====
        doc = Document(tmp_docx_path)

        # Tìm table chứa header "TT"
        table = None
        for tbl in doc.tables:
            if "TT" in tbl.rows[0].cells[0].text:
                table = tbl
                break

        if not table:
            raise UserError("Không tìm thấy bảng danh sách học viên trong file Word!")

        # Thêm từng dòng vào bảng
        for st in students_list:
            row = table.add_row().cells
            row[0].text = str(st['id'])
            row[1].text = st['shsq']
            row[2].text = st['full_name']
            row[3].text = str(st['score'])
            row[4].text = str(st['rank'])
            row[5].text = st['note']

        # Lưu file hoàn chỉnh
        final_path = tempfile.NamedTemporaryFile(delete=False, suffix=".docx").name
        doc.save(final_path)

        # ==== 3. TRẢ FILE CHO TRÌNH DUYỆT ====
        with open(final_path, 'rb') as f:
            file_data = f.read()

        data_base64 = base64.b64encode(file_data).decode()

        report_name = f"Ket_qua_huan_luyen_{self.course_id.display_name}_{self.plan_id.name}.docx".replace(" ", "_")

        attachment = self.env["ir.attachment"].create({
            "name": report_name,
            "type": "binary",
            "datas": data_base64,
            "res_model": self._name,
            "res_id": self.id,
            "mimetype": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        })

        # Xóa file tạm
        os.unlink(tmp_docx_path)
        os.unlink(final_path)

        return {
            "type": "ir.actions.act_url",
            "url": f"/web/content/{attachment.id}?download=true",
            "target": "new",
        }
