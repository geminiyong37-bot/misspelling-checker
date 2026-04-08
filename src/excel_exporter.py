import openpyxl
from openpyxl.styles import PatternFill, Font, Alignment
import os

FILE_COLORS = [
    "DBEAFE", "FEF3C7", "D1FAE5", "FCE7F3", "E0E7FF",
    "FED7AA", "E5E7EB", "DDD6FE", "CFFAFE", "FECACA"
]

ORANGE_FILL = PatternFill(start_color="FFE699", end_color="FFE699", fill_type="solid")
HEADER_FILL = PatternFill(start_color="374151", end_color="374151", fill_type="solid")

def build_rows_from_doc(doc):
    sentences = doc.get("sentences", [])
    source = doc.get("file") or doc.get("source") or "알 수 없는 문서"
    
    rows = []
    for idx, sentence in enumerate(sentences):
        rows.append({
            "file": source,
            "page": sentence.get("pageNumber", 1),
            "original": sentence.get("text", ""),
            "corrected": "",
            "help": sentence.get("meta") or "본문",
            "index": idx + 1
        })
    return rows

def create_workbook(rows):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "오타검토결과"

    headers = ["문서명", "수정전", "수정후", "비고"]
    ws.append(headers)

    # 너비 설정
    widths = [30, 40, 40, 50]
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[openpyxl.utils.get_column_letter(i)].width = w

    # 헤더 스타일
    header_font = Font(bold=True, color="FFFFFF")
    header_alignment = Alignment(horizontal="center")
    
    for cell in ws[1]:
        cell.font = header_font
        cell.fill = HEADER_FILL
        cell.alignment = header_alignment

    # 중복 제거 및 데이터 그룹화
    unique_errors = {}
    for row in rows:
        key = (row["original"], row["corrected"])
        if key not in unique_errors:
            unique_errors[key] = {
                "file": row["file"],
                "original": row["original"],
                "corrected": row["corrected"],
                "help": row.get("help") or row.get("reason", ""),
                "count": 0,
                "pages": set()
            }
        unique_errors[key]["count"] += 1
        unique_errors[key]["pages"].add(str(row.get("page", 1)))

    file_color_map = {}
    color_idx = 0

    for key, data in unique_errors.items():
        original = data["original"]
        corrected = data["corrected"]
        note = data["help"]
        count = data["count"]
        display_name = os.path.basename(data["file"])
        if display_name not in file_color_map:
            file_color_map[display_name] = FILE_COLORS[color_idx % len(FILE_COLORS)]
            color_idx += 1
        
        file_bg_color = file_color_map[display_name]
        
        note_text = f"[중복 {count}회] {note}" if count > 1 else note

        ws.append([display_name, original, corrected, note_text])
        current_row = ws.max_row
        
        # 강조 스타일
        norm_orig = (original or "").strip().replace(" ", "")
        norm_corr = (corrected or "").strip().replace(" ", "")
        
        if norm_corr and norm_orig != norm_corr:
            file_fill = PatternFill(start_color=file_bg_color, end_color=file_bg_color, fill_type="solid")
            ws.cell(row=current_row, column=2).fill = file_fill
            ws.cell(row=current_row, column=3).fill = file_fill

    return wb

def export_to_excel(rows, output_path):
    wb = create_workbook(rows)
    wb.save(output_path)
