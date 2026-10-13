# -*- coding: utf-8 -*-
"""Builds the furigana dictionary (dict.json) for the N2 explanation texts.

* readings come from UniDic (fugashi) tokenisation of every explanation
* kanji token runs are merged into one entry (想像 + 力 -> 想像力)
* surfaces whose reading depends on context (中: なか/ちゅう, 日: ひ/か ...)
  get context-qualified entries (extra kana after / character before) picked by
  an iterative loop that renders the whole corpus with a Python port of the
  engine and bumps the context size of every entry that renders wrongly.
* expected.jsonl holds, per explanation, the base/rt pairs (with positions) the
  JS engine must produce -> verified by check.mjs.
"""
import json, re, sys, collections, io, os

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from fugashi import Tagger

KANJI = re.compile(r'^[\u3400-\u4DBF\u4E00-\u9FFF\uF900-\uFAFF\u3005]+$')
HAS_KANJI = re.compile(r'[\u3400-\u4DBF\u4E00-\u9FFF\uF900-\uFAFF\u3005]')
KANJI_CH = re.compile(r'[\u3400-\u4DBF\u4E00-\u9FFF\uF900-\uFAFF\u3005]')
KANA_CH = re.compile(r'[\u3041-\u3096\u30A1-\u30F6\u30FC]')
PREFIX_OK = re.compile(r'[\u3041-\u3096\u30A1-\u30F6\u30FC0-9０-９]')

OVERRIDE = json.load(open('override.json', encoding='utf-8')) if os.path.exists('override.json') else {}
MANUAL = json.load(open('manual_keys.json', encoding='utf-8')) if os.path.exists('manual_keys.json') else {}
FIX = json.load(open('fix.json', encoding='utf-8')) if os.path.exists('fix.json') else {}


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


tagger = Tagger()
rows = [json.loads(l) for l in open('explanations.jsonl', encoding='utf-8')]


# --------------------------------------------------------------- tokenisation
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
        if HAS_KANJI.search(surf):
            j, s, rd = i + 1, surf, reading_of(n)
            while (j < len(nodes) and KANJI.match(s) and KANJI.match(nodes[j].surface)
                   and reading_of(nodes[j])):
                nxt = nodes[j].surface
                k = text.find(nxt, pos)
                if k != pos:          # only merge tokens that touch in the text
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


def base_tail(surface):
    lastk = -1
    for i, ch in enumerate(surface):
        if KANJI_CH.search(ch):
            lastk = i
    return surface[:lastk + 1], surface[lastk + 1:]


def kana_after(text, end, limit=5):
    """hiragana run right after the group (katakana is not usable as context)"""
    out = ''
    for ch in text[end:end + limit]:
        if '\u3041' <= ch <= '\u3096':
            out += ch
        else:
            break
    return out


# ------------------------------------------------------------- the JS engine
def _segs(core):
    segs, buf, t = [], '', None
    for ch in core:
        tt = 'j' if KANJI_CH.search(ch) else 'k'
        if tt != t:
            if buf:
                segs.append((t, buf))
            buf, t = '', tt
        buf += ch
    if buf:
        segs.append((t, buf))
    return segs


def rubify(key, reading):
    base, tail = base_tail(key)
    rd = reading
    if tail and rd.endswith(tail):
        rd = rd[:-len(tail)]
    segs = _segs(base)
    pos, out = 0, []
    for i, (t, txt) in enumerate(segs):
        if t == 'k':
            if i == 0:
                idx = rd.find(txt, pos)
                if idx >= 0:
                    pos = idx + len(txt)
            out.append(('lit', txt))
            continue
        nxt = segs[i + 1] if i + 1 < len(segs) else None
        if nxt and nxt[0] == 'k':
            idx = rd.find(nxt[1], pos)
            if idx == pos:
                alt = rd.find(nxt[1], pos + 1)
                if alt >= 0:
                    idx = alt
            if idx >= 0:
                r = rd[pos:idx]
                pos = idx + len(nxt[1])
            else:
                r = rd[pos:]
                pos = len(rd)
        else:
            r = rd[pos:]
            pos = len(rd)
        out.append(('ruby', txt, r))
    out.append(('lit', tail))
    return out


def render(text, d, maxlen):
    """-> ([('lit',s) | ('ruby',pos,base,rt)], [(pos, kanji_uncovered)])"""
    out, miss, i, n = [], [], 0, len(text)
    while i < n:
        hit = None
        for L in LENS.get(text[i], ()):
            if L > n - i:
                continue
            cand = text[i:i + L]
            if cand in d:
                hit = cand
                break
        if hit and d[hit]:
            off = i
            for seg in rubify(hit, d[hit]):
                if seg[0] == 'ruby':
                    out.append(('ruby', off, seg[1], seg[2]))
                else:
                    out.append(('lit', seg[1]))
                off += len(seg[1])
            i += len(hit)
        elif hit:                     # khoá chặn (cách đọc rỗng) -> giữ nguyên, không chú thích
            out.append(('lit', hit))
            i += len(hit)
        else:
            ch = text[i]
            if KANJI_CH.search(ch):
                miss.append((i, ch))
            out.append(('lit', ch))
            i += 1
    return out, miss


