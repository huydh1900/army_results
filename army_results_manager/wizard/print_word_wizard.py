# -*- coding: utf-8 -*-
from odoo import models, fields
from odoo.modules.module import get_module_resource
from io import BytesIO
import base64
from docx.shared import Pt
from docx import Document
from docx.shared import Cm
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_ALIGN_VERTICAL
from docx.shared import Inches


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
        """Main function to replace placeholder with table 4, chỉ lấy records có type='squad'."""
        # 🔸 Lọc record theo type
        filtered_records = [r for r in records if r.type == 'officer']

        # Nếu không có record phù hợp thì không tạo bảng
        if not filtered_records:
            return

        for para in doc.paragraphs:
            if placeholder not in para.text:
                continue

            # Xóa placeholder
            parent = para._element.getparent()
            idx = parent.index(para._element)
            parent.remove(para._element)

            # Tạo cấu trúc bảng
            table = self._create_table_4_structure(doc)
            
            # Điền dữ liệu bảng
            self._fill_table_4_data(table, filtered_records)
            
            # Thêm dòng tổng kết
            # self._add_table_4_summary(table, filtered_records)

            # Chèn bảng vào đúng vị trí placeholder
            parent.insert(idx, table._element)
            break



    def _create_table_4_structure(self, doc):
        """Create table 4 structure with headers."""
        # Create table with 3 header rows
        table = doc.add_table(rows=3, cols=18)
        table.style = "Table Grid"

        # Build headers
        self._build_table_4_headers(table)
        
        # Set column widths
        self._set_table_4_column_widths(table)
        
        # Format header cells
        self._format_table_4_headers(table)
        
        return table


    def _build_table_4_headers(self, table):
        """Build header structure for table 4."""
        # --- ROW 0: Main headers ---
        hdr = table.rows[0].cells
        hdr[0].text = "TT"
        hdr[1].text = "Nội dung huấn luyện"
        hdr[2].text = "Thành phần tham gia"
        hdr[3].text = "Cấp phụ trách"
        hdr[4].text = "Thời gian (giờ)"
        hdr[17].text = "Biện pháp tiến hành"

        # Merge "Thời gian (giờ)" horizontally (col 4 → 16)
        hdr[4].merge(hdr[16])

        # --- ROW 1: Sub headers ---
        sub = table.rows[1].cells
        sub[4].text = "Tổng số"
        for i in range(12):
            sub[5 + i].text = f"Tháng {i + 1:02d}"

        # --- ROW 2: Numbers row ---
        nums = table.rows[2].cells
        # month_numbers = ["07", "77", "48", "48", "48", "48", "62", "48", "84", "21", "", ""]

        # # Fill month numbers first
        # for i, num in enumerate(month_numbers):
        #     nums[5 + i].text = num

        # Calculate total from cells 5-16
        total = sum(int(nums[5 + i].text) for i in range(12) if nums[5 + i].text.strip())
        nums[4].text = str(total)

        # Merge vertically for fixed columns
        for col in [0, 1, 2, 3, 17]:
            table.cell(0, col).merge(table.cell(2, col))


    def _set_table_4_column_widths(self, table):
        """Set column widths for table 4."""
        col_widths = [
            0.5,   # TT
            3.8,   # Nội dung huấn luyện
            1.0,   # Thành phần tham gia
            1.0,   # Cấp phụ trách
            0.5,   # Tổng số
            *[0.5] * 12,  # Tháng 01–12
            2.8    # Biện pháp tiến hành
        ]
        
        for i, width in enumerate(col_widths):
            for row in table.rows:
                row.cells[i].width = Inches(width)


    def _format_table_4_headers(self, table):
        """Format header cells for table 4."""
        for row in table.rows[:3]:  # Only first 3 rows (headers)
            for cell in row.cells:
                cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
                for p in cell.paragraphs:
                    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    run = p.runs[0] if p.runs else p.add_run()
                    run.font.name = "Times New Roman"
                    run.font.size = Pt(14)
                    run.bold = True


    def _fill_table_4_data(self, table, records):
        """Fill data rows for table 4."""
        sequence_counter = 1  # Khởi tạo bộ đếm thứ tự
        
        for record in records:
            courses = record.course_ids if hasattr(record, 'course_ids') and record.course_ids else []
            
            for course in courses:
                missions = course.mission_ids if hasattr(course, 'mission_ids') and course.mission_ids else []
                
                for mission in missions:
                    self._add_table_4_mission_row(table, mission, course, sequence_counter)
                    sequence_counter += 1  # Tăng số thứ tự sau mỗi row


    def _add_table_4_mission_row(self, table, mission, course, sequence_number):
        """Add a single mission row to table 4."""
        row = table.add_row()
        cells = row.cells
        
        # Column 0: TT (Auto sequence number)
        cells[0].text = str(sequence_number)
        
        # Columns 1-3: Merge và lấy tên từ training.course
        course_name = getattr(course, 'name', '') or ''
        
        # Gộp cells 1, 2, 3
        cells[1].merge(cells[2])
        cells[1].merge(cells[3])
        cells[1].text = course_name
        cells[1].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.LEFT
        
        # Columns 5-16: Monthly distribution
        self._fill_monthly_hours(cells, mission)
        
        # Column 4: Tổng số giờ (tổng từ cells 5-16)
        total_hours = sum([
            self._get_cell_numeric_value(cells[i]) 
            for i in range(5, 17)
        ])
        cells[4].text = str(int(total_hours)) if total_hours else ''
        
        # Column 17: Để trống
        cells[17].text = ''
        
        # Format the row
        self._format_table_4_data_row(cells)


    def _get_cell_numeric_value(self, cell):
        """Helper method to get numeric value from cell text."""
        try:
            text = cell.text.strip()
            return float(text) if text else 0
        except (ValueError, AttributeError):
            return 0


    def _fill_monthly_hours(self, cells, mission):
        """Fill monthly hours distribution (columns 5-16)."""
        monthly_hours = getattr(mission, 'monthly_distribution', [])
        
        # Ensure we have 12 values
        if not monthly_hours:
            monthly_hours = [''] * 12
        elif len(monthly_hours) < 12:
            monthly_hours = list(monthly_hours) + [''] * (12 - len(monthly_hours))
        
        for i in range(12):
            value = monthly_hours[i] if i < len(monthly_hours) else ''
            cells[5 + i].text = str(int(value)) if value else ''


    def _format_table_4_data_row(self, cells):
        """Format a data row in table 4."""
        for cell in cells:
            cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
            
            # Default center alignment except for columns 1 and 17 (already set above)
            for p in cell.paragraphs:
                if p.alignment != WD_ALIGN_PARAGRAPH.LEFT:
                    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                
                for run in p.runs:
                    run.font.name = "Times New Roman"
                    run.font.size = Pt(13)


    def _add_table_4_summary(self, table, records):
        """Add summary row at the bottom of table 4."""
        summary_row = table.add_row()
        cells = summary_row.cells
        
        # Column 1: Label
        cells[1].text = "TỔNG SỐ"
        cells[1].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
        
        # Calculate totals
        totals = self._calculate_table_4_totals(records)
        
        # Column 4: Total hours
        cells[4].text = str(int(totals['total'])) if totals['total'] else ''
        
        # Columns 5-16: Monthly totals
        for i in range(12):
            month_total = totals['monthly'][i]
            cells[5 + i].text = str(int(month_total)) if month_total else ''
        
        # Format summary row
        for cell in cells:
            cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
            for p in cell.paragraphs:
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                for run in p.runs:
                    run.font.name = "Times New Roman"
                    run.font.size = Pt(13)
                    run.bold = True


    def _calculate_table_4_totals(self, records):
        """Calculate totals for all missions."""
        total_hours = 0
        monthly_totals = [0] * 12
        
        for record in records:
            courses = record.course_ids if hasattr(record, 'course_ids') and record.course_ids else []
            
            for course in courses:
                missions = course.mission_ids if hasattr(course, 'mission_ids') and course.mission_ids else []
                
                for mission in missions:
                    # Add to total
                    hours = getattr(mission, 'total_hours', 0) or 0
                    total_hours += hours
                    
                    # Add to monthly totals
                    monthly_hours = getattr(mission, 'monthly_distribution', [])
                    for i in range(min(12, len(monthly_hours))):
                        if monthly_hours[i]:
                            monthly_totals[i] += monthly_hours[i]
        
        return {
            'total': total_hours,
            'monthly': monthly_totals
        }

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
        self.replace_table_4(doc, "{{table_4}}", records)


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