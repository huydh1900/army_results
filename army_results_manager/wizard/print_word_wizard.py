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


class PrintWordWizard(models.TransientModel):
    _name = "print.word.wizard"
    _description = "Wizard chọn mẫu in Word/Excel"

    mau_in = fields.Selection(
        [('template1', 'Phụ lục 1'),
         ('template2', 'Phụ lục 2'),
         ('template3', 'Phụ lục 3'),
         ('template4', 'Phụ lục 4'),
         ('template5', 'Phụ lục 5')],
        string="Chọn mẫu phụ lục", required=True, default='template1'
    )

    # ==================== Helper Functions ====================

    @staticmethod
    def set_column_width(cell, width_cm):
        """Set cell width in centimeters."""
        cell.width = Cm(width_cm)
        tcPr = cell._tc.get_or_add_tcPr()
        tcW = OxmlElement('w:tcW')
        tcW.set(qn('w:w'), str(int(width_cm * 567)))
        tcW.set(qn('w:type'), 'dxa')
        tcPr.append(tcW)

    @staticmethod
    def cell_set(cell, text, align='center', bold=False):
        """Set cell text and formatting."""
        cell.text = str(text) if text else ''

        # Set alignment
        alignment = WD_ALIGN_PARAGRAPH.CENTER if align == 'center' else WD_ALIGN_PARAGRAPH.LEFT
        for paragraph in cell.paragraphs:
            paragraph.alignment = alignment
            if bold:
                for run in paragraph.runs:
                    run.bold = True

        if align == 'center':
            cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER

    @staticmethod
    def calculate_hours_by_codes(courses, codes):
        """Tính tổng giờ cho các môn học theo code."""
        hours_list = []
        grand_total = 0

        for code in codes[1:]:  # Bỏ qua None đầu tiên
            total = sum(
                getattr(mission, 'total_hours', 0) or 0
                for course in courses
                if hasattr(course, 'mission_ids') and course.mission_ids
                for mission in course.mission_ids
                if (hasattr(mission, 'subject_id') and mission.subject_id and
                    hasattr(mission.subject_id, 'code') and mission.subject_id.code == code)
            )
            hours_list.append(str(int(total)) if total else '')
            grand_total += total

        hours_list.insert(0, str(int(grand_total)) if grand_total else '')
        return hours_list

    # ==================== Table Replacement Functions ====================

    def replace_placeholder_with_table(self, doc, placeholder, records, rows_data, note=None):
        """Replace placeholder with standard table format."""
        for para in doc.paragraphs:
            if placeholder not in para.text:
                continue

            parent = para._element.getparent()
            idx = parent.index(para._element)
            parent.remove(para._element)

            num_records = len(records)
            num_cols = 2 + num_records + (1 if note else 0)
            num_rows = 2 + len(rows_data)

            table = doc.add_table(rows=num_rows, cols=num_cols)
            table.style = 'Table Grid'

            # Set column widths
            tt_width, nd_width, total_time_width = 1.2, 15, 25
            record_width = total_time_width / num_records if num_records else total_time_width
            widths = [tt_width, nd_width] + [record_width] * num_records
            if note:
                widths.append(5)

            for row in table.rows:
                for cell, w in zip(row.cells, widths):
                    self.set_column_width(cell, w)

            # Create headers
            self._build_standard_headers(table, records, num_records, num_cols, note)

            # Fill data rows
            self._fill_data_rows(table, records, rows_data, note, num_cols)

            parent.insert(idx, table._element)
            break

    def _build_standard_headers(self, table, records, num_records, num_cols, note):
        """Build headers for standard table."""
        # Column 1: TT
        table.cell(0, 0).merge(table.cell(1, 0))
        self.cell_set(table.cell(0, 0), "TT", bold=True)

        # Column 2: Nội dung
        table.cell(0, 1).merge(table.cell(1, 1))
        self.cell_set(table.cell(0, 1), "Nội dung", bold=True)

        # Time columns
        if num_records > 0:
            table.cell(0, 2).merge(table.cell(0, 1 + num_records))
            self.cell_set(table.cell(0, 2), "Thời gian", bold=True)
            for i, rec in enumerate(records):
                self.cell_set(table.cell(1, 2 + i), rec.name, bold=True)

        # Note column
        if note:
            table.cell(0, num_cols - 1).merge(table.cell(1, num_cols - 1))
            self.cell_set(table.cell(0, num_cols - 1), "Ghi chú", bold=True)

    def _fill_data_rows(self, table, records, rows_data, note, num_cols):
        """Fill data rows for standard table."""
        for r_idx, (tt, label, field) in enumerate(rows_data, start=2):
            self.cell_set(table.cell(r_idx, 0), tt)
            self.cell_set(table.cell(r_idx, 1), label, align='left')

            for c_idx, rec in enumerate(records):
                value = getattr(rec, field, '') or ''
                self.cell_set(table.cell(r_idx, 2 + c_idx), value)

            if note:
                self.cell_set(table.cell(r_idx, num_cols - 1), note)

    def replace_table_3_aasam(self, doc, placeholder, records):
        """Replace placeholder with AASAM-2025 competition table."""
        for para in doc.paragraphs:
            if placeholder not in para.text:
                continue

            parent = para._element.getparent()
            parent_idx = parent.index(para._element)
            parent.remove(para._element)

            # Calculate total rows
            total_courses = sum(len(r.course_ids) if r.course_ids else 0 for r in records)
            num_rows = 2 + (len(records) * 2) + total_courses

            table = doc.add_table(rows=num_rows, cols=15)
            table.style = 'Table Grid'

            # Build headers
            self._build_aasam_headers(table)

            # Fill data
            self._fill_aasam_data(table, records)

            parent.insert(parent_idx, table._element)
            break

    def _build_aasam_headers(self, table):
        """Build headers for AASAM table."""
        # Main headers (row 0)
        headers_config = [
            (0, 0, 1, 0, "TT", 0.5),
            (0, 1, 1, 1, "Đối tượng", 7),
            (0, 2, 1, 2, "Tổng số\n(giờ)", 1.5),
            (0, 3, 0, 9, "Huấn luyện chung", None),
            (0, 10, 0, 13, "Huấn luyện riêng", None),
            (0, 14, 1, 14, "Ghi chú", 3.5)
        ]

        for r1, c1, r2, c2, text, width in headers_config:
            table.cell(r1, c1).merge(table.cell(r2, c2))
            self.cell_set(table.cell(r1, c1), text, bold=True)
            if width:
                self.set_column_width(table.cell(r1, c1), width)

        # Sub-headers (row 1)
        sub_headers = [
            (3, "+\n(%)"), (4, "Chính trị"), (5, "G đục\np.luật"),
            (6, "Hậu cần"), (7, "Kỹ thuật"), (8, "Điều lệnh"),
            (9, "Kỹ thuật\nCĐBĐ"), (10, "+\n(%)"), (11, "Bắn súng"),
            (12, "Thể lực"), (13, "Tiếng\nAnh")
        ]

        for col, text in sub_headers:
            self.cell_set(table.cell(1, col), text, bold=True)
            self.set_column_width(table.cell(1, col), 1.2)

    def _fill_aasam_data(self, table, records):
        """Fill data for AASAM table."""
        current_row = 2
        course_labels = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h']

        for record_idx, record in enumerate(records):
            courses = record.course_ids if record.course_ids else []
            num_courses = len(courses)

            row_total_hours = current_row
            row_percent = current_row + 1

            # Merge cells
            self._merge_aasam_cells(table, row_total_hours, row_percent, num_courses)

            # Fill summary rows
            self._fill_aasam_summary(table, record, record_idx, courses, row_total_hours, row_percent)

            # Fill course details
            current_row = self._fill_aasam_courses(
                table, courses, course_labels, row_percent + 1
            )

        return current_row

    def _merge_aasam_cells(self, table, row_total_hours, row_percent, num_courses):
        """Merge cells for AASAM table."""
        # Merge for summary rows
        merge_configs = [(0, 0), (1, 1), (2, 2), (14, 14)]
        for col, _ in merge_configs:
            table.cell(row_total_hours, col).merge(table.cell(row_percent, col))

        # Merge for percentage row
        table.cell(row_percent, 4).merge(table.cell(row_percent, 5))
        table.cell(row_percent, 6).merge(table.cell(row_percent, 9))

        # Merge note column for courses
        if num_courses > 0:
            table.cell(row_percent + 1, 14).merge(
                table.cell(row_percent + num_courses, 14)
            )

    def _fill_aasam_summary(self, table, record, record_idx, courses, row_total_hours, row_percent):
        """Fill summary rows for AASAM table."""
        # Hours row
        total_hours = getattr(record, 'total_hours', 0)
        self.cell_set(table.cell(row_total_hours, 2), f'{total_hours}\n100%', bold=True)

        # Calculate hours
        hl_chung_codes = [None, 'CT', 'GDPL', 'HC', 'KT', 'DL', 'KTCDBD']
        hl_chung_hours = self.calculate_hours_by_codes(courses, hl_chung_codes)

        hl_rieng_codes = [None, 'BS', 'TL']
        hl_rieng_hours = self.calculate_hours_by_codes(courses, hl_rieng_codes)

        for i, val in enumerate(hl_chung_hours):
            self.cell_set(table.cell(row_total_hours, 3 + i), val, bold=True)

        for i, val in enumerate(hl_rieng_hours):
            self.cell_set(table.cell(row_total_hours, 10 + i), val, bold=True)

        # Percentage row
        tt_number = f"{record_idx + 1}.1"
        self.cell_set(table.cell(row_percent, 0), tt_number, bold=True)
        self.cell_set(table.cell(row_percent, 1), record.name, align='left', bold=True)

        # Helper function để convert sang số
        def to_number(value):
            """Convert value to number, handling strings and lists."""
            if isinstance(value, (int, float)):
                return value
            if isinstance(value, str):
                try:
                    return float(value.replace(',', '.').strip())
                except (ValueError, AttributeError):
                    return 0
            if isinstance(value, list):
                return sum(to_number(v) for v in value)
            return 0

        # Tính tổng giờ học chung và học riêng (sử dụng trực tiếp từ list đã tính)
        total_hl_chung = sum(to_number(val) for val in hl_chung_hours[1:])  # Bỏ qua phần tử đầu (None)
        total_hl_rieng = sum(to_number(val) for val in hl_rieng_hours[1:])  # Bỏ qua phần tử đầu (None)

        # Lấy giá trị từ list đã tính sẵn thay vì tính lại
        # hl_chung_hours = [None, CT, GDPL, HC, KT, DL, KTCDBD]
        # Index: 0=None, 1=CT, 2=GDPL, 3=HC, 4=KT, 5=DL, 6=KTCDBD
        total_ct_gdpl = to_number(hl_chung_hours[1]) + to_number(hl_chung_hours[2])
        total_hc = to_number(hl_chung_hours[3])

        # hl_rieng_hours = [None, BS, TL, TA]
        # Index: 0=None, 1=BS, 2=TL, 3=TA
        total_bs = to_number(hl_rieng_hours[1])
        total_tl = to_number(hl_rieng_hours[2])

        # Tính phần trăm (tránh chia cho 0)
        total_hours_num = to_number(total_hours)
        if total_hours_num > 0:
            pct_col3 = f"{(total_hl_chung / total_hours_num * 100):.1f}%"  # Tổng HL chung / total_hours
            pct_col4 = f"{(total_ct_gdpl / total_hours_num * 100):.1f}%"  # CT + GDPL / total_hours
            pct_col6 = f"{(total_hc / total_hours_num * 100):.1f}%"  # HC / total_hours
            pct_col10 = f"{(total_hl_rieng / total_hours_num * 100):.1f}%"  # Tổng HL riêng / total_hours
            pct_col11 = f"{(total_bs / total_hours_num * 100):.1f}%"  # BS / total_hours
            pct_col12 = f"{(total_tl / total_hours_num * 100):.1f}%"  # TL / total_hours
        else:
            pct_col3 = pct_col4 = pct_col6 = pct_col10 = pct_col11 = pct_col12 = "0%"

        percentages = [
            (3, pct_col3),  # Tổng HL chung / total_hours
            (4, pct_col4),  # CT + GDPL / total_hours
            (6, pct_col6),  # HC / total_hours
            (10, pct_col10),  # Tổng HL riêng / total_hours
            (11, pct_col11),  # BS / total_hours
            (12, pct_col12)  # TL / total_hours
        ]
        for col, pct in percentages:
            self.cell_set(table.cell(row_percent, col), pct, bold=True)

    def _fill_aasam_courses(self, table, courses, course_labels, start_row):
        """Fill course details for AASAM table."""
        current_row = start_row

        for course_idx, course in enumerate(courses):
            label = course_labels[course_idx] if course_idx < len(course_labels) else str(course_idx + 1)
            self.cell_set(table.cell(current_row, 0), label)

            # Course name with dates
            course_name = f"Giai đoạn {course_idx + 1}: {course.name or ''}"
            if hasattr(course, 'start_date') and hasattr(course, 'end_date'):
                start_date = course.start_date.strftime('%d/%m') if course.start_date else ''
                end_date = course.end_date.strftime('%d/%m/%Y') if course.end_date else ''
                if start_date or end_date:
                    course_name += f" (từ ngày {start_date} ÷ {end_date})"

            self.cell_set(table.cell(current_row, 1), course_name, align='left')

            # Total hours
            total_hours = getattr(course, 'total_hours', '')
            self.cell_set(table.cell(current_row, 2), str(total_hours))

            # Calculate hours for this specific course
            hl_chung_codes = [None, 'CT', 'GDPL', 'HC', 'KT', 'DL', 'KTCDBD']
            hl_chung_hours = self.calculate_hours_by_codes([course], hl_chung_codes)

            hl_rieng_codes = [None, 'BS', 'TL', 'TA']
            hl_rieng_hours = self.calculate_hours_by_codes([course], hl_rieng_codes)

            # Fill training hours for Huấn luyện chung
            for i, val in enumerate(hl_chung_hours):
                self.cell_set(table.cell(current_row, 3 + i), val)

            # Fill training hours for Huấn luyện riêng
            for i, val in enumerate(hl_rieng_hours):
                self.cell_set(table.cell(current_row, 10 + i), val)

            # Note (only for first course)
            if course_idx == 0:
                note = getattr(course, 'note', '') or \
                       'Huấn luyện nội dung Tiếng Anh không tính vào thời gian huấn luyện chính khóa'
                self.cell_set(table.cell(current_row, 14), note, align='left')

            current_row += 1

        return current_row

    # ==================== Main Action ====================

    def action_print_word(self):
        """Export training plan to Word document with multiple tables."""
        active_ids = self.env.context.get("active_ids", [])
        records = self.env['training.plan'].browse(active_ids)

        # Data definitions
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

        # Load template and replace tables
        template_path = get_module_resource(
            'army_results_manager', 'static', 'src', 'word', f'{self.mau_in}.docx'
        )
        doc = Document(template_path)

        self.replace_placeholder_with_table(doc, "{{table_1}}", records, rows_data_table_1)
        self.replace_placeholder_with_table(doc, "{{table_2}}", records, rows_data_table_2, note=" ")
        self.replace_table_3_aasam(doc, "{{table_3}}", records)

        # Export Word file
        file_data = BytesIO()
        doc.save(file_data)
        file_data.seek(0)
        data = base64.b64encode(file_data.read())

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