def lens_index(d):
    """char -> key lengths (longest first) so lookup only tests real candidates"""
    idx = collections.defaultdict(list)
    for k in d:
        idx[k[0]].append(len(k))
    for c in idx:
        idx[c] = sorted(set(idx[c]), reverse=True)
    return dict(idx)


LENS = {}
# ------------------------------------------------- occurrences + candidates
OCC = []          # one dict per kanji group occurrence
IGNORED = []      # kanji groups UniDic cannot read (wrong kanji / Chinese forms)
CACHE = 'units_cache.json'
cache = {}
if os.path.exists(CACHE):
    try:
        blob = json.load(open(CACHE, encoding='utf-8'))
        if blob.get('v') == 3 and blob.get('n') == len(rows) and blob.get('ids') == [r['id'] for r in rows]:
            cache = {int(k): v for k, v in blob['units'].items()}
    except Exception:
        cache = {}


def units_for(ri):
    if ri in cache:
        return cache[ri]
    return build_units(rows[ri]['text'])


for ri, row in enumerate(rows):
    text = row['text']
    for u in units_for(ri):
        surface = u['surface']
        reading = OVERRIDE.get(surface, u['reading'])
        reading = FIX.get('%s|%s|%d' % (row['file'], row['id'], u['start']), reading)
        if not reading:
            # không đọc được: tổ hợp kanji sai / chữ Trung Quốc -> để nguyên, không chú thích
            IGNORED.append({'ri': ri, 'file': row['file'], 'id': row['id'], 'start': u['start'],
                            'end': u['end'], 'surface': surface})
            continue
        base, tail = base_tail(surface)
        rd = reading
        if tail and rd.endswith(tail):
            rd = rd[:-len(tail)]
        prev1 = text[u['start'] - 1] if u['start'] > 0 else ''
        prev2 = text[u['start'] - 2] if u['start'] > 1 else ''
        OCC.append({'ri': ri, 'file': row['file'], 'id': row['id'],
                    'surface': surface, 'reading': reading,
                    'start': u['start'], 'end': u['end'],
                    'base': base, 'rt': rd, 'base_end': u['start'] + len(base),
                    'ka': kana_after(text, u['end']),
                    'prev1': prev1, 'prev2': prev2})
for o in OCC:
    o['key_span'] = (o['start'], o['end'])

# remember the tokenisation so re-runs skip fugashi
if not cache:
    blob = {'v': 2, 'n': len(rows), 'ids': [r['id'] for r in rows],
            'units': {str(ri): units_for(ri) for ri in range(len(rows))}}
    json.dump(blob, open(CACHE, 'w', encoding='utf-8'), ensure_ascii=False)


def candidates(o):
    """least specific context first; each entry is (key, reading, kind)"""
    S, r, ka = o['surface'], o['reading'], o['ka']
    out = [(S, r, 'plain')]
    for k in (1, 2, 3, 4, 5):
        if len(ka) >= k:
            out.append((S + ka[:k], r + ka[:k], 'kana%d' % k))
    p1, p2 = o['prev1'], o['prev2']
    if p1 and PREFIX_OK.match(p1):
        pr = hira(p1) if KANA_CH.match(p1) else ''
        out.append((p1 + S, pr + r, 'prev1'))
        if len(ka) >= 1:
            out.append((p1 + S + ka[:1], pr + r + ka[:1], 'prev1+kana'))
        if p2 and PREFIX_OK.match(p2):
            pr2 = hira(p2) if KANA_CH.match(p2) else ''
            out.append((p2 + p1 + S, pr2 + pr + r, 'prev2'))
    return out


# ------------------------------------------------------- dictionary building
def build(levels):
    d, rules, unresolved = {}, [], []
    for o in OCC:
        cands = candidates(o)
        lv = levels.get(id(o), 0)
        if lv >= len(cands):
            unresolved.append(o)
            continue
        key, rd, kind = cands[lv]
        if key in d and d[key] != rd:                     # keep the earlier reading
            unresolved.append(o)
            continue
        d[key] = rd
        o['key'] = key
        o['key_reading'] = rd
        o['kind'] = kind
        if kind != 'plain':
            rules.append((o['surface'], key, rd, kind))
    for k, v in MANUAL.items():        # hand-written entries win
        d[k] = v
    for g in IGNORED:                  # tổ hợp không đọc được: "khoá chặn" -> render để trần
        d.setdefault(g['surface'], '')
    return d, rules, unresolved


def seg_map(base, rt, offset):
    """-> {absolute position: (kanji segment, reading)} for one ruby block"""
    out, pos = {}, 0
    for seg in rubify(base, rt):
        if seg[0] == 'ruby':
            out[offset + pos] = (seg[1], seg[2])
        pos += len(seg[1])
    return out


