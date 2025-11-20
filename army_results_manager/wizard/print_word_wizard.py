# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.modules.module import get_module_resource
from io import BytesIO
import base64
import string
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_ALIGN_VERTICAL
from datetime import date
from odoo.exceptions import UserError
from collections import defaultdict
from docx.shared import Cm
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches
from docx.shared import Pt


class PrintWordWizard(models.TransientModel):
    _name = "print.word.wizard"
    _description = "Wizard chọn mẫu in Word/Excel"

    mau_in = fields.Selection(
        [('template1', 'Phụ lục 1'),
         ('template2', 'Phụ lục 2'),
         ('template3', 'Phụ lục 3'),
         ('template4', 'Phụ lục 4'),
         ('template5', 'Phụ lục 5')]
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

    approver_id = fields.Many2one('hr.employee', string='Cán bộ phê duyệt',
                                  domain=[('role', '=', 'commanding_officer')])
    attachment_ids = fields.Many2many(
        'ir.attachment',
        string='Tài liệu PDF',
        domain=[('mimetype', '=', 'application/pdf')]
    )

    # ==================== Helper Functions ====================

    def action_send_report(self):
        TrainingDay = self.env['training.day']

        if not self.approver_id:
            raise UserError('Bạn phải chọn người phê duyệt trước khi bấm Gửi duyệt!')
        elif not self.attachment_ids:
            raise UserError('File Pdf không được trống!')
        domain = [
            ('year', '=', self.year),
            ('month_name', '=', f'Tháng {self.month}'),
            ('week_name', '=', f'Tuần {self.week}'),
        ]
        records = TrainingDay.search(domain)
        records.write({'attachment_ids': [(6, 0, self.attachment_ids.ids)]})



    @api.onchange('report_type')
    def _onchange_report_type(self):
        if self.report_type:
            self.week = self.month = False

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

    def int_to_roman(self, num):
        """Chuyển số nguyên sang số La Mã"""
        val = [
            1000, 900, 500, 400,
            100, 90, 50, 40,
            10, 9, 5, 4,
            1
        ]
        syms = [
            "M", "CM", "D", "CD",
            "C", "XC", "L", "XL",
            "X", "IX", "V", "IV",
            "I"
        ]
        roman_num = ''
        i = 0
        while num > 0:
            for _ in range(num // val[i]):
                roman_num += syms[i]
                num -= val[i]
            i += 1
        return roman_num

    def _format_hours(self, hours):
        """Định dạng số giờ: 0 để trống, số thực có .0 thì chuyển thành số nguyên"""
        if not hours:
            return ""

        # Chuyển đổi sang số nếu có thể
        try:
            hours_float = float(hours)
            if hours_float == 0:
                return ""
            # Nếu là số nguyên thì trả về dạng nguyên, ngược lại giữ nguyên
            if hours_float.is_integer():
                return str(int(hours_float))
            return str(hours_float)
        except (ValueError, TypeError):
            return str(hours) if hours else ""

    def _ensure_table_rows(self, table, required_index):
        """Đảm bảo table có đủ rows đến required_index"""
        while required_index >= len(table.rows):
            table.add_row()

    def _get_mission_month(self, mission):
        """Lấy tháng từ mission.mission_line_ids.day_ids.month"""
        months = set()
        for line in mission.mission_line_ids:
            for day in line.day_ids:
                if day.month:
                    months.add(day.month)

        if months:
            # Trả về tháng đầu tiên (có thể điều chỉnh logic theo nhu cầu)
            return sorted(months)[0]
        return None

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

            # NHÓM THEO COURSE_NAME VÀ NGÀY
            grouped_records = {}

            for record in records:
                weekday_text = weekday_map.get(record.weekday, record.weekday)
                day_str = record.day.strftime("%d/%m/%Y")
                key = (weekday_text, day_str)

                # Khởi tạo cấu trúc cho key nếu chưa tồn tại
                if key not in grouped_records:
                    grouped_records[key] = {}

                # Nhóm theo course_name
                course_name = record.course_name or "Không có tên khóa"
                if course_name not in grouped_records[key]:
                    grouped_records[key][course_name] = {
                        'lessons': [],  # Danh sách bài học
                        'total_hours': 0,  # Tổng số giờ
                        'times': []  # Danh sách thời gian
                    }

                # Thêm bài học nếu chưa có
                if record.lesson_name and record.lesson_name not in grouped_records[key][course_name]['lessons']:
                    grouped_records[key][course_name]['lessons'].append(record.lesson_name)

                # Cộng dồn tổng giờ
                grouped_records[key][course_name]['total_hours'] += (record.total_hours or 0)

                # Thêm thời gian
                for time_rec in record.time_ids:
                    if time_rec.start_time and time_rec.end_time:
                        # Chuyển đổi trực tiếp
                        start_h = int(time_rec.start_time)
                        start_m = int((time_rec.start_time - start_h) * 60)
                        end_h = int(time_rec.end_time)
                        end_m = int((time_rec.end_time - end_h) * 60)

                        time_str = f"{start_h:02d}:{start_m:02d} - {end_h:02d}:{end_m:02d}"
                        if time_str not in grouped_records[key][course_name]['times']:
                            grouped_records[key][course_name]['times'].append(time_str)

            # Điền vào bảng - CHỈ 1 HÀNG CHO MỖI NGÀY
            for (weekday, day_str), courses_data in grouped_records.items():
                # Thêm 1 hàng mới cho mỗi ngày
                new_row = table.add_row()

                # Điền weekday và ngày vào cùng 1 cell
                new_row.cells[0].text = f"{weekday}\n{day_str}"
                new_row.cells[0].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER

                # Điền course_name và lessons vào cell[1]
                cell_content = new_row.cells[1]
                cell_content.text = ""

                # Điền hours vào cell[2]
                cell_hours = new_row.cells[2]
                cell_hours.text = ""

                # Điền time vào cell[3]
                cell_time = new_row.cells[3]
                cell_time.text = ""

                for course_name, course_data in courses_data.items():
                    # Thêm course_name với dấu :
                    p_course = cell_content.add_paragraph()
                    p_course.text = f"{course_name}:"

                    # Thêm tất cả lessons với dấu +
                    for lesson in course_data['lessons']:
                        p_lesson = cell_content.add_paragraph()
                        p_lesson.text = f"  + {lesson}"

                    # Thêm tổng hours cho course này
                    p_hour = cell_hours.add_paragraph()
                    p_hour.text = f"{course_data['total_hours']:g}" if course_data['total_hours'] else "0"
                    p_hour.alignment = WD_ALIGN_PARAGRAPH.CENTER

                    # Thêm times cho course này
                    for time_str in course_data['times']:
                        p_time = cell_time.add_paragraph()
                        p_time.text = time_str
                        p_time.alignment = WD_ALIGN_PARAGRAPH.CENTER

        elif self.report_type == 'month':
            self.replace_placeholder_with_text(doc, "{{year}}", self.year)
            self.replace_placeholder_with_text(doc, "{{month}}", self.month)

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
            if not records:
                raise UserError('Không tìm thấy dữ liệu!')

            # Table 1
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

            # Group và tính tổng giờ trong 1 vòng lặp
            grouped_by_plan = defaultdict(lambda: {
                'records': [],
                'total_hours': 0,
                'chinh_tri_hours': 0,
                'phap_luat_hours': 0,
                'hau_can_hours': 0,
                'ky_thuat_hours': 0,
                'dieu_lenh_hours': 0,
                'cdbb_hours': 0,
                'ban_sung_hours': 0,
                'tl_chuyen_mon_hours': 0,
                'tl_chung_hours': 0
            })

            grouped_by_course_common = defaultdict(lambda: {'records': [], 'total_hours': 0})
            grouped_by_course_private = defaultdict(lambda: {'records': [], 'total_hours': 0})

            course_number = 1
            total_common_hours = 0

            for record in records:
                plan_name = record.plan_name
                grouped_by_plan[plan_name]['records'].append(record)
                grouped_by_plan[plan_name]['total_hours'] += (record.total_hours or 0)

                # Tính tổng giờ theo môn học cho từng plan
                if record.subject_code in subject_hours:
                    var_name = subject_hours[record.subject_code]
                    grouped_by_plan[plan_name][var_name] += (record.total_hours or 0)

                if record.type_training == 'common_training':
                    grouped_by_course_common[record.course_name]['records'].append(record)
                    grouped_by_course_common[record.course_name]['total_hours'] += (record.total_hours or 0)
                    total_common_hours += (record.total_hours or 0)

                elif record.type_training == 'private_training':
                    grouped_by_course_private[record.course_name]['records'].append(record)
                    grouped_by_course_private[record.course_name]['total_hours'] += (record.total_hours or 0)

            # Lấy table và điền dữ liệu
            table = doc.tables[0]
            row_index = 2

            letters = string.ascii_lowercase

            for letter_index, (plan_name, data) in enumerate(grouped_by_plan.items()):
                # Thêm hàng nếu cần
                while row_index >= len(table.rows):
                    table.add_row()

                row = table.rows[row_index]

                # Điền chữ cái
                row.cells[0].text = letters[letter_index] if letter_index < 26 else get_lower_letter(letter_index)
                row.cells[0].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER

                # Điền dữ liệu - MỖI PLAN CÓ GIÁ TRỊ RIÊNG
                row.cells[1].text = plan_name or ""
                row.cells[2].text = f"{data['total_hours']:g}" if data['total_hours'] else ""
                row.cells[3].text = f"{data['chinh_tri_hours']:g}" if data['chinh_tri_hours'] else ""
                row.cells[4].text = f"{data['phap_luat_hours']:g}" if data['phap_luat_hours'] else ""
                row.cells[5].text = f"{data['hau_can_hours']:g}" if data['hau_can_hours'] else ""
                row.cells[6].text = f"{data['ky_thuat_hours']:g}" if data['ky_thuat_hours'] else ""
                row.cells[7].text = f"{data['dieu_lenh_hours']:g}" if data['dieu_lenh_hours'] else ""
                row.cells[8].text = f"{data['cdbb_hours']:g}" if data['cdbb_hours'] else ""
                row.cells[9].text = f"{data['ban_sung_hours']:g}" if data['ban_sung_hours'] else ""
                row.cells[10].text = f"{data['tl_chuyen_mon_hours']:g}" if data['tl_chuyen_mon_hours'] else ""
                row.cells[11].text = f"{data['tl_chung_hours']:g}" if data['tl_chung_hours'] else ""

                # Căn giữa các ô từ 2 đến 11
                for i in range(2, 12):
                    row.cells[i].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER

                row.cells[12].text = "HL thể lực =35% tổng số thời gian"
                row_index += 1

            # Table 2

            def get_column_index(week_name, weekday):
                """Tính column index dựa trên tuần và thứ"""
                week_number = int(week_name.replace('Tuần', '').strip())
                weekday_map = {
                    'Thứ Hai': 2, 'Thứ Ba': 3, 'Thứ Tư': 4, 'Thứ Năm': 5, 'Thứ Sáu': 6, 'Thứ Bảy': 7,
                    'Thứ 2': 2, 'Thứ 3': 3, 'Thứ 4': 4, 'Thứ 5': 5, 'Thứ 6': 6, 'Thứ 7': 7,
                }

                weekday_number = weekday_map.get(weekday.strip())

                if weekday_number is None or weekday_number < 2 or weekday_number > 6:
                    return None

                weekday_offset = weekday_number - 2
                column_index = 5 + (week_number - 1) * 5 + weekday_offset

                return column_index

            def set_cell_alignment(cell, h_align=WD_ALIGN_PARAGRAPH.CENTER, v_align=WD_ALIGN_VERTICAL.CENTER):
                """Helper function để set alignment cho cell"""
                cell.paragraphs[0].alignment = h_align
                cell.vertical_alignment = v_align

            table_2 = doc.tables[1]

            row_index_2 = 4

            # Set tổng giờ chung

            table_2.rows[3].cells[4].text = f"{total_common_hours:g}" if total_common_hours else ""

            set_cell_alignment(table_2.rows[3].cells[4])

            lesson_letter_index = 0  # Biến riêng cho letter của lessons

            # Hàm xử lý dữ liệu cho các course (chung và riêng)

            def process_course_data(course_data, is_common=True):
                nonlocal course_number, row_index_2, lesson_letter_index

                for course_name, data in course_data.items():
                    # NHÓM CÁC LESSON THEO lesson_name VÀ TÍNH TỔNG HOURS
                    grouped_lessons = defaultdict(lambda: {'total_hours': 0, 'week_data': []})

                    for record in data['records']:
                        lesson_name = record.lesson_name or ""
                        grouped_lessons[lesson_name]['total_hours'] += (record.total_hours or 0)

                        # Lưu thông tin tuần và thứ cho mỗi lesson
                        if record.week_name and record.weekday:
                            grouped_lessons[lesson_name]['week_data'].append({
                                'week_name': record.week_name,
                                'weekday': record.weekday,
                                'hours': record.total_hours or 0
                            })

                    # Thêm hàng cho course
                    while row_index_2 >= len(table_2.rows):
                        table_2.add_row()

                    row = table_2.rows[row_index_2]

                    # Điền dữ liệu course
                    row.cells[0].text = str(course_number)
                    row.cells[1].text = course_name or ""
                    row.cells[4].text = f"{data['total_hours']:g}" if data['total_hours'] else ""
                    row.cells[26].text = "HL theo đội hình Trung tâm, ôn luyện theo đội hình Đoàn"

                    set_cell_alignment(row.cells[0])

                    # Căn giữa các ô từ 4 đến 11
                    for i in range(4, 12):
                        set_cell_alignment(row.cells[i])

                    course_number += 1
                    row_index_2 += 1

                    # Duyệt qua các lesson đã được nhóm

                    for lesson_name, lesson_data in grouped_lessons.items():
                        while row_index_2 >= len(table_2.rows):
                            table_2.add_row()

                        lesson_row = table_2.rows[row_index_2]
                        # Sử dụng lesson_letter_index riêng, bắt đầu từ 'a' cho mỗi course
                        lesson_row.cells[0].text = letters[
                            lesson_letter_index] if lesson_letter_index < 26 else get_lower_letter(lesson_letter_index)
                        lesson_row.cells[1].text = lesson_name or ""
                        lesson_row.cells[4].text = f"{lesson_data['total_hours']:g}" if lesson_data[
                            'total_hours'] else ""

                        # Điền giờ vào cột tuần/thứ tương ứng cho từng lesson
                        for week_info in lesson_data['week_data']:
                            col_index = get_column_index(week_info['week_name'], week_info['weekday'])
                            if col_index is not None and col_index < len(lesson_row.cells):
                                # Cộng dồn nếu đã có giá trị
                                current_value = lesson_row.cells[col_index].text.strip()

                                if current_value:
                                    try:
                                        current_hours = float(current_value)
                                        total_hours = current_hours + week_info['hours']
                                        lesson_row.cells[col_index].text = f"{total_hours:g}"
                                    except ValueError:
                                        lesson_row.cells[col_index].text = f"{week_info['hours']:g}"
                                else:
                                    lesson_row.cells[col_index].text = f"{week_info['hours']:g}"

                            elif col_index is not None:
                                print(
                                    f"Warning: Column index {col_index} out of range. Table has {len(lesson_row.cells)} columns.")
                                print(f"Week: {week_info['week_name']}, Weekday: {week_info['weekday']}")

                        set_cell_alignment(lesson_row.cells[0])

                        # Căn giữa các ô
                        for i in range(4, min(12, len(lesson_row.cells))):
                            lesson_row.cells[i].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER

                        lesson_letter_index += 1  # Tăng letter index cho lesson
                        row_index_2 += 1

                    # Reset letter index về 'a' cho course tiếp theo
                    lesson_letter_index = 0

            # Xử lý các môn chung
            process_course_data(grouped_by_course_common, is_common=True)

            # Lưu lại vị trí kết thúc của môn chung để tính tổng
            end_common_row = row_index_2

            # Tính tổng cho các cột từ 5 đến 25 ở hàng 3 (chỉ trong phạm vi môn chung)
            for col_index in range(5, 26):
                total = 0

                # Duyệt qua các hàng từ 4 đến end_common_row (không bao gồm end_common_row)
                for row_idx in range(4, end_common_row):
                    cell_text = table_2.rows[row_idx].cells[col_index].text.strip()

                    if cell_text:
                        try:
                            total += float(cell_text)
                        except ValueError:
                            pass  # Bỏ qua nếu không phải số

                # Ghi tổng vào hàng 3
                if total > 0:
                    table_2.rows[3].cells[col_index].text = f"{total:g}"

                    set_cell_alignment(table_2.rows[3].cells[col_index])

            # Thêm dòng "B. HUẤN LUYỆN RIÊNG" vào cuối table

            while row_index_2 >= len(table_2.rows):
                table_2.add_row()

            private_header_row = table_2.rows[row_index_2]

            private_header_row.cells[0].text = "B"

            private_header_row.cells[1].text = "HUẤN LUYỆN RIÊNG"

            private_header_row.cells[1].merge(private_header_row.cells[3])

            set_cell_alignment(private_header_row.cells[0])

            row_index_2 += 1

            # Xử lý các môn riêng
            course_number = 1

            process_course_data(grouped_by_course_private, is_common=False)

            # self.print_table(doc, 1)

        elif self.report_type == 'year':

            self.replace_placeholder_with_text(doc, "{{year}}", self.year)

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

            TrainingDay = self.env['training.day']
            domain = [('year', '=', self.year)]
            records = TrainingDay.search(domain)

            if not records:
                raise UserError('Không tìm thấy dữ liệu!')

            table_index = 0

            if table_index >= len(doc.tables):
                raise UserError('Không tìm thấy table!')

            table = doc.tables[table_index]

            # Lấy set của tất cả plan_id (unique plans)
            plan_ids_set = set()

            for record in records:
                if record.plan_id:
                    plan_ids_set.add(record.plan_id.id)

            # Chuyển sang list và lấy plan objects

            plan_ids = list(plan_ids_set)
            Plan = self.env['training.plan']
            plans = Plan.browse(plan_ids)

            self.replace_placeholder_with_table(doc, "{{table_1}}", plans, rows_data_table_1)
            self.replace_placeholder_with_table(doc, "{{table_2}}", plans, rows_data_table_2, note=" ")
            self.replace_table_3_aasam(doc, "{{table_3}}", plans)

            def set_cell_alignment(cell, h_align=WD_ALIGN_PARAGRAPH.CENTER, v_align=WD_ALIGN_VERTICAL.CENTER):
                """Helper function để set alignment cho cell"""
                cell.paragraphs[0].alignment = h_align
                cell.vertical_alignment = v_align

            # Xử lý table thứ 4 si quan
            records_si_quan = records.filtered(lambda m: m.type_plan == 'officer')
            if len(doc.tables) > 4:
                table_4 = doc.tables[4]

                # Bắt đầu từ row 2
                row_index = 2
                plan_counter = 1

                # Tối ưu: cache các hàm
                format_hours = self._format_hours
                ensure_rows = self._ensure_table_rows
                get_mission_month = self._get_mission_month
                int_to_roman = self.int_to_roman

                # NHÓM TRỰC TIẾP THEO PLAN VÀ COURSE - SỬA LỖI TÍNH GIỜ
                plans_data = {}

                for record in records_si_quan:
                    plan = record.plan_id
                    course = record.course_id
                    mission = record.mission_id

                    if not plan or not mission:
                        continue

                    # Khởi tạo cấu trúc dữ liệu cho plan
                    if plan not in plans_data:
                        plans_data[plan] = {
                            'common_courses': {},
                            'private_courses': {},
                            'total_hours': 0,
                            'processed_missions': set()  # THEO DÕI MISSION ĐÃ XỬ LÝ
                        }

                    # Tạo khóa duy nhất cho mission trong plan
                    mission_key = (mission.id, course.id if course else None)

                    # Nếu mission đã được xử lý trong plan này, bỏ qua
                    if mission_key in plans_data[plan]['processed_missions']:
                        continue

                    # Đánh dấu mission đã xử lý
                    plans_data[plan]['processed_missions'].add(mission_key)

                    # Xác định loại training
                    courses_dict = plans_data[plan]['common_courses'] if record.type_training == 'common_training' else \
                    plans_data[plan]['private_courses']

                    # Khởi tạo course
                    if course not in courses_dict:
                        courses_dict[course] = {
                            'missions': {},
                            'total_hours': 0,
                            'subject_obj': course
                        }

                    # Xử lý mission - CHỈ TÍNH 1 LẦN
                    mission_name = mission.name or ""
                    mission_month = get_mission_month(mission) if mission else 0
                    mission_hours = mission.total_hours or 0

                    # LUÔN TẠO MISSION MỚI - KHÔNG CỘNG DỒN
                    courses_dict[course]['missions'][mission_name] = {
                        'total_hours': mission_hours,  # CHỈ LẤY GIỜ TỪ MISSION, KHÔNG CỘNG DỒN
                        'month': mission_month,
                        'mission_obj': mission
                    }

                    # Cập nhật tổng giờ - CHỈ CỘNG 1 LẦN
                    courses_dict[course]['total_hours'] += mission_hours
                    plans_data[plan]['total_hours'] += mission_hours

                # DEBUG: In ra để kiểm tra
                print("=== DEBUG PLANS DATA ===")
                for plan, plan_data in plans_data.items():
                    print(f"Plan: {plan.name}, Total hours: {plan_data['total_hours']}")
                    print("Common courses:")
                    for course, course_data in plan_data['common_courses'].items():
                        course_name = course.name if course else "No Course"
                        print(f"  - {course_name}: {course_data['total_hours']} hours")
                        for mission_name, mission_data in course_data['missions'].items():
                            print(f"    * {mission_name}: {mission_data['total_hours']} hours")
                    print("Private courses:")
                    for course, course_data in plan_data['private_courses'].items():
                        course_name = course.name if course else "No Course"
                        print(f"  - {course_name}: {course_data['total_hours']} hours")
                        for mission_name, mission_data in course_data['missions'].items():
                            print(f"    * {mission_name}: {mission_data['total_hours']} hours")
                print("========================")

                # DUYỆT QUA CÁC PLAN ĐÃ ĐƯỢC NHÓM
                for plan, plan_data in plans_data.items():
                    common_courses = plan_data['common_courses']
                    private_courses = plan_data['private_courses']
                    total_plan_hours = plan_data['total_hours']

                    # DÒNG PLAN (I, II, III,...)
                    roman_numeral = int_to_roman(plan_counter)
                    ensure_rows(table_4, row_index)
                    row = table_4.rows[row_index]
                    row.cells[1].merge(row.cells[3])
                    row.cells[0].text = roman_numeral
                    set_cell_alignment(row.cells[0])
                    row.cells[1].text = plan.name or ""
                    row.cells[4].text = format_hours(total_plan_hours)
                    set_cell_alignment(row.cells[4])
                    row_index += 1

                    # PHẦN 1: HUẤN LUYỆN CHUNG
                    if common_courses:
                        # Dòng "1. Huấn luyện chung các đối tượng"
                        ensure_rows(table_4, row_index)
                        row = table_4.rows[row_index]
                        row.cells[1].merge(row.cells[3])
                        row.cells[0].text = "1"
                        set_cell_alignment(row.cells[0])
                        row.cells[1].text = "Huấn luyện chung các đối tượng"
                        row_index += 1

                        # ĐIỀN CÁC COURSE CỦA HUẤN LUYỆN CHUNG (1.1, 1.2,...)
                        common_subject_counter = 1
                        for course, course_data in common_courses.items():
                            course_name = course.name or "" if course else ""

                            ensure_rows(table_4, row_index)
                            row = table_4.rows[row_index]

                            # Merge cells cho course
                            row.cells[1].merge(row.cells[3])
                            row.cells[0].text = f"1.{common_subject_counter}"
                            set_cell_alignment(row.cells[0])
                            row.cells[1].text = course_name

                            # Điền tổng giờ
                            row.cells[4].text = format_hours(course_data['total_hours'])
                            set_cell_alignment(row.cells[4])

                            # Điền giờ theo tháng nếu có
                            mission_month = None
                            for mission_data in course_data['missions'].values():
                                if mission_data['month'] and 1 <= mission_data['month'] <= 12:
                                    mission_month = mission_data['month']
                                    break

                            if mission_month:
                                col_idx = 4 + mission_month
                                if col_idx < len(row.cells):
                                    row.cells[col_idx].text = format_hours(course_data['total_hours'])
                                    set_cell_alignment(row.cells[col_idx])

                            row_index += 1

                            # ĐIỀN CÁC MISSION CỦA COURSE (a, b, c,...)
                            mission_counter = 0
                            mission_start_row = None

                            for mission_name, mission_data in course_data['missions'].items():
                                ensure_rows(table_4, row_index)

                                if mission_start_row is None:
                                    mission_start_row = row_index

                                mission_row = table_4.rows[row_index]

                                # Đánh số mission (a, b, c, ...)
                                mission_row.cells[0].text = chr(97 + mission_counter)
                                set_cell_alignment(mission_row.cells[0])
                                mission_row.cells[1].text = mission_name

                                # Chỉ điền thông tin phân loại cho mission đầu tiên
                                if mission_counter == 0:
                                    subject_obj = course_data['subject_obj']
                                    participant_text = subject_obj.participant_category_id.name or "" if subject_obj and subject_obj.participant_category_id else ""
                                    responsible_text = subject_obj.responsible_level_id.name or "" if subject_obj and subject_obj.responsible_level_id else ""

                                    mission_row.cells[2].text = participant_text
                                    mission_row.cells[3].text = responsible_text
                                    set_cell_alignment(mission_row.cells[2])
                                    set_cell_alignment(mission_row.cells[3])

                                # Điền giờ theo tháng cho mission
                                mission_month = mission_data['month']
                                if mission_month and 1 <= mission_month <= 12:
                                    col_idx = 4 + mission_month
                                    if col_idx < len(mission_row.cells):
                                        mission_row.cells[col_idx].text = format_hours(mission_data['total_hours'])
                                        set_cell_alignment(mission_row.cells[col_idx])

                                mission_counter += 1
                                row_index += 1

                            # Merge cột phân loại nếu có nhiều mission
                            if mission_counter > 1 and mission_start_row is not None:
                                mission_end_row = row_index - 1
                                table_4.rows[mission_start_row].cells[2].merge(table_4.rows[mission_end_row].cells[2])
                                table_4.rows[mission_start_row].cells[3].merge(table_4.rows[mission_end_row].cells[3])

                            common_subject_counter += 1

                    # PHẦN 2: HUẤN LUYỆN RIÊNG
                    if private_courses:
                        # Dòng "2. Huấn luyện riêng các đối tượng"
                        ensure_rows(table_4, row_index)
                        row = table_4.rows[row_index]
                        row.cells[1].merge(row.cells[3])
                        row.cells[0].text = "2"
                        set_cell_alignment(row.cells[0])
                        row.cells[1].text = "Huấn luyện riêng các đối tượng"
                        row_index += 1

                        # ĐIỀN CÁC COURSE CỦA HUẤN LUYỆN RIÊNG (2.1, 2.2,...)
                        private_subject_counter = 1
                        for course, course_data in private_courses.items():
                            course_name = course.name or "" if course else ""

                            ensure_rows(table_4, row_index)
                            row = table_4.rows[row_index]

                            # Merge cells cho course
                            row.cells[1].merge(row.cells[3])
                            row.cells[0].text = f"2.{private_subject_counter}"
                            set_cell_alignment(row.cells[0])
                            row.cells[1].text = course_name

                            # Điền tổng giờ
                            row.cells[4].text = format_hours(course_data['total_hours'])
                            set_cell_alignment(row.cells[4])

                            # Điền giờ theo tháng nếu có
                            mission_month = None
                            for mission_data in course_data['missions'].values():
                                if mission_data['month'] and 1 <= mission_data['month'] <= 12:
                                    mission_month = mission_data['month']
                                    break

                            if mission_month:
                                col_idx = 4 + mission_month
                                if col_idx < len(row.cells):
                                    row.cells[col_idx].text = format_hours(course_data['total_hours'])
                                    set_cell_alignment(row.cells[col_idx])

                            row_index += 1

                            # ĐIỀN CÁC MISSION CỦA COURSE (a, b, c,...)
                            mission_counter = 0
                            mission_start_row = None

                            for mission_name, mission_data in course_data['missions'].items():
                                ensure_rows(table_4, row_index)

                                if mission_start_row is None:
                                    mission_start_row = row_index

                                mission_row = table_4.rows[row_index]

                                # Đánh số mission (a, b, c, ...)
                                mission_row.cells[0].text = chr(97 + mission_counter)
                                set_cell_alignment(mission_row.cells[0])
                                mission_row.cells[1].text = mission_name

                                # Chỉ điền thông tin phân loại cho mission đầu tiên
                                if mission_counter == 0:
                                    subject_obj = course_data['subject_obj']
                                    participant_text = subject_obj.participant_category_id.name or "" if subject_obj and subject_obj.participant_category_id else ""
                                    responsible_text = subject_obj.responsible_level_id.name or "" if subject_obj and subject_obj.responsible_level_id else ""

                                    mission_row.cells[2].text = participant_text
                                    mission_row.cells[3].text = responsible_text
                                    set_cell_alignment(mission_row.cells[2])
                                    set_cell_alignment(mission_row.cells[3])

                                # Điền giờ theo tháng cho mission
                                mission_month = mission_data['month']
                                if mission_month and 1 <= mission_month <= 12:
                                    col_idx = 4 + mission_month
                                    if col_idx < len(mission_row.cells):
                                        mission_row.cells[col_idx].text = format_hours(mission_data['total_hours'])
                                        set_cell_alignment(mission_row.cells[col_idx])

                                mission_counter += 1
                                row_index += 1

                            # Merge cột phân loại nếu có nhiều mission
                            if mission_counter > 1 and mission_start_row is not None:
                                mission_end_row = row_index - 1
                                table_4.rows[mission_start_row].cells[2].merge(table_4.rows[mission_end_row].cells[2])
                                table_4.rows[mission_start_row].cells[3].merge(table_4.rows[mission_end_row].cells[3])

                            private_subject_counter += 1

                    plan_counter += 1

            records_phan_doi = records.filtered(lambda m: m.type_plan == 'squad')
            if len(doc.tables) > 5:
                table_5 = doc.tables[5]

                # Bắt đầu từ row 2
                row_index = 2
                plan_counter = 1

                # Tối ưu: cache các hàm
                format_hours = self._format_hours
                ensure_rows = self._ensure_table_rows
                get_mission_month = self._get_mission_month
                int_to_roman = self.int_to_roman

                # NHÓM TRỰC TIẾP THEO PLAN VÀ COURSE - SỬA LỖI TÍNH GIỜ
                plans_data = {}

                for record in records_phan_doi:
                    plan = record.plan_id
                    course = record.course_id
                    mission = record.mission_id

                    if not plan or not mission:
                        continue

                    # Khởi tạo cấu trúc dữ liệu cho plan
                    if plan not in plans_data:
                        plans_data[plan] = {
                            'common_courses': {},
                            'private_courses': {},
                            'total_hours': 0,
                            'processed_missions': set()  # THEO DÕI MISSION ĐÃ XỬ LÝ
                        }

                    # Tạo khóa duy nhất cho mission trong plan
                    mission_key = (mission.id, course.id if course else None)

                    # Nếu mission đã được xử lý trong plan này, bỏ qua
                    if mission_key in plans_data[plan]['processed_missions']:
                        continue

                    # Đánh dấu mission đã xử lý
                    plans_data[plan]['processed_missions'].add(mission_key)

                    # Xác định loại training
                    courses_dict = plans_data[plan]['common_courses'] if record.type_training == 'common_training' else \
                        plans_data[plan]['private_courses']

                    # Khởi tạo course
                    if course not in courses_dict:
                        courses_dict[course] = {
                            'missions': {},
                            'total_hours': 0,
                            'subject_obj': course
                        }

                    # Xử lý mission - CHỈ TÍNH 1 LẦN
                    mission_name = mission.name or ""
                    mission_month = get_mission_month(mission) if mission else 0
                    mission_hours = mission.total_hours or 0

                    # LUÔN TẠO MISSION MỚI - KHÔNG CỘNG DỒN
                    courses_dict[course]['missions'][mission_name] = {
                        'total_hours': mission_hours,  # CHỈ LẤY GIỜ TỪ MISSION, KHÔNG CỘNG DỒN
                        'month': mission_month,
                        'mission_obj': mission
                    }

                    # Cập nhật tổng giờ - CHỈ CỘNG 1 LẦN
                    courses_dict[course]['total_hours'] += mission_hours
                    plans_data[plan]['total_hours'] += mission_hours

                # DEBUG: In ra để kiểm tra
                print("=== DEBUG PLANS DATA ===")
                for plan, plan_data in plans_data.items():
                    print(f"Plan: {plan.name}, Total hours: {plan_data['total_hours']}")
                    print("Common courses:")
                    for course, course_data in plan_data['common_courses'].items():
                        course_name = course.name if course else "No Course"
                        print(f"  - {course_name}: {course_data['total_hours']} hours")
                        for mission_name, mission_data in course_data['missions'].items():
                            print(f"    * {mission_name}: {mission_data['total_hours']} hours")
                    print("Private courses:")
                    for course, course_data in plan_data['private_courses'].items():
                        course_name = course.name if course else "No Course"
                        print(f"  - {course_name}: {course_data['total_hours']} hours")
                        for mission_name, mission_data in course_data['missions'].items():
                            print(f"    * {mission_name}: {mission_data['total_hours']} hours")
                print("========================")

                # DUYỆT QUA CÁC PLAN ĐÃ ĐƯỢC NHÓM
                for plan, plan_data in plans_data.items():
                    common_courses = plan_data['common_courses']
                    private_courses = plan_data['private_courses']
                    total_plan_hours = plan_data['total_hours']

                    # DÒNG PLAN (I, II, III,...)
                    roman_numeral = int_to_roman(plan_counter)
                    ensure_rows(table_5, row_index)
                    row = table_5.rows[row_index]
                    row.cells[1].merge(row.cells[3])
                    row.cells[0].text = roman_numeral
                    set_cell_alignment(row.cells[0])
                    row.cells[1].text = plan.name or ""
                    row.cells[4].text = format_hours(total_plan_hours)
                    set_cell_alignment(row.cells[4])
                    row_index += 1

                    # PHẦN 1: HUẤN LUYỆN CHUNG
                    if common_courses:
                        # Dòng "1. Huấn luyện chung các đối tượng"
                        ensure_rows(table_5, row_index)
                        row = table_5.rows[row_index]
                        row.cells[1].merge(row.cells[3])
                        row.cells[0].text = "1"
                        set_cell_alignment(row.cells[0])
                        row.cells[1].text = "Huấn luyện chung các đối tượng"
                        row_index += 1

                        # ĐIỀN CÁC COURSE CỦA HUẤN LUYỆN CHUNG (1.1, 1.2,...)
                        common_subject_counter = 1
                        for course, course_data in common_courses.items():
                            course_name = course.name or "" if course else ""

                            ensure_rows(table_5, row_index)
                            row = table_5.rows[row_index]

                            # Merge cells cho course
                            row.cells[1].merge(row.cells[3])
                            row.cells[0].text = f"1.{common_subject_counter}"
                            set_cell_alignment(row.cells[0])
                            row.cells[1].text = course_name

                            # Điền tổng giờ
                            row.cells[4].text = format_hours(course_data['total_hours'])
                            set_cell_alignment(row.cells[4])

                            # Điền giờ theo tháng nếu có
                            mission_month = None
                            for mission_data in course_data['missions'].values():
                                if mission_data['month'] and 1 <= mission_data['month'] <= 12:
                                    mission_month = mission_data['month']
                                    break

                            if mission_month:
                                col_idx = 4 + mission_month
                                if col_idx < len(row.cells):
                                    row.cells[col_idx].text = format_hours(course_data['total_hours'])
                                    set_cell_alignment(row.cells[col_idx])

                            row_index += 1

                            # ĐIỀN CÁC MISSION CỦA COURSE (a, b, c,...)
                            mission_counter = 0
                            mission_start_row = None

                            for mission_name, mission_data in course_data['missions'].items():
                                ensure_rows(table_5, row_index)

                                if mission_start_row is None:
                                    mission_start_row = row_index

                                mission_row = table_5.rows[row_index]

                                # Đánh số mission (a, b, c, ...)
                                mission_row.cells[0].text = chr(97 + mission_counter)
                                set_cell_alignment(mission_row.cells[0])
                                mission_row.cells[1].text = mission_name

                                # Chỉ điền thông tin phân loại cho mission đầu tiên
                                if mission_counter == 0:
                                    subject_obj = course_data['subject_obj']
                                    participant_text = subject_obj.participant_category_id.name or "" if subject_obj and subject_obj.participant_category_id else ""
                                    responsible_text = subject_obj.responsible_level_id.name or "" if subject_obj and subject_obj.responsible_level_id else ""

                                    mission_row.cells[2].text = participant_text
                                    mission_row.cells[3].text = responsible_text
                                    set_cell_alignment(mission_row.cells[2])
                                    set_cell_alignment(mission_row.cells[3])

                                # Điền giờ theo tháng cho mission
                                mission_month = mission_data['month']
                                if mission_month and 1 <= mission_month <= 12:
                                    col_idx = 4 + mission_month
                                    if col_idx < len(mission_row.cells):
                                        mission_row.cells[col_idx].text = format_hours(mission_data['total_hours'])
                                        set_cell_alignment(mission_row.cells[col_idx])

                                mission_counter += 1
                                row_index += 1

                            # Merge cột phân loại nếu có nhiều mission
                            if mission_counter > 1 and mission_start_row is not None:
                                mission_end_row = row_index - 1
                                table_5.rows[mission_start_row].cells[2].merge(table_5.rows[mission_end_row].cells[2])
                                table_5.rows[mission_start_row].cells[3].merge(table_5.rows[mission_end_row].cells[3])

                            common_subject_counter += 1

                    # PHẦN 2: HUẤN LUYỆN RIÊNG
                    if private_courses:
                        # Dòng "2. Huấn luyện riêng các đối tượng"
                        ensure_rows(table_5, row_index)
                        row = table_5.rows[row_index]
                        row.cells[1].merge(row.cells[3])
                        row.cells[0].text = "2"
                        set_cell_alignment(row.cells[0])
                        row.cells[1].text = "Huấn luyện riêng các đối tượng"
                        row_index += 1

                        # ĐIỀN CÁC COURSE CỦA HUẤN LUYỆN RIÊNG (2.1, 2.2,...)
                        private_subject_counter = 1
                        for course, course_data in private_courses.items():
                            course_name = course.name or "" if course else ""

                            ensure_rows(table_5, row_index)
                            row = table_5.rows[row_index]

                            # Merge cells cho course
                            row.cells[1].merge(row.cells[3])
                            row.cells[0].text = f"2.{private_subject_counter}"
                            set_cell_alignment(row.cells[0])
                            row.cells[1].text = course_name

                            # Điền tổng giờ
                            row.cells[4].text = format_hours(course_data['total_hours'])
                            set_cell_alignment(row.cells[4])

                            # Điền giờ theo tháng nếu có
                            mission_month = None
                            for mission_data in course_data['missions'].values():
                                if mission_data['month'] and 1 <= mission_data['month'] <= 12:
                                    mission_month = mission_data['month']
                                    break

                            if mission_month:
                                col_idx = 4 + mission_month
                                if col_idx < len(row.cells):
                                    row.cells[col_idx].text = format_hours(course_data['total_hours'])
                                    set_cell_alignment(row.cells[col_idx])

                            row_index += 1

                            # ĐIỀN CÁC MISSION CỦA COURSE (a, b, c,...)
                            mission_counter = 0
                            mission_start_row = None

                            for mission_name, mission_data in course_data['missions'].items():
                                ensure_rows(table_5, row_index)

                                if mission_start_row is None:
                                    mission_start_row = row_index

                                mission_row = table_5.rows[row_index]

                                # Đánh số mission (a, b, c, ...)
                                mission_row.cells[0].text = chr(97 + mission_counter)
                                set_cell_alignment(mission_row.cells[0])
                                mission_row.cells[1].text = mission_name

                                # Chỉ điền thông tin phân loại cho mission đầu tiên
                                if mission_counter == 0:
                                    subject_obj = course_data['subject_obj']
                                    participant_text = subject_obj.participant_category_id.name or "" if subject_obj and subject_obj.participant_category_id else ""
                                    responsible_text = subject_obj.responsible_level_id.name or "" if subject_obj and subject_obj.responsible_level_id else ""

                                    mission_row.cells[2].text = participant_text
                                    mission_row.cells[3].text = responsible_text
                                    set_cell_alignment(mission_row.cells[2])
                                    set_cell_alignment(mission_row.cells[3])

                                # Điền giờ theo tháng cho mission
                                mission_month = mission_data['month']
                                if mission_month and 1 <= mission_month <= 12:
                                    col_idx = 4 + mission_month
                                    if col_idx < len(mission_row.cells):
                                        mission_row.cells[col_idx].text = format_hours(mission_data['total_hours'])
                                        set_cell_alignment(mission_row.cells[col_idx])

                                mission_counter += 1
                                row_index += 1

                            # Merge cột phân loại nếu có nhiều mission
                            if mission_counter > 1 and mission_start_row is not None:
                                mission_end_row = row_index - 1
                                table_5.rows[mission_start_row].cells[2].merge(table_5.rows[mission_end_row].cells[2])
                                table_5.rows[mission_start_row].cells[3].merge(table_5.rows[mission_end_row].cells[3])

                            private_subject_counter += 1

                    plan_counter += 1



        file_data = BytesIO()
        doc.save(file_data)
        file_data.seek(0)
        data = base64.b64encode(file_data.read())

        if hasattr(self, 'week') and self.week:
            # Có tuần: Báo cáo huấn luyện tuần X tháng Y năm Z
            report_name = f'Bao_cao_huan_luyen_tuan_{self.week}_thang_{self.month}_nam_{self.year}.docx'
        elif hasattr(self, 'month') and self.month:
            # Có tháng: Báo cáo huấn luyện tháng X năm Y
            report_name = f'Bao_cao_huan_luyen_thang_{self.month}_nam_{self.year}.docx'
        else:
            # Chỉ có năm: Báo cáo huấn luyện năm X
            report_name = f'Bao_cao_huan_luyen_nam_{self.year}.docx'

        attachment = self.env['ir.attachment'].create({
            'name': report_name,
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
