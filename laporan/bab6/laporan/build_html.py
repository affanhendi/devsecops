import re

with open('laporan.md', encoding='utf-8') as f:
    content = f.read()

content = re.sub(r'^# (.*)$', r'<h1 style="font-size:18pt;color:#111827;margin-top:20px;margin-bottom:10px;border-bottom:2px solid #3B82F6;padding-bottom:8px;">\1</h1>', content, flags=re.MULTILINE)
content = re.sub(r'^## (.*)$', r'<h2 style="font-size:14pt;color:#1F2937;margin-top:15px;margin-bottom:6px;border-bottom:1px solid #E5E7EB;padding-bottom:4px;">\1</h2>', content, flags=re.MULTILINE)
content = re.sub(r'^### (.*)$', r'<h3 style="font-size:11pt;color:#374151;margin-top:10px;margin-bottom:4px;">\1</h3>', content, flags=re.MULTILINE)
content = re.sub(r'^#### (.*)$', r'<h4 style="font-size:10pt;color:#4B5563;margin-top:8px;margin-bottom:3px;">\1</h4>', content, flags=re.MULTILINE)

content = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', content)
content = re.sub(r'\*(.+?)\*', r'<em>\1</em>', content)

content = re.sub(r'```(\w+)?\n(.*?)\n```', r'<pre style="background:#1F2937;color:#FFFFFF;padding:8px 12px;border-radius:3px;font-family:Consolas,monospace;font-size:7.5pt;white-space:pre-wrap;word-break:break-word;"><code>\2</code></pre>', content, flags=re.DOTALL)
content = re.sub(r'`([^`]+)`', r'<code style="background:#F3F4F6;padding:1px 4px;border-radius:2px;font-family:Consolas,monospace;font-size:8pt;">\1</code>', content)

lines = content.split('\n')
in_table = False
table_lines = []
result = []
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
            row = ''
            for l in table_lines:
                row += l.strip() + ' '
            result.append('<tr>' + row + '</tr>')
            table_lines = []
            in_table = False
    else:
        result.append(line)

final = '\n'.join(result)
final = re.sub(r'^\|.*\|$', '', final, flags=re.MULTILINE)

with open('laporan_render.html', 'w', encoding='utf-8') as f:
    f.write(final)
print('HTML saved, size:', len(final))
