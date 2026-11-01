import os
import sys
import re
from urllib.parse import unquote
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls
from PIL import Image

WORKSPACE_DIR = r"d:\RSUD_bangil\LJ\Workshop DevOps\devsecops"
bab = sys.argv[1] if len(sys.argv) > 1 else "bab2"
MD_PATH = os.path.join(WORKSPACE_DIR, "laporan", bab, "laporan", "laporan.md")
DOCX_PATH = os.path.join(WORKSPACE_DIR, "laporan", bab, "laporan", "laporan.docx")
ASSETS_DIR = os.path.join(WORKSPACE_DIR, "laporan", bab, "assets")

def set_cell_shading(cell, color_hex):
    shading = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{color_hex}"/>')
    cell._tc.get_or_add_tcPr().append(shading)

def set_cell_margins(cell, top=100, bottom=100, left=140, right=140):
    tcMar = parse_xml(f'<w:tcMar {nsdecls("w")}><w:top w:w="{top}" w:type="dxa"/><w:bottom w:w="{bottom}" w:type="dxa"/><w:left w:w="{left}" w:type="dxa"/><w:right w:w="{right}" w:type="dxa"/></w:tcMar>')
    cell._tc.get_or_add_tcPr().append(tcMar)

def add_formatted_runs(paragraph, text):
    pattern = r'(\*\*\*.*?\*\*\*|\*\*.*?\*\*|\*.*?\*|`.*?`|\[.*?\]\(.*?\))'
    tokens = re.split(pattern, text)
    for token in tokens:
        if not token:
            continue
        if token.startswith('***') and token.endswith('***') and len(token) >= 6:
            r = paragraph.add_run(token[3:-3])
            r.bold = True
            r.italic = True
        elif token.startswith('**') and token.endswith('**') and len(token) >= 4:
            r = paragraph.add_run(token[2:-2])
            r.bold = True
        elif token.startswith('*') and token.endswith('*') and len(token) >= 2:
            r = paragraph.add_run(token[1:-1])
            r.italic = True
        elif token.startswith('`') and token.endswith('`') and len(token) >= 2:
            r = paragraph.add_run(token[1:-1])
            r.font.name = "Consolas"
            r.font.size = Pt(9.5)
            r.font.color.rgb = RGBColor(0x0F, 0x17, 0x2A)
        elif token.startswith('[') and ']' in token and '(' in token and token.endswith(')'):
            m = re.match(r'\[(.*?)\]\((.*?)\)', token)
            if m:
                r = paragraph.add_run(m.group(1))
                r.font.color.rgb = RGBColor(0x25, 0x63, 0xEB)
                r.underline = True
            else:
                paragraph.add_run(token)
        else:
            paragraph.add_run(token)
