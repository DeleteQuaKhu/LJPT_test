# -*- coding: utf-8 -*-
"""Sinh N2/furi-dict.js (bảng đọc furigana) + copy furi-engine.js cho app.

    python emit_js.py <thư mục N2 của app>

Nguồn: dict.json (do build_dict.py sinh ra). Không sửa tay furi-dict.js.
"""
import json, os, shutil, sys

out_dir = sys.argv[1] if len(sys.argv) > 1 else '.'
src_dir = os.path.dirname(os.path.abspath(__file__))
d = json.load(open(os.path.join(src_dir, 'dict.json'), encoding='utf-8'))
N_EXPL = len([l for l in open(os.path.join(src_dir, 'expected.jsonl'), encoding='utf-8') if l.strip()])

HEAD = '''/* ===== FURIGANA DATA — bảng đọc cho phần Giải thích (JLPT N2) =====
   key   = chuỗi viết (kanji, có thể kèm kana/ngữ cảnh phía sau hoặc trước)
   value = cách đọc hiragana của toàn bộ chuỗi đó
   Khớp theo "chuỗi dài nhất trước" tại mỗi vị trí (xem furi-engine.js).
   Sinh tự động từ %d phần giải thích trong data_*.js — KHÔNG sửa tay. */
var FURI={
'''
lines = []
for i, (k, v) in enumerate(sorted(d.items())):
    lines.append('"%s":"%s"%s\n' % (k, v, ',' if i + 1 < len(d) else ''))
body = ''.join(lines)

with open(os.path.join(out_dir, 'furi-dict.js'), 'w', encoding='utf-8', newline='\n') as f:
    f.write(HEAD % N_EXPL + body + '};\n')

shutil.copyfile(os.path.join(src_dir, 'furi-engine.js'), os.path.join(out_dir, 'furi-engine.js'))
print('wrote %s (entries %d)' % (os.path.join(out_dir, 'furi-dict.js'), len(d)))
print('copied %s' % os.path.join(out_dir, 'furi-engine.js'))
