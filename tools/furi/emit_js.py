# -*- coding: utf-8 -*-
"""Sinh N2/furi-dict.js (bảng đọc furigana) + copy furi-engine.js cho app.

    python emit_js.py <thư mục N2 của app>

Nguồn: dict.json + expected.jsonl (do build_dict.py sinh ra). Không sửa tay furi-dict.js.
"""
import json, os, shutil, sys

out_dir = sys.argv[1] if len(sys.argv) > 1 else '.'
src_dir = os.path.dirname(os.path.abspath(__file__))
d = json.load(open(os.path.join(src_dir, 'dict.json'), encoding='utf-8'))
N_TEXTS = len([l for l in open(os.path.join(src_dir, 'expected.jsonl'), encoding='utf-8') if l.strip()])
_fix_path = os.path.join(src_dir, 'fix_text.json')
FIXTEXT = json.load(open(_fix_path, encoding='utf-8')) if os.path.exists(_fix_path) else {}

HEAD = '''/* ===== FURIGANA DATA — bảng đọc cho mọi đoạn tiếng Nhật của JLPT N2 =====
   (問題文 / 質問 / 選択肢 / 訳 / 解説 — xem tools/furi/corpus-fields.mjs)
   key   = chuỗi viết (kanji, có thể kèm kana/ngữ cảnh phía sau hoặc trước)
   value = cách đọc hiragana của toàn bộ chuỗi đó
   Khớp theo "chuỗi dài nhất trước" tại mỗi vị trí (xem furi-engine.js).
   Sinh tự động từ %d đoạn text trong data_*.js — KHÔNG sửa tay. */
var FURI={
'''
lines = []
for i, (k, v) in enumerate(sorted(d.items())):
    lines.append('"%s":"%s"%s\n' % (k, v, ',' if i + 1 < len(d) else ''))
body = ''.join(lines)

with open(os.path.join(out_dir, 'furi-dict.js'), 'w', encoding='utf-8', newline='\n') as f:
    f.write(HEAD % N_TEXTS + body + '};\n')

FIXHEAD = '''/* ===== FURIGANA EXCEPTIONS \u2014 ngo\u1ea1i l\u1ec7 theo \u0111\u00fang \u0111o\u1ea1n text (JLPT N2) =====
   key   = \u0111o\u1ea1n text \u0111\u1ea7y \u0111\u1ee7 nh\u01b0 trong data_*.js
   value = { v\u1ecb tr\u00ed: [m\u1eb7t ch\u1eef, c\u00e1ch \u0111\u1ecdc] } \u2014 d\u00f9ng thay b\u1ea3ng \u0111\u1ecdc t\u1ea1i \u0111\u00fang c\u00e1c v\u1ecb tr\u00ed n\u00e0y
   (v\u1ecb tr\u00ed n\u00e0o kh\u00f4ng c\u00f3 th\u00ec v\u1eabn d\u00f9ng b\u1ea3ng \u0111\u1ecdc b\u00ecnh th\u01b0\u1eddng).
   Ch\u1ec9 c\u1ea7n cho %d \u0111o\u1ea1n m\u00e0 b\u1ea3ng \u0111\u1ecdc kh\u00f4ng ph\u00e2n bi\u1ec7t \u0111\u01b0\u1ee3c (c\u00f9ng ng\u1eef c\u1ea3nh, kh\u00e1c
   c\u00e1ch \u0111\u1ecdc) \u2014 sinh t\u1ef1 \u0111\u1ed9ng t\u1eeb fix_text.json, KH\u00d4NG s\u1eeda tay. */
var FURI_FIX={
'''
fix_lines = []
for i, t in enumerate(sorted(FIXTEXT)):
    val = {str(k): v for k, v in sorted(FIXTEXT[t].items(), key=lambda kv: int(kv[0]))}
    fix_lines.append('%s:%s%s\n' % (json.dumps(t, ensure_ascii=False),
                                    json.dumps(val, ensure_ascii=False),
                                    ',' if i + 1 < len(FIXTEXT) else ''))
with open(os.path.join(out_dir, 'furi-fix.js'), 'w', encoding='utf-8', newline='\n') as f:
    f.write(FIXHEAD % len(FIXTEXT) + ''.join(fix_lines) + '};\n')

shutil.copyfile(os.path.join(src_dir, 'furi-engine.js'), os.path.join(out_dir, 'furi-engine.js'))
print('wrote %s (entries %d)' % (os.path.join(out_dir, 'furi-dict.js'), len(d)))
print('wrote %s (fix texts %d)' % (os.path.join(out_dir, 'furi-fix.js'), len(FIXTEXT)))
print('copied %s' % os.path.join(out_dir, 'furi-engine.js'))
