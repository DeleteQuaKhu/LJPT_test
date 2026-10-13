# -*- coding: utf-8 -*-
"""Kiểm tra một mẫu trong read_fix.json: dòng nào khớp, offset, unit nào chứa
offset đó và đọc ra sao.

    python dbg_pat.py "毎年行っている"
"""
import io, json, re, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from fugashi import Tagger

KANJI_CH = re.compile(r'[\u3400-\u4DBF\u4E00-\u9FFF\uF900-\uFAFF\u3005]')
tagger = Tagger()


def hira(s):
    return ''.join(chr(ord(c) - 0x60) if 0x30A1 <= ord(c) <= 0x30F6 else c for c in s)


def reading_of(node):
    f = node.feature
    for field in ('kana', 'pron'):
        try:
            v = f[field]
        except Exception:
            v = getattr(f, field, None)
        if v and v != '*':
            return hira(v)
    return ''


def nounish(node):
    return getattr(node.feature, 'pos1', None) in ('名詞', '接尾辞')


def build_units(text):
    units = []
    pos, i, nodes = 0, 0, list(tagger(text))
    while i < len(nodes):
        n = nodes[i]
        surf = n.surface
        start = text.find(surf, pos)
        if start < 0:
            start = pos
        end = start + len(surf)
        pos = end
        if re.search(r'[\u3400-\u4DBF\u4E00-\u9FFF\uF900-\uFAFF\u3005]', surf):
            j, s, rd = i + 1, surf, reading_of(n)
            while (j < len(nodes) and re.match(r'^[\u3400-\u4DBF\u4E00-\u9FFF\uF900-\uFAFF\u3005]+$', s)
                   and re.match(r'^[\u3400-\u4DBF\u4E00-\u9FFF\uF900-\uFAFF\u3005]+$', nodes[j].surface)
                   and nounish(nodes[j]) and reading_of(nodes[j])):
                nxt = nodes[j].surface
                k = text.find(nxt, pos)
                if k != pos:
                    break
                s += nxt
                rd += reading_of(nodes[j])
                pos = k + len(nxt)
                end = pos
                j += 1
            units.append({'surface': s, 'reading': rd, 'start': start, 'end': end})
            i = j
        else:
            i += 1
    return units


pat = sys.argv[1]
rows = [json.loads(l) for l in open('texts.jsonl', encoding='utf-8')]
hits = 0
for ri, r in enumerate(rows):
    for m in re.finditer(pat, r['text']):
        runs = [mm.span() for mm in re.finditer(
            r'[\u3400-\u4DBF\u4E00-\u9FFF\uF900-\uFAFF\u3005]+', m.group(0))]
        which = int(sys.argv[2]) if len(sys.argv) > 2 else -1
        off = m.start() + runs[which][0]
        hits += 1
        print('--- %s %s %s %s  off=%d  match=%r' %
              (r['file'], r['id'], r['field'], r['idx'], off, m.group(0)))
        for u in build_units(r['text']):
            mark = ' <<<' if u['start'] == off else ('  (contains)' if u['start'] < off < u['end'] else '')
            if mark or abs(u['start'] - off) < 30:
                print('      %-10s %-14s start=%-4d end=%-4d%s' %
                      (u['surface'], u['reading'], u['start'], u['end'], mark))
print('hits: %d' % hits)
