import os
import sys
import re
import base64
import subprocess
from urllib.parse import unquote

WORKSPACE_DIR = r"d:\RSUD_bangil\LJ\Workshop DevOps\devsecops"
bab = sys.argv[1] if len(sys.argv) > 1 else "bab2"
MD_PATH = os.path.join(WORKSPACE_DIR, "laporan", bab, "laporan", "laporan.md")
HTML_PATH = os.path.join(WORKSPACE_DIR, "laporan", bab, "laporan", "laporan.html")
PDF_PATH = os.path.join(WORKSPACE_DIR, "laporan", bab, "laporan", "laporan.pdf")
ASSETS_DIR = os.path.join(WORKSPACE_DIR, "laporan", bab, "assets")
EDGE_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"

def get_base64_image(rel_path):
    clean_path = unquote(rel_path).replace("../assets/", "").replace("assets/", "")
    full_path = os.path.join(ASSETS_DIR, clean_path)
    if os.path.exists(full_path):
        with open(full_path, "rb") as f:
            data = base64.b64encode(f.read()).decode("utf-8")
        return f"data:image/png;base64,{data}"
    return rel_path

def md_to_html(md_text):
    lines = md_text.splitlines()
    html_lines = []
    in_code = False
    code_buffer = []
    in_table = False
    table_buffer = []
    in_list = False
    list_type = ""

    def flush_list():
        nonlocal in_list, list_type
        if in_list:
            html_lines.append(f"</{list_type}>")
            in_list = False
            list_type = ""

    def flush_table():
        nonlocal in_table, table_buffer
        if in_table and table_buffer:
            html_lines.append('<table class="data-table">')
            for i, row in enumerate(table_buffer):
                cells = [c.strip() for c in row.strip("|").split("|")]
                if i == 0:
                    html_lines.append("<thead><tr>" + "".join(f"<th>{inline_format(c)}</th>" for c in cells) + "</tr></thead><tbody>")
                elif i == 1 and all(set(c).issubset({"-", ":", " "}) for c in cells):
                    continue
                else:
                    html_lines.append("<tr>" + "".join(f"<td>{inline_format(c)}</td>" for c in cells) + "</tr>")
            html_lines.append("</tbody></table>")
            in_table = False
            table_buffer = []

    def inline_format(text):
        text = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', text)
        text = re.sub(r'\*(.*?)\*', r'<em>\1</em>', text)
        text = re.sub(r'`(.*?)`', r'<code>\1</code>', text)
        text = re.sub(r'\[(.*?)\]\((.*?)\)', r'<a href="\2">\1</a>', text)
        text = text.replace("<strong>Terpenuhi</strong>", '<span class="badge-pass">Terpenuhi</span>')
        text = text.replace("<strong>Gagal/terblokir</strong>", '<span class="badge-fail">Gagal</span>')
        return text

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("```"):
            if not in_code:
                flush_list()
                flush_table()
                in_code = True
                code_buffer = []
            else:
                in_code = False
                raw_code = "\n".join(code_buffer)
                raw_code = raw_code.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                html_lines.append(f'<div class="terminal-box"><pre><code>{raw_code}</code></pre></div>')
                code_buffer = []
            continue

        if in_code:
            code_buffer.append(line)
            continue

        if stripped.startswith("|") and stripped.endswith("|"):
            flush_list()
            in_table = True
            table_buffer.append(stripped)
            continue
        else:
            flush_table()

        if not stripped:
            flush_list()
            continue

        if stripped in ("---", "***", "___"):
            flush_list()
            continue

        if stripped.startswith("# "):
            flush_list()
            title = inline_format(stripped[2:])
            html_lines.append(f'<div class="doc-title"><h1>{title}</h1>')
            continue
        elif stripped.startswith("## "):
            flush_list()
            title = inline_format(stripped[3:])
            if "Fondasi Teoretis" in title:
                html_lines.append(f'<h2>{title}</h2></div>')
            else:
                html_lines.append(f'<h2 class="section-title">{title}</h2>')
            continue
        elif stripped.startswith("### "):
            flush_list()
            title = inline_format(stripped[4:])
            html_lines.append(f'<h3 class="subsection-title">{title}</h3>')
            continue
        elif stripped.startswith("#### "):
            flush_list()
            title = inline_format(stripped[5:])
            html_lines.append(f'<h4 class="subsubsection-title">{title}</h4>')
            continue

        img_match = re.match(r'!\[(.*?)\]\((.*?)\)', stripped)
        if img_match:
            flush_list()
            alt_text, img_src = img_match.groups()
            b64_src = get_base64_image(img_src)
            html_lines.append(f'<div class="figure-box"><img src="{b64_src}" alt="{alt_text}"></div>')
            continue

        if stripped.startswith("*Gambar ") and stripped.endswith("*"):
            flush_list()
            caption = inline_format(stripped[1:-1])
            html_lines.append(f'<div class="figure-caption">{caption}</div>')
            continue

        if stripped.startswith("- ") or stripped.startswith("* "):
            if not in_list or list_type != "ul":
                flush_list()
                in_list = True
                list_type = "ul"
                html_lines.append("<ul>")
            item_text = inline_format(stripped[2:])
            html_lines.append(f"<li>{item_text}</li>")
            continue
        
        ol_match = re.match(r'^(\d+)\.\s+(.*)', stripped)
        if ol_match:
            if not in_list or list_type != "ol":
                flush_list()
                in_list = True
                list_type = "ol"
                html_lines.append("<ol>")
            item_text = inline_format(ol_match.group(2))
            html_lines.append(f"<li>{item_text}</li>")
            continue

        flush_list()

        if stripped.startswith("**Nama**:") or stripped.startswith("**NIM**:") or stripped.startswith("**Kelas**:") or stripped.startswith("**Tanggal pelaksanaan**:"):
            html_lines.append(f'<p class="identity-line">{inline_format(stripped)}</p>')
            continue

        html_lines.append(f"<p>{inline_format(stripped)}</p>")

    flush_list()
    flush_table()
    return "\n".join(html_lines)

