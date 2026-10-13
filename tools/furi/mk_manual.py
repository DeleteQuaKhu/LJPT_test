# -*- coding: utf-8 -*-
"""Builds manual_keys.json / fix.json from the original texts.

The keys are cut out of the source text so the exact characters (full width
brackets, spaces, ideographic comma ...) are used, and the reading is composed
from the kanji core reading plus the literal prefix/suffix that stays in the key.
"""
import json, re

KANJI_CH = re.compile(r'[\u3400-\u4DBF\u4E00-\u9FFF\uF900-\uFAFF\u3005]')
KANA_CH = re.compile(r'^[\u3041-\u3096\u30A1-\u30F6\u30FC]+$')


def hira(s):
    return ''.join(chr(ord(c) - 0x60) if 0x30A1 <= ord(c) <= 0x30F6 else c for c in s)


def reading_for(key, core):
    first = last = None
    for i, ch in enumerate(key):
        if KANJI_CH.search(ch):
            first = i if first is None else first
            last = i
    pre, suf = key[:first], key[last + 1:]
    pr = hira(pre) if KANA_CH.match(pre) else ''
    return pr + core + suf


rows = [json.loads(l) for l in open('texts.jsonl', encoding='utf-8')]
by = {(r['file'], r['id'], r['field'], r['idx']): r for r in rows}

# (file, id, field, regex, core reading of the kanji run)
CASES = [
    ('data_2019_12.js', 'b14-2', 'explanation', r'（土', 'ど'),
    ('data_2019_7.js', 'a3-3', 'explanation', r'・間[ 　]?[(（]', 'かん'),
    ('data_2019_7.js', 'b13-1', 'explanation', r'、時に', 'とき'),
    ('data_2023_12.js', 'd3-3', 'explanation', r'連れ[ 　]?[(（]', 'づ'),
    ('data_2020_12.js', 'a3-3', 'explanation', r'一（', 'ひと'),
    ('data_2020_12.js', 'b11-9', 'explanation', r'次の撮影', 'つぎのさつえい'),
]

manual = {}
for f, i, fld, pat, core in CASES:
    text = by[(f, i, fld, -1)]['text']
    m = re.search(pat, text)
    assert m, (f, i, fld, pat)
    key = m.group(0)
    manual[key] = reading_for(key, core)
    print('%s %s %s  key=%r  rd=%r' % (f, i, fld, key, manual[key]))

json.dump(manual, open('manual_keys.json', 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)

# occurrences whose UniDic reading is simply wrong:
#   (file, id, field, anchor, offset inside anchor, reading)
FIXCASES = [
    ('data_2021_07.js', 'a6-1', 'explanation', '②水', 1, 'みず'),
    ('data_2020_12.js', 'a3-3', 'explanation', '一（ひと）', 0, 'ひと'),
]
FIX = {}
for f, i, fld, anchor, sub, reading in FIXCASES:
    text = by[(f, i, fld, -1)]['text']
    j = text.index(anchor) + sub
    FIX['%s|%s|%s|%d|%d' % (f, i, fld, -1, j)] = reading
    print('%s %s %s  fix @%d (%s) -> %s' % (f, i, fld, j, text[j], reading))
json.dump(FIX, open('fix.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
