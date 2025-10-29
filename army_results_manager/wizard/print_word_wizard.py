# -*- coding: utf-8 -*-
from odoo import models, fields
from odoo.modules.module import get_module_resource
from io import BytesIO
import base64
import string
from docx.shared import Pt
from docx import Document
from docx.shared import Cm
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_ALIGN_VERTICAL
from docx.shared import Inches
from datetime import date
from odoo.exceptions import UserError
from collections import defaultdict


class PrintWordWizard(models.TransientModel):
    _name = "print.word.wizard"
    _description = "Wizard chọn mẫu in Word/Excel"

    mau_in = fields.Selection(
        [('template1', 'Phụ lục 1'),
         ('template2', 'Phụ lục 2'),
         ('template3', 'Phụ lục 3'),
         ('template4', 'Phụ lục 4'),
         ('template5', 'Phụ lục 5')],
        string="Chọn mẫu phụ lục"
    )
    report_type = fields.Selection([
        ('week', 'Theo tuần'),
        ('month', 'Theo tháng'),
        ('year', 'Theo năm'),
    ], string="Loại báo cáo", required=True, default='week')

    year = fields.Char(string="Năm", default=lambda self: date.today().year)
    month = fields.Selection([
        ('1', 'Tháng 1'), ('2', 'Tháng 2'), ('3', 'Tháng 3'),
        ('4', 'Tháng 4'), ('5', 'Tháng 5'), ('6', 'Tháng 6'),
        ('7', 'Tháng 7'), ('8', 'Tháng 8'), ('9', 'Tháng 9'),
        ('10', 'Tháng 10'), ('11', 'Tháng 11'), ('12', 'Tháng 12'),
    ], string="Tháng")

    week = fields.Selection([
        ('1', 'Tuần 1'), ('2', 'Tuần 2'),
        ('3', 'Tuần 3'), ('4', 'Tuần 4'), ('5', 'Tuần 5'),
    ], string="Tuần")

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

    def replace_placeholder_with_table(self, doc, placeholder, records, rows_data=None, note=None):
        """Replace placeholder with standard table format, chỉ lấy records có type='squad'."""
        # 🔸 Lọc record theo type
        filtered_records = [r for r in records if r.type == 'squad']

        # Nếu không có record phù hợp thì không tạo bảng
        if not filtered_records:
            return

        for para in doc.paragraphs:
            if placeholder not in para.text:
                continue

            parent = para._element.getparent()
            idx = parent.index(para._element)
            parent.remove(para._element)

            num_records = len(filtered_records)
            num_cols = 2 + num_records + (1 if note else 0)
            num_rows = 2 + len(rows_data)

            table = doc.add_table(rows=num_rows, cols=num_cols)
            table.style = 'Table Grid'

            # 🔸 Thiết lập độ rộng cột
            tt_width, nd_width, total_time_width = 1.2, 15, 25
            record_width = total_time_width / num_records if num_records else total_time_width
            widths = [tt_width, nd_width] + [record_width] * num_records
            if note:
                widths.append(5)

            for row in table.rows:
                for cell, w in zip(row.cells, widths):
                    self.set_column_width(cell, w)

            # 🔸 Tạo phần header
            self._build_standard_headers(table, filtered_records, num_records, num_cols, note)

            # 🔸 Điền dữ liệu vào bảng
            self._fill_data_rows(table, filtered_records, rows_data, note, num_cols)

            # 🔸 Chèn bảng vào đúng vị trí placeholder
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
        """Replace placeholder with AASAM-2025 competition table (only records with type='squad')."""
        # 🔸 Lọc chỉ những record có training_plan_id.type == 'squad'
        filtered_records = [r for r in records if r.type == 'squad']

        # Nếu không có record phù hợp thì không tạo bảng
        if not filtered_records:
            return

        for para in doc.paragraphs:
            if placeholder not in para.text:
                continue

            parent = para._element.getparent()
            parent_idx = parent.index(para._element)
            parent.remove(para._element)

            # 🔸 Tính tổng số dòng dựa trên filtered_records
            total_courses = sum(len(r.course_ids) if r.course_ids else 0 for r in filtered_records)
            num_rows = 2 + (len(filtered_records) * 2) + total_courses

            table = doc.add_table(rows=num_rows, cols=15)
            table.style = 'Table Grid'

            # Xây header
            self._build_aasam_headers(table)

            # Điền dữ liệu cho các record đã lọc
            self._fill_aasam_data(table, filtered_records)

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

    # ==================== Table 4: Huấn luyện sĩ quan ====================

    def replace_table_4(self, doc, placeholder, records):
        """Main function to replace placeholder with table 4, chỉ lấy records officer."""
        filtered_records = [r for r in records if r.type == 'officer']
        if not filtered_records:
            return

        for para in doc.paragraphs:
            if placeholder not in para.text:
                continue

            parent = para._element.getparent()
            idx = parent.index(para._element)
            parent.remove(para._element)

            table = self._create_table_4_structure(doc)
            self._fill_table_4_data(table, filtered_records)
            self._update_table_4_header_totals(table)

            parent.insert(idx, table._element)
            break

    def _create_table_4_structure(self, doc):
        """Tạo bảng với cấu trúc header tối ưu."""
        table = doc.add_table(rows=3, cols=18)
        table.style = "Table Grid"

        # Set column widths trước khi build header
        self._set_table_4_column_widths(table)

        # Build headers
        self._build_table_4_headers(table)

        # Format headers và set row height
        self._format_table_4_headers(table)

        return table

    def _build_table_4_headers(self, table):
        """Tạo 3 hàng tiêu đề cho Bảng 4 với cấu trúc tối ưu."""

        # ───── 1. HEADER CHÍNH (ROW 0) ─────
        row0 = table.rows[0]
        headers_row0 = [
            "TT", "Nội dung huấn luyện", "Thành phần tham gia",
            "Cấp phụ trách", "Thời gian (giờ)", "", "", "", "", "",
            "", "", "", "", "", "", "", "Biện pháp tiến hành"
        ]

        for i, text in enumerate(headers_row0):
            if text:  # Only set non-empty cells
                row0.cells[i].text = text

        # Merge "Thời gian (giờ)" từ cột 4 → 16
        row0.cells[4].merge(row0.cells[16])

        # ───── 2. SUBHEADER (ROW 1) ─────
        row1 = table.rows[1]
        row1.cells[4].text = "Tổng số"
        for month_idx in range(12):
            row1.cells[5 + month_idx].text = f"Tháng {month_idx + 1:02d}"

        # ───── 3. MERGE CỘT CỐ ĐỊNH THEO CHIỀU DỌC ─────
        # Merge các cột: TT, Nội dung, Thành phần, Cấp phụ trách, Biện pháp
        fixed_cols = [0, 1, 2, 3, 17]
        for col_idx in fixed_cols:
            table.cell(0, col_idx).merge(table.cell(2, col_idx))

    def _set_table_4_column_widths(self, table):
        """Đặt chiều rộng cố định cho từng cột."""
        col_widths = [
            0.4,  # TT
            4.5,  # Nội dung huấn luyện
            1.0,  # Thành phần
            0.9,  # Cấp phụ trách
            0.5,  # Tổng số
            0.45, 0.45, 0.45, 0.45, 0.45, 0.45,  # Tháng 1-6
            0.45, 0.45, 0.45, 0.45, 0.45, 0.45,  # Tháng 7-12
            2.5  # Biện pháp
        ]

        for row in table.rows:
            for col_idx, width_in in enumerate(col_widths):
                row.cells[col_idx].width = Inches(width_in)

    def _format_table_4_headers(self, table):
        """Định dạng header với chiều cao cố định."""
        # Set height cho từng row riêng biệt
        height_values = [0.3, 0.45, 0.3]  # Row 0, Row 1 (tháng), Row 2

        for row_idx in range(3):
            row = table.rows[row_idx]
            # Set row height
            tr = row._tr
            trPr = tr.get_or_add_trPr()
            trHeight = OxmlElement('w:trHeight')
            trHeight.set(qn('w:val'), str(int(height_values[row_idx] * 1440)))  # 1440 twips per inch
            trHeight.set(qn('w:hRule'), 'exact')
            trPr.append(trHeight)

            # Format cells
            for cell in row.cells:
                self._format_cell(
                    cell,
                    bold=True,
                    font_size=14,
                    align_center=True,
                    vertical_center=True
                )

    def _fill_table_4_data(self, table, records):
        """Điền dữ liệu vào bảng."""
        seq = 1
        for record in records:
            courses = getattr(record, 'course_ids', [])
            if not courses:
                continue

            for course in courses:
                mission_lines = getattr(course, 'mission_ids', [])
                if not mission_lines:
                    continue

                # Add parent row và sub rows
                parent_idx = self._add_parent_row(table, course, seq)
                seq += 1

                sub_start = len(table.rows)
                self._add_sub_rows(table, course, mission_lines)
                sub_end = len(table.rows) - 1

                # Update totals cho parent row
                if sub_end >= sub_start:
                    self._update_parent_row_totals(table, sub_start, sub_end, parent_idx, course)

    def _add_parent_row(self, table, course, seq):
        """Thêm dòng cha (course name)."""
        row = table.add_row()
        cells = row.cells

        # STT
        cells[0].text = str(seq)

        # Merge cột 1-3 cho tên khóa học
        cells[1].merge(cells[2]).merge(cells[3])
        cells[1].text = getattr(course, 'name', '')
        cells[1].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.LEFT

        # Clear các cột khác
        for i in range(4, 18):
            cells[i].text = ''

        # Format row
        self._format_data_row(row)

        return len(table.rows) - 1

    def _add_sub_rows(self, table, course, mission_lines):
        """Thêm các dòng con (mission details)."""
        all_sub_lines = []

        # Collect all sub_lines
        for mission_line in mission_lines:
            sub_lines = getattr(mission_line, 'mission_line_ids', [])
            all_sub_lines.extend(sub_lines)

        if not all_sub_lines:
            return

        start_row = len(table.rows)

        # Add sub rows
        for sub_line in all_sub_lines:
            row = table.add_row()
            cells = row.cells

            cells[0].text = ''
            cells[1].text = sub_line.name or ''
            cells[1].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.LEFT
            cells[2].text = ''
            cells[3].text = ''

            # Tổng giờ
            total_hours = getattr(sub_line, 'total_hours', 0) or 0
            cells[4].text = str(int(total_hours)) if total_hours else ''

            # Giờ theo tháng
            month_hours = self._get_month_hours(sub_line)
            for m_idx in range(1, 13):
                val = month_hours.get(m_idx, 0)
                cells[4 + m_idx].text = str(int(val)) if val else ''

            cells[17].text = ''

            # Format row
            self._format_data_row(row)

        end_row = len(table.rows) - 1

        # Merge cột 2 và 3 cho sub rows
        if end_row >= start_row:
            participant = getattr(getattr(course, 'participant_category_id', None), 'name', '')
            responsible = getattr(getattr(course, 'responsible_level_id', None), 'name', '')

            self._merge_and_fill(table, start_row, end_row, 2, participant)
            self._merge_and_fill(table, start_row, end_row, 3, responsible)

    def _update_parent_row_totals(self, table, sub_start, sub_end, parent_idx, course):
        """Cập nhật tổng cho dòng cha."""
        if parent_idx is None or sub_end < sub_start:
            return

        parent_cells = table.rows[parent_idx].cells

        # Tính tổng cho các cột 4-16 (tổng số + 12 tháng)
        for col_idx in range(4, 17):
            total = sum(
                self._get_cell_numeric_value(table.rows[r].cells[col_idx])
                for r in range(sub_start, sub_end + 1)
            )
            parent_cells[col_idx].text = str(int(total)) if total else ''

        # Merge cột 17 (Biện pháp) với các dòng con
        cell17 = parent_cells[17]
        for r in range(sub_start, sub_end + 1):
            cell17 = cell17.merge(table.rows[r].cells[17])
        cell17.text = getattr(course, 'measure', '') or ''
        cell17.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.LEFT

        # Bôi đậm dòng cha
        for i in range(0, 17):
            self._bold_cell(parent_cells[i])

    def _update_table_4_header_totals(self, table):
        """Cập nhật tổng cho hàng header (row 2)."""
        header_row = table.rows[2]
        month_totals = {i: 0 for i in range(1, 13)}
        total_all = 0

        # Tính tổng từ các dòng cha (có STT)
        for r_idx in range(3, len(table.rows)):
            cells = table.rows[r_idx].cells
            if cells[0].text.strip().isdigit():  # Chỉ tính dòng cha
                total_all += self._get_cell_numeric_value(cells[4])
                for m_idx in range(1, 13):
                    month_totals[m_idx] += self._get_cell_numeric_value(cells[4 + m_idx])

        # Ghi tổng vào header
        header_row.cells[4].text = str(int(total_all)) if total_all else ''
        for m_idx in range(1, 13):
            val = month_totals[m_idx]
            header_row.cells[4 + m_idx].text = str(int(val)) if val else ''

        # Bold header totals
        for cell in header_row.cells:
            self._bold_cell(cell)

    def _merge_and_fill(self, table, start_row, end_row, col_idx, text):
        """Merge cells và điền text."""
        if end_row < start_row:
            return

        start_cell = table.rows[start_row].cells[col_idx]
        for r in range(start_row + 1, end_row + 1):
            start_cell = start_cell.merge(table.rows[r].cells[col_idx])

        start_cell.text = str(text) if text not in (None, True, False) else ''
        start_cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER

    def _get_cell_numeric_value(self, cell):
        """Lấy giá trị số từ cell."""
        try:
            text = cell.text.strip()
            return float(text) if text else 0
        except (ValueError, AttributeError):
            return 0

    def _format_data_row(self, row):
        """Format một dòng dữ liệu."""
        for cell in row.cells:
            self._format_cell(cell, font_size=14, vertical_center=True)

    def _format_cell(self, cell, bold=False, font_size=14, align_center=False, vertical_center=False):
        """Format một cell với các tùy chọn."""
        if vertical_center:
            cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER

        for para in cell.paragraphs:
            if align_center:
                para.alignment = WD_ALIGN_PARAGRAPH.CENTER

            # Ensure at least one run exists
            if not para.runs:
                para.add_run()

            for run in para.runs:
                run.font.name = "Times New Roman"
                run.font.size = Pt(font_size)
                run.bold = bold

    def _bold_cell(self, cell):
        """Bôi đậm tất cả text trong cell."""
        for para in cell.paragraphs:
            if not para.runs:
                para.add_run()
            for run in para.runs:
                run.font.bold = True

    # ==template3==
    def _iter_all_paragraphs(self, doc):
        """Duyệt tất cả các paragraph trong doc, kể cả trong bảng."""
        for p in doc.paragraphs:
            yield p
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    for p in cell.paragraphs:
                        yield p

    def replace_table_3_1(self, doc, placeholder, records):
        """Thay thế placeholder {{table_3_1}} bằng bảng kế hoạch huấn luyện tuần."""
        filtered_records = [r for r in records if r.type == 'squad']
        if not filtered_records:
            return

        for para in self._iter_all_paragraphs(doc):
            if placeholder not in para.text:
                continue

            parent = para._element.getparent()
            idx = parent.index(para._element)
            parent.remove(para._element)

            table = self._create_table_3_1_structure(doc)
            # self._fill_table_3_1_data(table, records)

            parent.insert(idx, table._element)
            break

    def _create_table_3_1_structure(self, doc):
        """Tạo bảng 3.1 với 7 cột như trong ảnh."""
        table = doc.add_table(rows=1, cols=7)
        table.style = "Table Grid"

        # Set column widths
        self._set_table_3_1_column_widths(table)

        # Build header
        self._build_table_3_1_headers(table)

        # Format header
        self._format_table_3_1_headers(table)

        # Add 7 rows for days of the week
        self._add_table_3_1_week_rows(table)

        return table

    def _set_table_3_1_column_widths(self, table):
        """Chiều rộng cột bảng 3.1."""
        col_widths = [
            0.8,  # Thứ, Ngày tháng
            5.3,  # Nội dung
            1.1,  # Tổng thời gian (giờ)
            3.2,  # Thời gian huấn luyện
            1.0,  # Cấp phụ trách
            1.0,  # Địa điểm
            2.8  # Vật chất bảo đảm chính
        ]

        for row in table.rows:
            for col_idx, width_in in enumerate(col_widths):
                row.cells[col_idx].width = Inches(width_in)

    def _build_table_3_1_headers(self, table):
        """Xây dựng dòng header bảng 3.1."""
        headers = [
            "Thứ, Ngày tháng",
            "Nội dung",
            "Tổng thời gian (giờ)",
            "Thời gian huấn luyện\n(Sáng: 07.30 - 11.30)\n(Chiều: 13.30 - 16.30)",
            "Cấp phụ trách",
            "Địa điểm",
            "Vật chất\nbảo đảm chính"
        ]

        row = table.rows[0]
        for i, text in enumerate(headers):
            row.cells[i].text = text

    def _format_table_3_1_headers(self, table):
        """Định dạng header: Times New Roman, cỡ 14, đậm, căn giữa."""
        header_row = table.rows[0]
        tr = header_row._tr
        trPr = tr.get_or_add_trPr()
        trHeight = OxmlElement('w:trHeight')
        trHeight.set(qn('w:val'), str(int(0.9 * 1440)))  # Chiều cao 0.6 inch
        trHeight.set(qn('w:hRule'), 'exact')
        trPr.append(trHeight)

        for cell in header_row.cells:
            self._format_cell(
                cell,
                bold=True,
                font_size=13,
                align_center=True,
                vertical_center=True
            )

    def _add_table_3_1_week_rows(self, table):
        """Thêm 7 dòng vào bảng 3.1, với cột đầu tiên là thứ trong tuần."""
        days = ["Hai,\n", "Ba,\n", "Tư,\n", "Năm,\n", "Sáu,\n", "Bảy,\n", "CN,\n"]

        for day in days:
            row = table.add_row()

            # Cột đầu tiên: căn giữa ngang & dọc
            first_cell = row.cells[0]
            first_cell.text = day
            for p in first_cell.paragraphs:
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            first_cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER

            # Các cột còn lại: để nguyên (không căn giữa)
            for i in range(1, len(row.cells)):
                row.cells[i].text = ""

    def _fill_table_3_1_data(self, table, records):
        """
        Điền dữ liệu vào bảng 3.1.
        records là danh sách dict hoặc object có thuộc tính:
        - weekday (str): 'Hai', 'Ba', ...
        - date (str): '17', '18/10'...
        - content (str): Nội dung huấn luyện
        - total_hours (int)
        - time_range (str): '07.30 - 09.30'
        - level (str): Cấp phụ trách
        - location (str): Địa điểm
        - materials (str): Vật chất bảo đảm chính
        """
        for rec in records:
            row = table.add_row()
            cells = row.cells

            cells[0].text = f"{rec.weekday}\n{rec.date}"
            cells[1].text = rec.content or ''
            cells[2].text = str(rec.total_hours or '')
            cells[3].text = rec.time_range or ''
            cells[4].text = rec.level or ''
            cells[5].text = rec.location or ''
            cells[6].text = rec.materials or ''

            self._format_data_row(row)

    def _format_data_row(self, row):
        """Định dạng dòng dữ liệu bảng 3.1."""
        for i, cell in enumerate(row.cells):
            self._format_cell(
                cell,
                font_size=13,
                align_center=(i not in [1, 6]),  # cột Nội dung & Vật chất căn trái
                vertical_center=True
            )
            if i in [1, 6]:
                for para in cell.paragraphs:
                    para.alignment = WD_ALIGN_PARAGRAPH.LEFT

    def replace_placeholder_with_text(self, doc, placeholder, replacement_text):
        """Thay thế placeholder trong cả paragraphs và tables, xử lý trường hợp placeholder bị split"""
        found = False

        def replace_in_paragraph(paragraph):
            """Helper function để thay thế trong một paragraph"""
            nonlocal found

            # Ghép tất cả runs lại để tìm placeholder
            full_text = ''.join(run.text for run in paragraph.runs)

            # Kiểm tra có chứa placeholder không
            if placeholder in full_text:
                found = True

                # Thay thế placeholder
                new_text = full_text.replace(placeholder, str(replacement_text))

                if paragraph.runs:
                    # Lưu format của run đầu tiên (hoặc run có format chính)
                    first_run = paragraph.runs[0]

                    saved_format = {
                        'name': first_run.font.name,
                        'size': first_run.font.size,
                        'bold': first_run.font.bold,
                        'italic': first_run.font.italic,
                        'underline': first_run.font.underline,
                    }

                    # Lưu màu chữ (có thể None)
                    try:
                        if first_run.font.color and first_run.font.color.rgb:
                            saved_format['color'] = first_run.font.color.rgb
                        else:
                            saved_format['color'] = None
                    except:
                        saved_format['color'] = None

                    # Xóa tất cả runs hiện tại
                    while len(paragraph.runs) > 0:
                        paragraph._element.remove(paragraph.runs[0]._element)

                    # Tạo run mới với text đã thay thế
                    new_run = paragraph.add_run(new_text)

                    # Khôi phục format
                    if saved_format['name']:
                        new_run.font.name = saved_format['name']
                    if saved_format['size']:
                        new_run.font.size = saved_format['size']
                    new_run.font.bold = saved_format['bold']
                    new_run.font.italic = saved_format['italic']
                    new_run.font.underline = saved_format['underline']
                    if saved_format['color']:
                        new_run.font.color.rgb = saved_format['color']

        # Thay thế trong tất cả paragraphs
        for paragraph in doc.paragraphs:
            replace_in_paragraph(paragraph)

        # Thay thế trong tất cả tables
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    for paragraph in cell.paragraphs:
                        replace_in_paragraph(paragraph)

        return found

    def print_table(self, doc, table_index):
        """
        In ra thông tin của table

        Args:
            doc: Document object
            table_index: Vị trí table (0-based, table_index=1 là table thứ 2)
        """
        if table_index >= len(doc.tables):
            print(f"Table index {table_index} không tồn tại!")
            print(f"Document chỉ có {len(doc.tables)} tables")
            return False

        table = doc.tables[table_index]

        print("=" * 80)
        print(f"TABLE INDEX: {table_index}")
        print(f"Số dòng: {len(table.rows)}")
        print(f"Số cột: {len(table.columns)}")
        print("=" * 80)

        # In ra từng dòng và cell
        for row_idx, row in enumerate(table.rows):
            print(f"\n--- Dòng {row_idx} ---")
            for col_idx, cell in enumerate(row.cells):
                cell_text = cell.text.strip()
                print(f"  Cell[{row_idx}][{col_idx}]: {cell_text}")

        print("=" * 80)
        return True

    # ==================== Main Action ====================

    def action_print_word(self):
        if self.report_type == 'week':
            self.mau_in = 'template3'
        elif self.report_type == 'month':
            self.mau_in = 'template2'
        elif self.report_type == 'year':
            self.mau_in = 'template1'

        template_path = get_module_resource(
            'army_results_manager', 'static', 'src', 'word', f'{self.mau_in}.docx'
        )
        doc = Document(template_path)

        if self.report_type == 'week':
            self.replace_placeholder_with_text(doc, "{{week}}", self.week)
            self.replace_placeholder_with_text(doc, "{{month}}", self.month)

            # Lấy dữ liệu training days
            TrainingDay = self.env['training.day']
            domain = [
                ('year', '=', self.year),
                ('month_name', '=', f'Tháng {self.month}'),
                ('week_name', '=', f'Tuần {self.week}'),
            ]

            records = TrainingDay.search(domain, order='day asc')

            if not records:
                raise UserError('Không tìm thấy dữ liệu!')

            table_index = 1
            if table_index >= len(doc.tables):
                raise UserError('Không tìm thấy table!')

            table = doc.tables[table_index]

            # Mapping weekday
            weekday_map = {
                '2': 'Hai',
                '3': 'Ba',
                '4': 'Tư',
                '5': 'Năm',
                '6': 'Sáu',
                '7': 'Bảy',
                'cn': 'Chủ nhật'
            }

            grouped_records = {}

            for record in records:
                weekday_text = weekday_map.get(record.weekday, record.weekday)
                day_str = record.day.strftime("%d/%m/%Y")
                key = (weekday_text, day_str)

                # Khởi tạo cấu trúc cho key nếu chưa tồn tại
                if key not in grouped_records:
                    grouped_records[key] = {'missions': defaultdict(lambda: {'lessons': [], 'hours': [], 'times': []})}

                # Lưu lesson, hours và times theo từng mission
                mission_data = grouped_records[key]['missions'][record.mission_name]

                if record.lesson_name and record.lesson_name not in mission_data['lessons']:
                    mission_data['lessons'].append(record.lesson_name)

                # Lưu hours cho từng record
                if record.total_hours and record.total_hours not in mission_data['hours']:
                    mission_data['hours'].append(record.total_hours)

                # Lưu thời gian
                for time_rec in record.time_ids:
                    if time_rec.start_time and time_rec.end_time:
                        # Chuyển đổi trực tiếp
                        start_h = int(time_rec.start_time)
                        start_m = int((time_rec.start_time - start_h) * 60)
                        end_h = int(time_rec.end_time)
                        end_m = int((time_rec.end_time - end_h) * 60)

                        time_str = f"{start_h:02d}:{start_m:02d} - {end_h:02d}:{end_m:02d}"
                        if time_str not in mission_data['times']:
                            mission_data['times'].append(time_str)

            # Điền vào bảng - TỰ ĐỘNG THÊM HÀNG
            for (weekday, day_str), data in grouped_records.items():
                # Thêm 3 hàng mới cho mỗi ngày
                new_row1 = table.add_row()
                new_row2 = table.add_row()
                new_row3 = table.add_row()

                # Merge cells nếu cần (tùy chọn)
                # new_row1.cells[0].merge(new_row2.cells[0])  # Merge weekday cell

                # Điền weekday vào hàng đầu tiên
                new_row1.cells[0].text = weekday
                new_row1.cells[0].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER

                # Điền ngày tháng năm vào hàng thứ hai
                new_row2.cells[0].text = day_str
                new_row2.cells[0].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER

                # Điền missions và lessons vào cell[1]
                cell = new_row1.cells[1]
                cell.text = ""

                # Điền hours vào cell[2]
                cell_hours = new_row1.cells[2]
                cell_hours.text = ""

                # Điền time vào cell[3]
                cell_time = new_row1.cells[3]
                cell_time.text = ""

                first_mission = True
                first_hour = True
                first_time = True

                for mission_name, mission_data in data['missions'].items():
                    # Thêm mission với dấu -
                    if first_mission:
                        p = cell.paragraphs[0]
                        first_mission = False
                    else:
                        p = cell.add_paragraph()
                    p.text = f"- {mission_name}"

                    # Thêm tất cả lessons với dấu +
                    for lesson in mission_data['lessons']:
                        p = cell.add_paragraph()
                        p.text = f"  + {lesson}"

                    # Thêm hours cho mission này
                    for hour in mission_data['hours']:
                        if first_hour:
                            p_hour = cell_hours.paragraphs[0]
                            first_hour = False
                        else:
                            p_hour = cell_hours.add_paragraph()
                        p_hour.text = str(hour) if hour else "0"
                        p_hour.alignment = WD_ALIGN_PARAGRAPH.CENTER

                    # Thêm times cho mission này
                    for time_str in mission_data['times']:
                        if first_time:
                            p_time = cell_time.paragraphs[0]
                            first_time = False
                        else:
                            p_time = cell_time.add_paragraph()
                        p_time.text = time_str
                        p_time.alignment = WD_ALIGN_PARAGRAPH.CENTER

        elif self.report_type == 'month':
            self.replace_placeholder_with_text(doc, "{{year}}", self.year)
            self.replace_placeholder_with_text(doc, "{{month}}", self.month)
            self.print_table(doc, 0)
            letters = string.ascii_lowercase

            def get_lower_letter(index):
                """Chuyển index thành chữ cái: 0->a, 25->z, 26->aa, 27->ab..."""
                result = ""
                while index >= 0:
                    result = chr(index % 26 + 97) + result
                    index = index // 26 - 1
                return result

            TrainingDay = self.env['training.day']
            domain = [
                ('year', '=', self.year),
                ('month_name', '=', f'Tháng {self.month}'),
            ]
            records = TrainingDay.search(domain)
            print(records)
            if not records:
                raise UserError('Không tìm thấy dữ liệu!')

            subject_hours = {
                'CT': 'chinh_tri_hours',
                'GDPL': 'phap_luat_hours',
                'HC': 'hau_can_hours',
                'KT': 'ky_thuat_hours',
                'DL': 'dieu_lenh_hours',
                'KTCD': 'cdbb_hours',
                'BS': 'ban_sung_hours',
                'TLCM': 'tl_chuyen_mon_hours',
                'TLC': 'tl_chung_hours'
            }

            # Khởi tạo dictionary để lưu tổng giờ
            hours_dict = {key: 0 for key in subject_hours.values()}

            # Group và tính tổng giờ trong 1 vòng lặp
            grouped_by_plan = defaultdict(lambda: {'records': [], 'total_hours': 0})
            for record in records:
                grouped_by_plan[record.plan_name]['records'].append(record)
                grouped_by_plan[record.plan_name]['total_hours'] += (record.total_hours or 0)

                if record.subject_code in subject_hours:
                    var_name = subject_hours[record.subject_code]
                    hours_dict[var_name] += (record.total_hours or 0)

            chinh_tri_hours = hours_dict['chinh_tri_hours']
            phap_luat_hours = hours_dict['phap_luat_hours']
            hau_can_hours = hours_dict['hau_can_hours']
            ky_thuat_hours = hours_dict['ky_thuat_hours']
            dieu_lenh_hours = hours_dict['dieu_lenh_hours']
            cdbb_hours = hours_dict['cdbb_hours']
            ban_sung_hours = hours_dict['ban_sung_hours']
            tl_chuyen_mon_hours = hours_dict['tl_chuyen_mon_hours']
            tl_chung_hours = hours_dict['tl_chung_hours']

            # Lấy table và điền dữ liệu
            table = doc.tables[0]
            row_index = 2

            for letter_index, (plan_name, data) in enumerate(grouped_by_plan.items()):
                # Thêm hàng nếu cần
                while row_index >= len(table.rows):
                    table.add_row()

                row = table.rows[row_index]

                # Điền chữ cái
                row.cells[0].text = letters[letter_index] if letter_index < 26 else get_lower_letter(letter_index)
                row.cells[0].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER

                # Điền dữ liệu
                row.cells[1].text = plan_name or ""
                row.cells[2].text = str(data['total_hours'])
                row.cells[3].text = str(chinh_tri_hours)
                row.cells[4].text = str(phap_luat_hours)
                row.cells[5].text = str(hau_can_hours)
                row.cells[6].text = str(ky_thuat_hours)
                row.cells[7].text = str(dieu_lenh_hours)
                row.cells[8].text = str(cdbb_hours)
                row.cells[9].text = str(ban_sung_hours)
                row.cells[10].text = str(tl_chuyen_mon_hours)
                row.cells[11].text = str(tl_chung_hours)

                # Căn giữa các ô từ 2 đến 11
                for i in range(2, 12):
                    row.cells[i].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER

                row.cells[12].text = "HL thể lực =35% tổng số thời gian"

                row_index += 1

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