def expected_map(o):
    return seg_map(o['base'], o['rt'], o['start'])


def is_ignored(ri, pos):
    return any(g['ri'] == ri and g['start'] <= pos < g['end'] for g in IGNORED)


def check(d):
    """renders the whole corpus and compares kanji readings position by position"""
    global LENS
    LENS = lens_index(d)
    bad, misses = [], []
    by_text = collections.defaultdict(list)
    for o in OCC:
        by_text[o['ri']].append(o)
    blocks = []
    for ri, group in by_text.items():
        text = rows[ri]['text']
        blocks, miss = render(text, d, 0)
        for m in miss:
            if not is_ignored(ri, m[0]):        # bỏ qua tổ hợp kanji không đọc được
                misses.append((ri, m[0], m[1]))
        got = {}
        for b in blocks:
            if b[0] == 'ruby':
                got.update(seg_map(b[2], b[3], b[1]))
        for o in group:
            exp = expected_map(o)
            wrong = [(p, v, got.get(p)) for p, v in exp.items() if got.get(p) != v]
            if not wrong:
                continue
            o['bad_reason'] = '; '.join('%d want=%s got=%s' % (p, v[1], (g[1] if g else None))
                                        for p, v, g in wrong[:3])
            bad.append(o)
    return bad, misses, blocks


levels = {}
history = []
for round_ in range(30):
    for o in OCC:
        levels.setdefault(id(o), 0)
    d, rules, unresolved = build(levels)
    # remove entries that are not used by their own occurrence
    bad, misses, _ = check(d)
    history.append((round_, len(d), len(bad), len(unique_miss := {(m[1], m[2]) for m in misses})))
    if not bad and not misses:
        break
    progressed = False
    for o in bad:
        cands = candidates(o)
        lv = levels[id(o)]
        if lv + 1 < len(cands):
            levels[id(o)] = lv + 1
            progressed = True
    if not progressed:
        break

# ------------------------------------------------------------------- outputs
json.dump(d, open('dict.json', 'w', encoding='utf-8'), ensure_ascii=False, sort_keys=True)
json.dump(IGNORED, open('ignored.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

bad, misses, _ = check(d)
miss_set = {(m[1], m[2]) for m in misses}

exp = []
by_text_rows = collections.defaultdict(list)
for o in OCC:
    by_text_rows[o['ri']].append(o)
for ri, row in enumerate(rows):
    exp.append({'file': row['file'], 'id': row['id'], 'text': row['text'],
                'ruby': [[o['start'], o['base'], o['rt']] for o in by_text_rows[ri]]})
with open('expected.jsonl', 'w', encoding='utf-8') as f:
    f.write('\n'.join(json.dumps(e, ensure_ascii=False) for e in exp))

ctx = [o for o in OCC if o.get('kind') and o.get('kind') != 'plain']
with open('rules.txt', 'w', encoding='utf-8') as f:
    f.write('occurrences %d   dict entries %d   context entries %d\n' % (len(OCC), len(d), len(ctx)))
    f.write('bad occurrences %d   uncovered kanji %d   ignored groups %d\n\n' %
            (len(bad), len(miss_set), len(IGNORED)))
    f.write('=== CONTEXT KEYS ===\n')
    for o in sorted(ctx, key=lambda x: (x['surface'], x['kind'])):
        f.write('%-14s %-10s key=%-18s rd=%-16s (%s / %s)\n' %
                (o['surface'], o['kind'], o['key'], o['rt'], o['file'], o['id']))
    f.write('\n=== STILL BAD (%d) ===\n' % len(bad))
    for o in bad:
        t = rows[o['ri']]['text']
        around = t[max(0, o['start'] - 8):o['base_end'] + 8]
        f.write('%-10s %-8s want=%-18s key=%-16s %s | %s\n' %
                (o['surface'], o.get('kind', '?'), o['base'] + '/' + o['rt'],
                 o.get('key', '-'), o['bad_reason'], around))
    f.write('\n=== UNCOVERED KANJI (%d) ===\n' % len(miss_set))
    for pos, ch in sorted(miss_set):
        f.write('%s\n' % ch)
    f.write('\n=== IGNORED (UniDic không đọc được: kanji sai / chữ Trung Quốc) (%d) ===\n' % len(IGNORED))
    for g in IGNORED:
        f.write('%-10s %-6s %-6s start=%-4d %s\n' % (g['file'], g['id'], g['surface'], g['start'],
                                                      rows[g['ri']]['text'][max(0, g['start'] - 10):g['end'] + 10]))

print('rounds            : %d' % (history[-1][0] + 1))
print('history (round, entries, bad, miss):')
for h in history:
    print('   ', h)
print('occurrences       : %d' % len(OCC))
print('dict entries      : %d' % len(d))
print('context entries   : %d' % len(ctx))
print('bad occurrences   : %d' % len(bad))
print('uncovered kanji   : %d' % len(miss_set))
print('ignored groups    : %d' % len(IGNORED))

