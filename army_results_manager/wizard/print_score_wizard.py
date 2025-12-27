from docxtpl import DocxTemplate
from docx import Document
import base64
from odoo import models, fields
from odoo.modules.module import get_module_resource
import tempfile
import os
from odoo.exceptions import UserError
import subprocess


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
        result_counter = {label: 0 for label in result_map.values()}
        total = len(result_records) if result_records else 1

        for rec in result_records:
            label = result_map.get(rec.result, "")
            if label in result_counter:
                result_counter[label] += 1

        result_percent = {label: round((count / total) * 100, 2) for label, count in result_counter.items()}
        summary_result = (
            f"Không đạt: {result_percent.get('Không đạt',0)}%, "
            f"Đạt: {result_percent.get('Đạt',0)}%, "
            f"TB: {result_percent.get('Trung bình',0)}%, "
            f"Khá: {result_percent.get('Khá',0)}%, "
            f"Giỏi: {result_percent.get('Xuất sắc',0)}%"
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

        tmp_docx_path = tempfile.NamedTemporaryFile(delete=False, suffix=".docx").name
        tpl.save(tmp_docx_path)

        # ==== 2. MỞ LẠI FILE WORD → CHÈN BẢNG HỌC VIÊN ====
        doc = Document(tmp_docx_path)
        table = None
        for tbl in doc.tables:
            if "TT" in tbl.rows[0].cells[0].text:
                table = tbl
                break

        if not table:
            raise UserError("Không tìm thấy bảng danh sách học viên trong file Word!")

        for st in students_list:
            row = table.add_row().cells
            row[0].text = str(st['id'])
            row[1].text = st['shsq']
            row[2].text = st['full_name']
            row[3].text = str(st['score'])
            row[4].text = str(st['rank'])
            row[5].text = st['note']

        final_docx_path = tempfile.NamedTemporaryFile(delete=False, suffix=".docx").name
        doc.save(final_docx_path)

        # ==== 3. CONVERT DOCX → PDF BẰNG LIBREOFFICE (LINUX) ====
        pdf_path = final_docx_path.replace(".docx", ".pdf")
        try:
            subprocess.run([
                "libreoffice", "--headless", "--convert-to", "pdf",
                final_docx_path, "--outdir", os.path.dirname(pdf_path)
            ], check=True)

            with open(pdf_path, 'rb') as f:
                pdf_content = f.read()

            # TẠO ATTACHMENT TẠM
            attachment = self.env['ir.attachment'].create({
                'name': f"Ket_qua_huan_luyen_{self.course_id.display_name}_{self.plan_id.name}.pdf",
                'type': 'binary',
                'datas': base64.b64encode(pdf_content),
                'mimetype': 'application/pdf',
            })

            # Dọn dẹp file tạm
            if os.path.exists(final_docx_path): os.unlink(final_docx_path)
            if os.path.exists(pdf_path): os.unlink(pdf_path)
            if os.path.exists(tmp_docx_path): os.unlink(tmp_docx_path)

            # TRẢ VỀ URL CHUẨN ODOO (preview PDF)
            return {
                "type": "ir.actions.act_url",
                "url": f"/web/content/{attachment.id}?download=false",
                "target": "new",
            }

        except subprocess.CalledProcessError as e:
            raise UserError(f"Lỗi convert PDF trên server Linux: {str(e)}")
