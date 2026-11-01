import os
import re
import weasyprint

md_path = 'd:/RSUD_bangil/LJ/Workshop DevOps/devsecops/laporan/bab6/laporan/laporan.md'
pdf_path = 'd:/RSUD_bangil/LJ/Workshop DevOps/devsecops/laporan/bab6/laporan/laporan_baru.pdf'

with open(md_path, encoding='utf-8') as f:
    md_text = f.read()

print('MD size:', len(md_text))

html_content = md_text
html_content = re.sub(r'^# (.*)$', r'<h1 style="font-size:18pt;color:#111827;margin-top:20px;margin-bottom:10px;border-bottom:2px solid #3B82F6;padding-bottom:8px;">\1</h1>', html_content, flags=re.MULTILINE)
html_content = re.sub(r'^## (.*)$', r'<h2 style="font-size:15pt;color:#1F2937;margin-top:18px;margin-bottom:8px;border-bottom:1px solid #E5E7EB;padding-bottom:5px;">\1</h2>', html_content, flags=re.MULTILINE)
html_content = re.sub(r'^### (.*)$', r'<h3 style="font-size:12pt;color:#374151;margin-top:14px;margin-bottom:6px;">\1</h3>', html_content, flags=re.MULTILINE)
html_content = re.sub(r'^#### (.*)$', r'<h4 style="font-size:11pt;color:#4B5563;margin-top:10px;margin-bottom:4px;">\1</h4>', html_content, flags=re.MULTILINE)

html_content = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html_content)
html_content = re.sub(r'\*(.+?)\*', r'<em>\1</em>', html_content)

html_content = re.sub(r'```(\w+)?\n(.*?)\n```', r'<pre style="background:#1F2937;color:#F9FAFB;padding:10px 14px;border-radius:4px;font-family:Consolas,monospace;font-size:8.5pt;white-space:pre-wrap;word-break:break-word;"><code>\2</code></pre>', html_content, flags=re.DOTALL)
html_content = re.sub(r'`([^`]+)`', r'<code style="background:#F3F4F6;padding:2px 5px;border-radius:3px;font-family:Consolas,monospace;font-size:9pt;">\1</code>', html_content)

lines = html_content.split('\n')
in_table = False
table_lines = []
new_html = []
for line in lines:
    stripped = line.strip()
    if stripped.startswith('|') and stripped.endswith('|') and len(stripped) > 2:
        in_table = True
        table_lines = [line]
    elif in_table:
        if line.strip() == '':
            continue
        table_lines.append(line)
        if line.strip().endswith('|') or line.strip().endswith('</tr>'):
            new_html.append(''.join(table_lines))
            table_lines = []
            in_table = False
    else:
        new_html.append(line)

html_content = '\n'.join(new_html)
html_content = re.sub(r'^\|.*\|$', '', html_content, flags=re.MULTILINE)

print('HTML size:', len(html_content))

full_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<style>
  @page {{
    size: A4 portrait;
    margin: 13mm 14mm 13mm 14mm;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    font-family: 'Segoe UI', Calibri, Arial, sans-serif;
    font-size: 9pt;
    line-height: 1.5;
    color: #1e293b;
    margin: 0;
    padding: 0;
  }}
  .header {{
    text-align: center;
    padding: 25px 0 12px 0;
    border-bottom: 3px solid #3B82F6;
    margin-bottom: 20px;
  }}
  .header h1 {{
    font-size: 20pt;
    color: #0f172a;
    margin: 0 0 6px 0;
  }}
  .header .subtitle {{
    font-size: 9pt;
    color: #6B7280;
    margin-top: 4px;
  }}
  h2 {{
    font-size: 12pt;
    font-weight: 700;
    color: #0f172a;
    border-bottom: 1.5px solid #0f172a;
    padding-bottom: 3px;
    margin-top: 14px;
    margin-bottom: 6px;
    text-transform: uppercase;
    break-after: avoid;
  }}
  h3 {{
    font-size: 10.5pt;
    color: #1e293b;
    margin-top: 10px;
    margin-bottom: 4px;
    break-after: avoid;
  }}
  h4 {{
    font-size: 9.5pt;
    color: #334155;
    margin-top: 8px;
    margin-bottom: 3px;
    break-after: avoid;
  }}
  p {{
    margin: 0 0 5px 0;
    text-align: justify;
    font-size: 9pt;
  }}
  ul, ol {{
    margin: 0 0 5px 0;
    padding-left: 20px;
    font-size: 9pt;
  }}
  li {{
    margin-bottom: 3px;
    text-align: justify;
  }}
  table {{
    border-collapse: collapse;
    width: 100%;
    margin: 8px 0;
    font-size: 8pt;
  }}
  th, td {{
    border: 1px solid #D1D5DB;
    padding: 4px 6px;
    text-align: left;
    vertical-align: top;
  }}
  th {{
    background-color: #F3F4F6;
    font-weight: 700;
  }}
  tr:nth-child(even) td {{
    background-color: #F9FAFB;
  }}
  blockquote {{
    border-left: 3px solid #3B82F6;
    margin: 8px 0;
    padding: 6px 12px;
    background: #EFF6FF;
    color: #1E40AF;
    font-size: 9pt;
  }}
  .code-block {{
    background: #1F2937;
    color: #F9FAFB;
    padding: 10px 14px;
    border-radius: 4px;
    font-family: Consolas, monospace;
    font-size: 8pt;
    white-space: pre-wrap;
    word-break: break-word;
  }}
  .footer {{
    text-align: center;
    margin-top: 25px;
    padding-top: 10px;
    border-top: 1px solid #E5E7EB;
    font-size: 8pt;
    color: #9CA3AF;
  }}
</style>
</head>
<body>

{html_content}

<div class="footer">
  <p>&mdash; Akhir Laporan &mdash;</p>
  <p>Laporan ini dibuat untuk praktikum DevSecOps Workshop, PENS, Tahun Akademik 2026/2027</p>
</div>

</body>
</html>
"""

with open('laporan_baru.html', 'w', encoding='utf-8') as f:
    f.write(full_html)

print('Full HTML:', len(full_html))

try:
    weasyprint.HTML(string=full_html).write_pdf(pdf_path)
    size_kb = os.path.getsize(pdf_path) / 1024
    print('SUCCESS: PDF generated at', pdf_path, f'({size_kb:.2f} KB)')
except Exception as e:
    print('ERROR:', e)
    import traceback
    traceback.print_exc()