def create_docx_from_md(md_path, docx_path, assets_dir):
    with open(md_path, "r", encoding="utf-8") as f:
        md_text = f.read()

    doc = docx.Document()

    for section in doc.sections:
        section.top_margin = Inches(0.65)
        section.bottom_margin = Inches(0.65)
        section.left_margin = Inches(0.7)
        section.right_margin = Inches(0.7)
        section.page_width = Inches(8.27)
        section.page_height = Inches(11.69)

    normal_style = doc.styles['Normal']
    normal_style.font.name = 'Calibri'
    normal_style.font.size = Pt(9.5)
    normal_style.font.color.rgb = RGBColor(0x1F, 0x29, 0x37)

    lines = md_text.splitlines()
    in_code_block = False
    code_lines = []
    in_table = False
    table_lines = []

    def flush_code_block():
        nonlocal in_code_block, code_lines
        if not code_lines:
            in_code_block = False
            return
        code_text = "\n".join(code_lines)
        
        tbl = doc.add_table(rows=1, cols=1)
        tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
        tbl.autofit = False
        cell = tbl.cell(0, 0)
        cell.width = Inches(6.87)
        
        set_cell_shading(cell, "F8FAFC")
        set_cell_margins(cell, top=60, bottom=60, left=100, right=100)
        
        borders = parse_xml(f'''
            <w:tcBorders {nsdecls("w")}>
                <w:top w:val="single" w:sz="4" w:space="0" w:color="CBD5E1"/>
                <w:bottom w:val="single" w:sz="4" w:space="0" w:color="CBD5E1"/>
                <w:left w:val="single" w:sz="18" w:space="0" w:color="2563EB"/>
                <w:right w:val="single" w:sz="4" w:space="0" w:color="CBD5E1"/>
            </w:tcBorders>
        ''')
        cell._tc.get_or_add_tcPr().append(borders)
        
        p = cell.paragraphs[0]
        p.paragraph_format.space_before = Pt(1)
        p.paragraph_format.space_after = Pt(1)
        p.paragraph_format.line_spacing = 1.0
        
        r = p.add_run(code_text)
        r.font.name = "Consolas"
        r.font.size = Pt(8)
        r.font.color.rgb = RGBColor(0x0F, 0x17, 0x2A)
        
        spacer = doc.add_paragraph()
        spacer.paragraph_format.space_before = Pt(0)
        spacer.paragraph_format.space_after = Pt(2)
        spacer.paragraph_format.line_spacing = 0.2
        
        code_lines = []
        in_code_block = False

    def flush_table():
        nonlocal in_table, table_lines
        if not table_lines:
            in_table = False
            return
        
        rows_data = []
        for tl in table_lines:
            if re.match(r'^\|[\s\-:|]+\|$', tl.strip()):
                continue
            cells = [c.strip() for c in tl.strip().strip('|').split('|')]
            rows_data.append(cells)
        
        if rows_data:
            num_cols = max(len(r) for r in rows_data)
            tbl = doc.add_table(rows=len(rows_data), cols=num_cols)
            tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
            tbl.autofit = True
            
            tblBorders = parse_xml(f'''
                <w:tblBorders {nsdecls("w")}>
                    <w:top w:val="single" w:sz="6" w:space="0" w:color="94A3B8"/>
                    <w:bottom w:val="single" w:sz="6" w:space="0" w:color="94A3B8"/>
                    <w:insideH w:val="single" w:sz="4" w:space="0" w:color="E2E8F0"/>
                    <w:insideV w:val="single" w:sz="4" w:space="0" w:color="E2E8F0"/>
                    <w:left w:val="none"/>
                    <w:right w:val="none"/>
                </w:tblBorders>
            ''')
            tbl._tbl.tblPr.append(tblBorders)

            for r_idx, row in enumerate(rows_data):
                is_header = (r_idx == 0)
                for c_idx in range(num_cols):
                    cell = tbl.cell(r_idx, c_idx)
                    cell_text = row[c_idx] if c_idx < len(row) else ""
                    set_cell_margins(cell, top=60, bottom=60, left=100, right=100)
                    if is_header:
                        set_cell_shading(cell, "1E3A8A")
                    elif r_idx % 2 == 1:
                        set_cell_shading(cell, "F8FAFC")
                    else:
                        set_cell_shading(cell, "FFFFFF")
                    
                    p = cell.paragraphs[0]
                    p.paragraph_format.space_before = Pt(1)
                    p.paragraph_format.space_after = Pt(1)
                    p.paragraph_format.line_spacing = 1.0
                    
                    if is_header:
                        r = p.add_run(cell_text)
                        r.bold = True
                        r.font.size = Pt(8.5)
                        r.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
                    else:
                        add_formatted_runs(p, cell_text)
                        for run in p.runs:
                            run.font.size = Pt(8)
            
            spacer = doc.add_paragraph()
            spacer.paragraph_format.space_before = Pt(0)
            spacer.paragraph_format.space_after = Pt(2)
            spacer.paragraph_format.line_spacing = 0.2
        
        table_lines = []
        in_table = False

    i = 0
    while i < len(lines):
        line = lines[i]

        if line.strip().startswith("```"):
            if in_code_block:
                flush_code_block()
            else:
                if in_table:
                    flush_table()
                in_code_block = True
                code_lines = []
            i += 1
            continue

        if in_code_block:
            code_lines.append(line)
            i += 1
            continue

        if line.strip().startswith("|") and line.strip().endswith("|"):
            if not in_table:
                in_table = True
                table_lines = []
            table_lines.append(line)
            i += 1
            continue
        elif in_table:
            flush_table()

        if not line.strip():
            i += 1
            continue

        if line.strip() in ["---", "***", "___"]:
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(6)
            p.paragraph_format.space_after = Pt(6)
            p_border = parse_xml(f'''
                <w:pBdr {nsdecls("w")}>
                    <w:bottom w:val="single" w:sz="6" w:space="1" w:color="E2E8F0"/>
                </w:pBdr>
            ''')
            p._p.get_or_add_pPr().append(p_border)
            i += 1
            continue

        if line.startswith("# "):
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(8)
            p.paragraph_format.space_after = Pt(2)
            p.paragraph_format.keep_with_next = True
            r = p.add_run(line[2:].strip())
            r.bold = True
            r.font.size = Pt(16)
            r.font.color.rgb = RGBColor(0x0F, 0x17, 0x2A)
            i += 1
            continue
        elif line.startswith("## "):
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(8)
            p.paragraph_format.space_after = Pt(2)
            p.paragraph_format.keep_with_next = True
            r = p.add_run(line[3:].strip())
            r.bold = True
            r.font.size = Pt(12)
            r.font.color.rgb = RGBColor(0x1E, 0x3A, 0x8A)
            i += 1
            continue
        elif line.startswith("### "):
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(6)
            p.paragraph_format.space_after = Pt(2)
            p.paragraph_format.keep_with_next = True
            r = p.add_run(line[4:].strip())
            r.bold = True
            r.font.size = Pt(10.5)
            r.font.color.rgb = RGBColor(0x25, 0x63, 0xEB)
            i += 1
            continue
        elif line.startswith("#### "):
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(4)
            p.paragraph_format.space_after = Pt(1)
            p.paragraph_format.keep_with_next = True
            r = p.add_run(line[5:].strip())
            r.bold = True
            r.font.size = Pt(9.5)
            r.font.color.rgb = RGBColor(0x37, 0x41, 0x51)
            i += 1
            continue

        img_match = re.match(r'^!\[(.*?)\]\((.*?)\)$', line.strip())
        if img_match:
            alt_text = img_match.group(1)
            raw_src = img_match.group(2)
            clean_filename = unquote(raw_src).replace("../assets/", "").replace("assets/", "")
            img_path = os.path.join(assets_dir, clean_filename)
            
            if os.path.exists(img_path):
                img_p = doc.add_paragraph()
                img_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                img_p.paragraph_format.space_before = Pt(3)
                img_p.paragraph_format.space_after = Pt(1)
                run = img_p.add_run()
                try:
                    with Image.open(img_path) as im:
                        w_px, h_px = im.size
                        aspect = w_px / h_px
                    max_w = 5.2
                    max_h = 1.6
                    if (max_w / aspect) > max_h:
                        run.add_picture(img_path, height=Inches(max_h))
                    else:
                        run.add_picture(img_path, width=Inches(max_w))
                except Exception:
                    run.add_picture(img_path, width=Inches(5.0))
            else:
                p = doc.add_paragraph(f"[Image Missing: {clean_filename}]")
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            i += 1
            continue

        if line.strip().startswith("*Gambar") and line.strip().endswith("*"):
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.space_before = Pt(1)
            p.paragraph_format.space_after = Pt(4)
            p.paragraph_format.line_spacing = 1.0
            r = p.add_run(line.strip()[1:-1])
            r.italic = True
            r.font.size = Pt(8.5)
            r.font.color.rgb = RGBColor(0x64, 0x74, 0x8B)
            i += 1
            continue

        if line.startswith("> "):
            p = doc.add_paragraph()
            p.paragraph_format.left_indent = Inches(0.3)
            p.paragraph_format.space_before = Pt(3)
            p.paragraph_format.space_after = Pt(3)
            p_border = parse_xml(f'''
                <w:pBdr {nsdecls("w")}>
                    <w:left w:val="single" w:sz="16" w:space="8" w:color="3B82F6"/>
                </w:pBdr>
            ''')
            p._p.get_or_add_pPr().append(p_border)
            add_formatted_runs(p, line[2:].strip())
            for run in p.runs:
                run.italic = True
                run.font.color.rgb = RGBColor(0x47, 0x55, 0x69)
            i += 1
            continue

        if line.strip().startswith("- ") or line.strip().startswith("* "):
            p = doc.add_paragraph(style='List Bullet')
            p.paragraph_format.space_before = Pt(1)
            p.paragraph_format.space_after = Pt(1.5)
            p.paragraph_format.line_spacing = 1.08
            content = line.strip()[2:].strip()
            add_formatted_runs(p, content)
            i += 1
            continue

        num_match = re.match(r'^(\d+)\.\s+(.*)$', line.strip())
        if num_match:
            p = doc.add_paragraph(style='List Number')
            p.paragraph_format.space_before = Pt(1)
            p.paragraph_format.space_after = Pt(1.5)
            p.paragraph_format.line_spacing = 1.08
            content = num_match.group(2)
            add_formatted_runs(p, content)
            i += 1
            continue

        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(1)
        p.paragraph_format.space_after = Pt(2.5)
        p.paragraph_format.line_spacing = 1.1
        add_formatted_runs(p, line.strip())
        i += 1

    if in_code_block:
        flush_code_block()
    if in_table:
        flush_table()

    doc.save(docx_path)
    print(f"SUCCESS: DOCX generated at: {docx_path}")

if __name__ == "__main__":
    create_docx_from_md(MD_PATH, DOCX_PATH, ASSETS_DIR)

