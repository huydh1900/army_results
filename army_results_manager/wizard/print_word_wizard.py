# -*- coding: utf-8 -*-
from odoo import models, fields
from odoo.modules.module import get_module_resource
from io import BytesIO
import base64
from docx import Document
from docx.shared import Cm
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_ALIGN_VERTICAL
from docx.shared import Pt


class PrintWordWizard(models.TransientModel):
    _name = "print.word.wizard"
    _description = "Wizard chọn mẫu in Word/Excel"

    mau_in = fields.Selection(
        [('template1', 'Phụ lục 1'),
         ('template2', 'Phụ lục 2'),
         ('template3', 'Phụ lục 3'),
         ('template4', 'Phụ lục 4'),
         ('template5', 'Phụ lục 5')],
        string="Chọn mẫu phụ lục ", required=True, default='template1'
    )

    def action_print_word(self):
        active_ids = self.env.context.get("active_ids", [])
        records = self.env['training.course'].browse(active_ids)
        record_names = [rec.name for rec in records]

        rows_data_table_1 = [
            ("1.1", "Bắt đầu huấn luyện", "start_date"),
            ("1.2", "Kết thúc huấn luyện", "end_date"),
            ("1.3", "Tổng số thời gian", "total_hours"),
            ("1.4", "Số tuần huấn luyện", ""),
            ("1.5", "Số ngày huấn luyện", ""),
            ("1.6", "Số ngày nghỉ", ""),
            ("a", "Nghỉ thứ 7 + CN", ""),
            ("b", "Nghỉ lễ, Tết", ""),
        ]
        rows_data_table_2 = [
            ("a", "Tổng số thời gian huấn luyện", "total_hours"),
            ("b", "Huấn luyện chung", "total_hours_type_common"),
            ("", "Giáo dục chính trị, nghị quyết, pháp luật", ""),
            ("", "Huấn luyện quân sự chung", ""),
            ("c", "Huấn luyện riêng", "total_hours_type_private"),
            ("", "Huấn luyện các bài bắn theo Quy chế, Điều lệ", ""),
            ("", "Huấn luyện thể lực", ""),
            ("d", "Học tiếng Anh ngoại khoá buổi tối (thứ 3, 5 hàng tuần)", ""),
        ]

        # Chọn template Word theo mau_in
        template_map = {
            'template1': 'army_results_manager/static/src/word/template1.docx',
            'template2': 'army_results_manager/static/src/word/template2.docx',
            'template3': 'army_results_manager/static/src/word/template3.docx',
            'template4': 'army_results_manager/static/src/word/template4.docx',
            'template5': 'army_results_manager/static/src/word/template5.docx',
        }

        template_path = get_module_resource('army_results_manager', 'static', 'src', 'word', f'{self.mau_in}.docx')
        doc = Document(template_path)

        def bold_cell_text(cell):
            """In đậm toàn bộ chữ trong ô Word."""
            for paragraph in cell.paragraphs:
                for run in paragraph.runs:
                    run.bold = True

        def center_cell_text(cell):
            # Canh ngang
            for paragraph in cell.paragraphs:
                paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
            # Canh dọc
            cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER

        def left_cell_text(cell):
            for paragraph in cell.paragraphs:
                paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT

        def set_column_width(cell, width_cm):
            """Set độ rộng cell trong Word."""
            cell.width = Cm(width_cm)
            tcPr = cell._tc.get_or_add_tcPr()
            tcW = OxmlElement('w:tcW')
            tcW.set(qn('w:w'), str(int(width_cm * 567)))
            tcW.set(qn('w:type'), 'dxa')
            tcPr.append(tcW)

        def replace_placeholder_with_table(doc, placeholder, records, rows_data, note=None):
            """
            Thay placeholder bằng bảng, có thể thêm cột Ghi chú
            - records: list record (có .name)
            - rows_data: [(tt, label, field), ...]
            """
            for para in doc.paragraphs:
                if placeholder not in para.text:
                    continue

                # Xóa placeholder
                parent = para._element.getparent()
                idx = parent.index(para._element)
                parent.remove(para._element)

                num_records = len(records)
                num_cols = 2 + num_records + (1 if note else 0)
                num_rows = 2 + len(rows_data)

                # Tạo table
                table = doc.add_table(rows=num_rows, cols=num_cols)
                table.style = 'Table Grid'

                # --- Set width động ---
                tt_width, nd_width, total_time_width = 1.2, 15, 25
                record_width = total_time_width / num_records if num_records else total_time_width
                widths = [tt_width, nd_width] + [record_width] * num_records
                if note:
                    widths.append(5)

                for row in table.rows:
                    for cell, w in zip(row.cells, widths):
                        set_column_width(cell, w)

                # --- Helper để format cell ---
                def cell_set(cell, text, align='center', bold=False):
                    cell.text = str(text)
                    if align == 'center':
                        center_cell_text(cell)
                    elif align == 'left':
                        left_cell_text(cell)
                    if bold:
                        bold_cell_text(cell)

                # --- Header ---
                # TT
                table.cell(0, 0).merge(table.cell(1, 0))
                cell_set(table.cell(0, 0), "TT", bold=True)

                # Nội dung
                table.cell(0, 1).merge(table.cell(1, 1))
                cell_set(table.cell(0, 1), "Nội dung", bold=True)

                # Thời gian (các record)
                if num_records > 0:
                    table.cell(0, 2).merge(table.cell(0, 1 + num_records))
                    cell_set(table.cell(0, 2), "Thời gian", bold=True)
                    for i, rec in enumerate(records):
                        cell_set(table.cell(1, 2 + i), rec.name, bold=True)

                # Ghi chú
                if note:
                    table.cell(0, num_cols - 1).merge(table.cell(1, num_cols - 1))
                    cell_set(table.cell(0, num_cols - 1), "Ghi chú", bold=True)

                # --- Dữ liệu ---
                for r_idx, (tt, label, field) in enumerate(rows_data, start=2):
                    cell_set(table.cell(r_idx, 0), tt)  # TT
                    cell_set(table.cell(r_idx, 1), label, align='left')  # label

                    for c_idx, rec in enumerate(records):
                        value = getattr(rec, field, '') or ''
                        cell_set(table.cell(r_idx, 2 + c_idx), value)

                    if note:
                        cell_set(table.cell(r_idx, num_cols - 1), note)

                # Insert table vào document
                parent.insert(idx, table._element)
                break

        from docx.shared import Pt
        from docx.enum.text import WD_ALIGN_PARAGRAPH

        def create_sample_table(doc):
            cols = 15
            rows = 3  # 2 hàng header + ít nhất 1 hàng dữ liệu

            table = doc.add_table(rows=rows, cols=cols)
            table.style = "Table Grid"

            # === Header ===
            # gộp 2 hàng đầu cho TT, Đối tượng, Tổng số
            table.cell(0, 0).merge(table.cell(1, 0)).text = "TT"
            table.cell(0, 1).merge(table.cell(1, 1)).text = "Đối tượng"
            table.cell(0, 2).merge(table.cell(1, 2)).text = "Tổng số\n(giờ)"

            # nhóm huấn luyện chung (colspan 7 cột: từ 3..9)
            table.cell(0, 3).merge(table.cell(0, 9)).text = "Huấn luyện chung"
            headers_hlc = ["+ (%)", "Chính trị", "GD pháp luật", "Hậu cần",
                           "Kỹ thuật", "Điều lệnh", "Kỹ thuật CĐBB"]
            for j, text in enumerate(headers_hlc, start=3):
                table.cell(1, j).text = text

            # nhóm huấn luyện riêng (colspan 4 cột: từ 10..13)
            table.cell(0, 10).merge(table.cell(0, 13)).text = "Huấn luyện riêng"
            headers_hlr = ["+ (%)", "Bắn súng", "Thể lực", "Tiếng Anh"]
            for j, text in enumerate(headers_hlr, start=10):
                table.cell(1, j).text = text

            # ghi chú
            table.cell(0, 14).merge(table.cell(1, 14)).text = "Ghi chú"

            # căn giữa + bold cho header
            for i in range(2):
                for j in range(cols):
                    p = table.cell(i, j).paragraphs[0]
                    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    if p.runs:
                        p.runs[0].font.bold = True
                        p.runs[0].font.size = Pt(10)

            # === Hàng dữ liệu ví dụ ===
            i = 2
            table.cell(i, 0).text = "4.1"
            table.cell(i, 1).text = "Hội thi AASAM-2025"
            table.cell(i, 2).text = "1.530\n100%"

            # Huấn luyện chung: mỗi ô 2 dòng (số + %)
            hlc_values = ["100\n6,5%", "41\n3,8%", "18\n", "06\n", "04\n2,7%", "25\n", "06\n"]
            for j, val in enumerate(hlc_values, start=3):
                cell = table.cell(i, j)
                cell.text = val
                p = cell.paragraphs[0]
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                if p.runs:
                    p.runs[0].font.size = Pt(10)

            # Huấn luyện riêng
            hlr_values = ["1.430\n93,5%", "1024\n66,9%", "406\n26,6%", "51\n"]
            for j, val in enumerate(hlr_values, start=10):
                cell = table.cell(i, j)
                cell.text = val
                p = cell.paragraphs[0]
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                if p.runs:
                    p.runs[0].font.size = Pt(10)

            # ghi chú
            table.cell(i, 14).text = ""

            # căn trái cột Đối tượng
            table.cell(i, 1).paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.LEFT

            return table

        def replace_placeholder_with_table_3(doc, placeholder, records, note_text=None):
            """Tìm {{table_3}} và thay bằng bảng Table_3 tạo từ records"""
            for para in doc.paragraphs:
                if placeholder in para.text:
                    # lấy element cha của paragraph
                    p = para._element
                    parent = p.getparent()
                    idx = parent.index(p)

                    # xoá paragraph chứa placeholder
                    parent.remove(p)

                    # tạo bảng mới
                    table = create_sample_table(doc)

                    # chèn bảng mới vào đúng vị trí paragraph vừa xoá
                    parent.insert(idx, table._element)

                    break

        replace_placeholder_with_table(doc, "{{table_1}}", records, rows_data=rows_data_table_1)
        replace_placeholder_with_table_3(doc, "{{table_3}}", records)

        replace_placeholder_with_table(doc, "{{table_2}}", records, rows_data=rows_data_table_2, note=" ")
        # Xuất file Word
        file_data = BytesIO()
        doc.save(file_data)
        file_data.seek(0)
        data = base64.b64encode(file_data.read())

        # Tạo attachment tạm thời để download
        attachment = self.env['ir.attachment'].create({
            'name': f'{self.mau_in}.docx',
            'type': 'binary',
            'datas': data,
            'res_model': self._name,
            'res_id': self.id,
            'mimetype': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'new',
        }