with open(MD_PATH, "r", encoding="utf-8") as f:
    md_content = f.read()

body_html = md_to_html(md_content)

full_html = f"""<!DOCTYPE html>
<html lang="id">
<head>
<meta charset="UTF-8">
<title>Laporan Praktikum Bab 1 - DevSecOps</title>
<style>
  @page {{
    size: A4 portrait;
    margin: 13mm 14mm 13mm 14mm;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    font-family: 'Segoe UI', Calibri, Arial, sans-serif;
    font-size: 8.8pt;
    line-height: 1.4;
    color: #1e293b;
    margin: 0;
    padding: 0;
  }}
  .inst-header {{
    border-bottom: 2px solid #0f172a;
    padding-bottom: 4px;
    margin-bottom: 8px;
    display: flex;
    justify-content: space-between;
    align-items: flex-end;
  }}
  .inst-header .title-left {{
    font-size: 8.5pt;
    font-weight: 700;
    color: #334155;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    line-height: 1.3;
  }}
  .inst-header .meta-right {{
    font-size: 8pt;
    color: #64748b;
    text-align: right;
  }}
  .doc-title {{ text-align: center; margin-bottom: 8px; }}
  .doc-title h1 {{
    font-size: 12.5pt;
    font-weight: 800;
    color: #0f172a;
    margin: 0 0 3px 0;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }}
  .doc-title h2 {{
    font-size: 10pt;
    font-weight: 600;
    color: #334155;
    margin: 0;
  }}
  .identity-line {{
    font-size: 8.5pt;
    margin: 2px 0;
  }}
  h2.section-title {{
    font-size: 10.5pt;
    font-weight: 700;
    color: #0f172a;
    border-bottom: 1.5px solid #0f172a;
    padding-bottom: 2px;
    margin-top: 10px;
    margin-bottom: 5px;
    text-transform: uppercase;
    break-after: avoid;
    page-break-after: avoid;
  }}
  h3.subsection-title {{
    font-size: 9.5pt;
    font-weight: 700;
    color: #1e293b;
    margin-top: 8px;
    margin-bottom: 3px;
    break-after: avoid;
    page-break-after: avoid;
  }}
  h4.subsubsection-title {{
    font-size: 9pt;
    font-weight: 700;
    color: #334155;
    margin-top: 6px;
    margin-bottom: 2px;
    break-after: avoid;
    page-break-after: avoid;
  }}
  p {{ margin: 0 0 4px 0; text-align: justify; }}
  ul, ol {{ margin: 0 0 5px 0; padding-left: 18px; }}
  li {{ margin-bottom: 2px; text-align: justify; }}
  table.data-table {{
    width: 100%;
    border-collapse: collapse;
    margin: 5px 0 7px 0;
    font-size: 8pt;
    break-inside: avoid;
    page-break-inside: avoid;
  }}
  table.data-table th, table.data-table td {{
    border: 1px solid #cbd5e1;
    padding: 4px 6px;
    text-align: left;
    vertical-align: middle;
  }}
  table.data-table th {{
    background-color: #f1f5f9;
    font-weight: 700;
    color: #0f172a;
  }}
  table.data-table tr:nth-child(even) td {{ background-color: #f8fafc; }}
  .badge-pass {{
    display: inline-block;
    background-color: #dcfce7;
    color: #166534;
    font-weight: 700;
    font-size: 7.5pt;
    padding: 1px 6px;
    border-radius: 3px;
    border: 1px solid #bbf7d0;
  }}
  .badge-fail {{
    display: inline-block;
    background-color: #fee2e2;
    color: #991b1b;
    font-weight: 700;
    font-size: 7.5pt;
    padding: 1px 6px;
    border-radius: 3px;
    border: 1px solid #fecaca;
  }}
  .terminal-box {{
    background-color: #090d16;
    color: #f1f5f9;
    font-family: 'Consolas', 'Courier New', monospace;
    font-size: 7.5pt;
    line-height: 1.35;
    padding: 5px 8px;
    border-radius: 4px;
    margin: 3px 0 5px 0;
    border: 1px solid #1e293b;
    white-space: pre-wrap;
    word-break: break-word;
    break-inside: avoid;
    page-break-inside: avoid;
  }}
  .terminal-box pre {{ margin: 0; padding: 0; }}
  .terminal-box code {{ font-family: inherit; }}
  .figure-box {{
    margin: 5px 0 2px 0;
    text-align: center;
    break-inside: avoid;
    page-break-inside: avoid;
  }}
  .figure-box img {{
    max-width: 95%;
    max-height: 155px;
    object-fit: contain;
    border: 1px solid #cbd5e1;
    border-radius: 3px;
    display: block;
    margin: 0 auto;
  }}
  .figure-caption {{
    font-size: 7.5pt;
    color: #475569;
    font-style: italic;
    margin-top: 2px;
    margin-bottom: 5px;
    text-align: center;
    break-after: avoid;
  }}
</style>
</head>
<body>
  <div class="inst-header">
    <div class="title-left">
      Workshop DevOps & DevSecOps<br>
      Departemen Teknik Informatika dan Komputer
    </div>
    <div class="meta-right">
      Modul Laboratorium Praktikum<br>
      Tahun Akademik 2026/2027
    </div>
  </div>

  {body_html}
</body>
</html>
"""

with open(HTML_PATH, "w", encoding="utf-8") as f:
    f.write(full_html)

print(f"HTML generated at: {HTML_PATH}")

cmd = [
    EDGE_PATH,
    "--headless=new",
    "--disable-gpu",
    "--no-pdf-header-footer",
    f"--print-to-pdf={PDF_PATH}",
    f"file:///{HTML_PATH.replace(os.sep, '/')}"
]

print("Executing Edge print-to-pdf...")
res = subprocess.run(cmd, capture_output=True, text=True)
if os.path.exists(PDF_PATH):
    size_kb = os.path.getsize(PDF_PATH) / 1024
    print(f"SUCCESS: PDF generated at: {PDF_PATH} ({size_kb:.2f} KB)")
else:
    print(f"ERROR: PDF generation failed. Return code: {res.returncode}")
    print(res.stderr)


