# -*- coding: utf-8 -*-
"""Builds the furigana dictionary (dict.json) for the N2 corpus.

* corpus = texts.jsonl (mọi đoạn tiếng Nhật của app: passage / question /
  option / translation / explanation / heading / instruction — xem
  corpus-fields.mjs), mỗi dòng {file, id, field, idx, text}
* readings come from UniDic (fugashi) tokenisation of every text
* kanji token runs are merged into one entry (想像 + 力 -> 想像力)
* surfaces whose reading depends on context (中: なか/ちゅう, 日: ひ/か ...)
  get context-qualified entries (extra kana after / character before) picked by
  an iterative loop that renders the whole corpus with a Python port of the
  engine and bumps the context size of every entry that renders wrongly.
* expected.jsonl holds, per text, the base/rt pairs (with positions) the
  JS engine must produce -> verified by check.mjs / check_repo.mjs.
"""
import json, re, sys, collections, io, os

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from fugashi import Tagger

KANJI = re.compile(r'^[\u3400-\u4DBF\u4E00-\u9FFF\uF900-\uFAFF\u3005]+$')
HAS_KANJI = re.compile(r'[\u3400-\u4DBF\u4E00-\u9FFF\uF900-\uFAFF\u3005]')
KANJI_CH = re.compile(r'[\u3400-\u4DBF\u4E00-\u9FFF\uF900-\uFAFF\u3005]')
KANA_CH = re.compile(r'[\u3041-\u3096\u30A1-\u30F6\u30FC]')
KANA_ONLY = re.compile(r'^[\u3041-\u3096\u30A1-\u30F6\u30FC]+$')
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
rows = [json.loads(l) for l in open('texts.jsonl', encoding='utf-8')]


def rkey(row):
    """id của một đoạn text: file|id|field|idx (idx = -1 với field không phải option)"""
    return '%s|%s|%s|%d' % (row['file'], row['id'], row['field'], row['idx'])



def align_reading(surface, reading):
    """Giữ nguyên ký tự katakana của mặt chữ trong cách đọc (ヶ月 -> ヶげつ) để
    engine cắt ruby đúng: ruby chỉ nằm trên kanji, phần katakana để trần."""
    out = list(reading)
    pos = 0
    for ch in surface:
        if '\u30A1' <= ch <= '\u30F6':
            h = hira(ch)
            i = reading.find(h, pos)
            if 0 <= i < len(out):
                out[i] = ch
                pos = i + 1
    return ''.join(out)


def nounish(node):
    """chỉ gộp token kế tiếp vào cụm kanji khi nó là danh từ/hậu tố —
    tránh gộp hai từ khác nhau (今 + 出 -> 今出, 一度 + 見 -> 一度見 ...) thành
    một khoá giả sẽ \"cướp\" chỗ của câu khác khi engine khớp dài nhất."""
    return getattr(node.feature, 'pos1', None) in ('名詞', '接尾辞')


def split_mixed(surf, rd):
    """Token chứa ký tự không-kanji không có trong cách đọc (vd. 二、三 / ニサン):
    cắt thành từng phần (kanji hoặc dấu), mỗi phần kanji lấy cách đọc riêng.
    Trả về [(surface, reading), ...] hoặc None nếu không kiểm chứng được."""
    if all(KANJI_CH.search(c) or c in rd for c in surf):
        return None
    parts, buf = [], ''
    for c in surf:
        if KANJI_CH.search(c):
            buf += c
        else:
            if buf:
                parts.append(buf)
                buf = ''
            parts.append(c)
    if buf:
        parts.append(buf)
    out, joined = [], ''
    for p in parts:
        if not KANJI_CH.search(p):
            out.append((p, ''))
            continue
        nodes = list(tagger(p))
        r = align_reading(p, reading_of(nodes[0])) if len(nodes) == 1 else ''
        if not r:
            return None
        out.append((p, r))
        joined += r
    return out if joined == rd else None


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
        mixed = split_mixed(surf, reading_of(n)) if HAS_KANJI.search(surf) else None
        if mixed:
            # token trộn dấu (vd. 二、三): tách thành từng phần để ruby đúng chỗ
            p_at = start
            for p_surf, p_rd in mixed:
                if p_rd:
                    units.append({'surface': p_surf, 'reading': p_rd,
                                  'start': p_at, 'end': p_at + len(p_surf)})
                p_at += len(p_surf)
            pos = p_at
            i += 1
            continue
        if HAS_KANJI.search(surf):
            j, s, rd = i + 1, surf, align_reading(surf, reading_of(n))
            while (j < len(nodes) and KANJI.match(s) and KANJI.match(nodes[j].surface)
                   and nounish(nodes[j]) and reading_of(nodes[j])):
                nxt = nodes[j].surface
                k = text.find(nxt, pos)
                if k != pos:          # only merge tokens that touch in the text
                    break
                s += nxt
                rd += align_reading(nxt, reading_of(nodes[j]))
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


# tiện ích gỡ lỗi:  python build_dict.py units data_2021_07.js c2-3 passage -1
# (in ra màn hình + ghi units_dbg.txt để xem lại bằng editor)
if len(sys.argv) > 5 and sys.argv[1] == 'units':
    _lines = []
    for _r in rows:
        if (_r['file'], _r['id'], _r['field'], str(_r['idx'])) == tuple(sys.argv[2:6]):
            _lines.append('%s | %s | %s | %s\n%s' % (_r['file'], _r['id'], _r['field'], _r['idx'], _r['text']))
            for _u in build_units(_r['text']):
                _lines.append('  %-12s %-20s start=%-4d end=%-4d ...%s...' %
                              (_u['surface'], _u['reading'], _u['start'], _u['end'],
                               _r['text'][max(0, _u['start'] - 8):_u['end'] + 8]))
    with open('units_dbg.txt', 'w', encoding='utf-8') as _f:
        _f.write('\n'.join(_lines) + '\n')
    print('\n'.join(_lines))
    sys.exit(0)


def next_ctx(text, end, limit=8):
    """run of non-kanji characters right after the group: hiragana, katakana,
    punctuation, digits ... (khÃ´ng láº¥y '<' '&' Ä‘á»ƒ khoá không chứa thẻ HTML)"""
    out = ''
    for ch in text[end:end + limit]:
        if KANJI_CH.search(ch) or ch in '<&':
            break
        out += ch
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
                elif KANA_ONLY.match(txt):     # vd. ヶ trong ヶ月 (đọc かげつ)
                    pos += len(txt)            # -> giả định mỗi ký tự kana ăn 1 mora
            out.append(('lit', txt))
            continue
        nxt = segs[i + 1] if i + 1 < len(segs) else None
        if nxt and nxt[0] == 'k':
            nt = nxt[1]
            idx = rd.find(nt, pos)
            if idx == pos:
                alt = rd.find(nt, pos + 1)
                if alt >= 0:
                    idx = alt
            if idx >= 0:
                r = rd[pos:idx]
                pos = idx + len(nt)
            elif KANA_ONLY.match(nt):
                r = rd[pos:pos + len(nt)]
                pos = min(pos + len(nt), len(rd))
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
    fx = FIXTEXT.get(text) or {}
    fpos = sorted(fx)          # ngoại lệ luôn thắng: không khoá nào được vắt qua
    fi = 0
    while i < n:
        while fi < len(fpos) and fpos[fi] < i:
            fi += 1
        if fi < len(fpos) and fpos[fi] == i:
            base, rd = fx[i]
            if not rd:                        # cách đọc rỗng -> để trần
                out.append(('lit', base))
                i += len(base)
                fi += 1
                continue
            off = i
            for seg in rubify(base, rd):      # cắt ruby y như khoá trong bảng đọc
                if seg[0] == 'ruby':
                    out.append(('ruby', off, seg[1], seg[2]))
                else:
                    out.append(('lit', seg[1]))
                off += len(seg[1])
            i += len(base)
            fi += 1
            continue
        lim = (fpos[fi] - i) if fi < len(fpos) else n - i
        hit = None
        for L in LENS.get(text[i], ()):
            if L > lim:
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
# ngoại lệ cuối: đúng đoạn text + vị trí (xem fix_text.json) — dùng cho các câu mà
# bảng đọc không thể phân biệt (cùng ngữ cảnh, khác cách đọc) hoặc bị khoá của câu
# khác "cướp" chỗ; giá trị là (mặt chữ, cách đọc) đã soát tay.
FIXTEXT = {}
if os.path.exists('fix_text.json'):
    _blob = json.load(open('fix_text.json', encoding='utf-8'))
    FIXTEXT = {t: {int(k): (v[0], v[1]) for k, v in m.items()} for t, m in _blob.items()}
# ------------------------------------------------- occurrences + candidates
OCC = []          # one dict per kanji group occurrence
IGNORED = []      # kanji groups UniDic cannot read (wrong kanji / Chinese forms)
CACHE = 'units_cache.json'
cache = {}
if os.path.exists(CACHE):
    try:
        blob = json.load(open(CACHE, encoding='utf-8'))
        if blob.get('v') == 7 and blob.get('n') == len(rows) and blob.get('keys') == [rkey(r) for r in rows]:
            cache = {int(k): v for k, v in blob['units'].items()}
    except Exception:
        cache = {}


def units_for(ri):
    if ri in cache:
        return cache[ri]
    return build_units(rows[ri]['text'])


def kanji_runs(s):
    return [m.span() for m in re.finditer(r'[\u3400-\u4DBF\u4E00-\u9FFF\uF900-\uFAFF\u3005]+', s)]


# read_fix.json: [regex, reading, target] — chỗ UniDic đọc sai hẳn (vd. この間 ->
# かん) hoặc hai cách đọc lệch nhau thì chọn một cách cho cả corpus.
# `target` (tuỳ chọn) chỉ ra unit cần sửa trong đoạn khớp:
#   * bỏ trống  -> bắt đầu cụm kanji cuối cùng của đoạn khớp
#   * số        -> vị trí ký tự trong đoạn khớp (vd. 0 với "ヶ月", "か所")
#   * chuỗi     -> regex con trong đoạn khớp (vd. "月" với "[0-9]+月")
PAT_FIX = json.load(open('read_fix.json', encoding='utf-8')) if os.path.exists('read_fix.json') else []
PAT_READ = collections.defaultdict(dict)
PAT_HIT = collections.Counter()
PAT_USED = collections.Counter()


def pat_target(it, m):
    """-> vị trí bắt đầu của char/mẫu con cần sửa, hoặc None nếu không rõ"""
    if len(it) < 3 or it[2] is None:
        runs = kanji_runs(m.group(0))
        if not runs:
            return None
        return m.start() + runs[-1][0]
    tgt = it[2]
    if isinstance(tgt, int):
        return m.start() + tgt
    sub = re.search(tgt, m.group(0))
    return (m.start() + sub.start()) if sub else None


for _ri, _row in enumerate(rows):
    _t = _row['text']
    for _it in PAT_FIX:
        _pat, _rd = _it[0], _it[1]
        for _m in re.finditer(_pat, _t):
            _at = pat_target(_it, _m)
            if _at is None:
                continue
            PAT_READ[_ri][_at] = (_pat + ' -> ' + _rd, _rd)
            PAT_HIT[_pat + ' -> ' + _rd] += 1


for ri, row in enumerate(rows):
    text = row['text']
    for u in units_for(ri):
        surface = u['surface']
        reading = OVERRIDE.get(surface, u['reading'])
        reading = FIX.get('%s|%d' % (rkey(row), u['start']), reading)
        _pat = PAT_READ.get(ri, {}).get(u['start'])
        if _pat is not None:
            reading = _pat[1]
            PAT_USED[_pat[0]] += 1
        if not reading:
            # không đọc được: tổ hợp kanji sai / chữ Trung Quốc -> để nguyên, không chú thích
            IGNORED.append({'ri': ri, 'file': row['file'], 'id': row['id'],
                            'field': row['field'], 'idx': row['idx'],
                            'start': u['start'], 'end': u['end'], 'surface': surface})
            continue
        base, tail = base_tail(surface)
        rd = reading
        if tail and rd.endswith(tail):
            rd = rd[:-len(tail)]
        prev1 = text[u['start'] - 1] if u['start'] > 0 else ''
        prev2 = text[u['start'] - 2] if u['start'] > 1 else ''
        prev3 = text[u['start'] - 3] if u['start'] > 2 else ''
        OCC.append({'ri': ri, 'file': row['file'], 'id': row['id'],
                    'field': row['field'], 'idx': row['idx'],
                    'surface': surface, 'reading': reading,
                    'start': u['start'], 'end': u['end'],
                    'base': base, 'rt': rd, 'base_end': u['start'] + len(base),
                    'ka': next_ctx(text, u['end']),
                    'prev1': prev1, 'prev2': prev2, 'prev3': prev3})
for o in OCC:
    o['key_span'] = (o['start'], o['end'])

# remember the tokenisation so re-runs skip fugashi
if not cache:
    blob = {'v': 7, 'n': len(rows), 'keys': [rkey(r) for r in rows],
            'units': {str(ri): units_for(ri) for ri in range(len(rows))}}
    json.dump(blob, open(CACHE, 'w', encoding='utf-8'), ensure_ascii=False)


def candidates(o):
    """least specific context first; each entry is (key, reading, kind)"""
    S, r, ka = o['surface'], o['reading'], o['ka']
    out = [(S, r, 'plain')]
    for k in (1, 2, 3, 4, 5, 6, 7, 8):
        if len(ka) >= k:
            out.append((S + ka[:k], r + ka[:k], 'kana%d' % k))
    p1, p2, p3 = o['prev1'], o['prev2'], o['prev3']
    if p1 and PREFIX_OK.match(p1):
        pr = p1 if KANA_CH.match(p1) else ''    # giữ nguyên katakana để khớp mặt chữ khoá
        out.append((p1 + S, pr + r, 'prev1'))
        if len(ka) >= 1:
            out.append((p1 + S + ka[:1], pr + r + ka[:1], 'prev1+kana'))
        if p2 and PREFIX_OK.match(p2):
            pr2 = p2 if KANA_CH.match(p2) else ''
            out.append((p2 + p1 + S, pr2 + pr + r, 'prev2'))
            if len(ka) >= 1:
                out.append((p2 + p1 + S + ka[:1], pr2 + pr + r + ka[:1], 'prev2+kana'))
            if p3 and PREFIX_OK.match(p3):
                pr3 = p3 if KANA_CH.match(p3) else ''
                out.append((p3 + p2 + p1 + S, pr3 + pr2 + pr + r, 'prev3'))
    return out


# ------------------------------------------------------- dictionary building
def build(levels):
    d, rules, unresolved, holder = {}, [], [], {}
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
        holder.setdefault(key, o)
        o['key'] = key
        o['key_reading'] = rd
        o['kind'] = kind
        if kind != 'plain':
            rules.append((o['surface'], key, rd, kind))
    for k, v in MANUAL.items():        # hand-written entries win
        d[k] = v
    for g in IGNORED:                  # tổ hợp không đọc được: "khoá chặn" -> render để trần
        d.setdefault(g['surface'], '')
    return d, rules, unresolved, holder


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
ROUNDS = 250
best = None          # (điểm, bad, miss, bản chụp levels) — trạng thái tốt nhất đã đạt
for round_ in range(ROUNDS):
    for o in OCC:
        levels.setdefault(id(o), 0)
    d, rules, unresolved, holder = build(levels)
    # remove entries that are not used by their own occurrence
    bad, misses, _ = check(d)
    n_miss = len({(m[1], m[2]) for m in misses})
    history.append((round_, len(d), len(bad), n_miss))
    score = len(bad) + n_miss
    if best is None or score < best[0]:
        best = (score, len(bad), n_miss, dict(levels))
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
        # câu đã hết ngữ cảnh để nâng (vd. một kanji đứng riêng) -> đẩy chủ khoá tranh chấp lên
        for o in bad:
            if len(candidates(o)) > 1:
                continue
            for key, rd, kind in candidates(o):
                h = holder.get(key)
                if h is not None and h is not o:
                    hl = levels.get(id(h), 0)
                    if hl + 1 < len(candidates(h)):
                        levels[id(h)] = hl + 1
                        progressed = True
                        break
            if progressed:
                break
    if not progressed:
        break
    if round_ == ROUNDS - 1:
        print('!! đã chạm trần %d vòng, vẫn còn %d câu lệch' % (ROUNDS, len(bad)))

if best is not None and (best[1] != history[-1][2] or best[2] != history[-1][3]):
    levels = best[3]
    d, rules, unresolved, holder = build(levels)
    bad, misses, _ = check(d)
    print('> khôi phục trạng thái tốt nhất: bad=%d miss=%d (thay vì bad=%d miss=%d)'
          % (best[1], best[2], history[-1][2], history[-1][3]))

# --------------------------------------------- ngoại lệ cuối: ghim theo đoạn text
baked_new = []
for _ in range(6):
    if not bad:
        break
    for o in bad:
        _t = rows[o['ri']]['text']
        if o['start'] not in (FIXTEXT.get(_t) or {}):
            baked_new.append(o)
        FIXTEXT.setdefault(_t, {})[o['start']] = (o['base'], o['rt'])
    d, rules, unresolved, holder = build(levels)
    bad, misses, _ = check(d)
if bad or misses:
    print('!! sau khi ghim ngoại lệ vẫn còn %d câu lệch, %d kanji thiếu' % (len(bad), len(misses)))
if baked_new:
    print('> ghim thêm %d ngoại lệ theo đoạn text (xem fix_text.json / rules.txt)' % len(baked_new))

# dọn ngoại lệ không còn cần: bỏ thử từng cái, nếu vẫn 0 lệch thì không ghim nữa
pruned = []
for _t in list(FIXTEXT):
    if _t not in {r['text'] for r in rows}:            # đoạn đã đổi/không còn -> bỏ
        pruned.append((_t, '-', ('(đoạn không còn trong corpus)', '')))
        del FIXTEXT[_t]
        continue
    for _p in list(FIXTEXT[_t]):
        _save = FIXTEXT[_t].pop(_p)
        if not FIXTEXT[_t]:
            del FIXTEXT[_t]
        d, rules, unresolved, holder = build(levels)
        b2, m2, _ = check(d)
        if b2 or m2:                                   # còn cần -> ghim lại
            FIXTEXT.setdefault(_t, {})[_p] = _save
        else:
            pruned.append((_t, _p, _save))
            bad, misses = b2, m2
d, rules, unresolved, holder = build(levels)
bad, misses, _ = check(d)
if bad or misses:
    print('!! sau khi dọn ngoại lệ còn %d câu lệch, %d kanji thiếu' % (len(bad), len(misses)))
if pruned:
    print('> bỏ %d ngoại lệ không còn cần (bảng đọc đã tự đúng)' % len(pruned))
with open('fix_text.json', 'w', encoding='utf-8') as f:
    json.dump({_t: {str(k): list(v) for k, v in sorted(m.items())}
               for _t, m in sorted(FIXTEXT.items())}, f, ensure_ascii=False, indent=1)

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
    exp.append({'file': row['file'], 'id': row['id'], 'field': row['field'], 'idx': row['idx'],
                'text': row['text'],
                'ruby': [[o['start'], o['base'], o['rt']] for o in by_text_rows[ri]]})
with open('expected.jsonl', 'w', encoding='utf-8') as f:
    f.write('\n'.join(json.dumps(e, ensure_ascii=False) for e in exp))

ctx = [o for o in OCC if o.get('kind') and o.get('kind') != 'plain']
by_field = collections.Counter()
for r in rows:
    by_field[r['field']] += 1
with open('rules.txt', 'w', encoding='utf-8') as f:
    f.write('texts %d   dict entries %d   context entries %d\n' %
            (len(rows), len(d), len(ctx)))
    f.write('fields: %s\n' % ', '.join('%s=%d' % kv for kv in sorted(by_field.items())))
    f.write('bad occurrences %d   uncovered kanji %d   ignored groups %d\n\n' %
            (len(bad), len(miss_set), len(IGNORED)))
    f.write('=== CONTEXT KEYS ===\n')
    for o in sorted(ctx, key=lambda x: (x['surface'], x['kind'])):
        f.write('%-14s %-10s key=%-18s rd=%-16s (%s / %s / %s)\n' %
                (o['surface'], o['kind'], o['key'], o['rt'], o['file'], o['id'], o['field']))
    f.write('\n=== STILL BAD (%d) ===\n' % len(bad))
    for o in bad:
        t = rows[o['ri']]['text']
        around = t[max(0, o['start'] - 24):o['base_end'] + 24]
        f.write('%-9s %-7s %-6s %-5d %s/%s want=%-14s got=%-14s key=%-14s %s | %s\n' %
                (o['file'].replace('data_', '').replace('.js', ''), o['id'], o['field'], o['idx'],
                 o['surface'], o.get('kind', '?'), o['base'] + '/' + o['rt'],
                 (o['bad_reason'].split('got=')[-1] if 'got=' in o['bad_reason'] else '-'),
                 o.get('key', '-'), o['bad_reason'], around))
    f.write('\n=== UNCOVERED KANJI (%d) ===\n' % len(miss_set))
    for pos, ch in sorted(miss_set):
        f.write('%s\n' % ch)
    f.write('\n=== IGNORED (UniDic không đọc được: kanji sai / chữ Trung Quốc) (%d) ===\n' % len(IGNORED))
    for g in IGNORED:
        f.write('%-10s %-6s %-12s %-6s start=%-4d %s\n' % (g['file'], g['id'], g['field'], g['surface'], g['start'],
                                                           rows[g['ri']]['text'][max(0, g['start'] - 10):g['end'] + 10]))
    f.write('\n=== NGOẠI LỆ THEO ĐOẠN TEXT (fix_text.json) (%d đoạn) ===\n' % len(FIXTEXT))
    for _t, _m in sorted(FIXTEXT.items()):
        _src = [r for r in rows if r['text'] == _t]
        _where = ', '.join('%s %s %s %s' % (
            r['file'].replace('data_', '').replace('.js', ''), r['id'], r['field'], r['idx'])
            for r in _src)[:52]
        _where = _where + ', ...' if len(_src) > 1 else _where
        for _k, _v in sorted(_m.items()):
            f.write('%-56s pos=%-4d %-10s %-14s  ...%s...\n' % (
                _where, _k, _v[0], _v[1], _t[max(0, _k - 8):_k + len(_v[0]) + 10]))

print('rounds            : %d' % (history[-1][0] + 1))
print('history (round, entries, bad, miss):')
for h in history:
    print('   ', h)
print('pat_fix khớp mẫu : %s' % (dict(PAT_HIT) or '-'))
print('pat_fix áp dụng  : %s' % (dict(PAT_USED) or '-'))
for pat, rd in [(it[0], it[1]) for it in PAT_FIX]:
    k = pat + ' -> ' + rd
    if not PAT_HIT.get(k):
        print('!! read_fix không khớp ở đâu: %s' % k)
    elif PAT_USED.get(k, 0) < PAT_HIT.get(k):
        print('!! read_fix khá»›p %d nhÆ°ng chá»‰ áp dụng %d lần: %s' %
              (PAT_HIT[k], PAT_USED.get(k, 0), k))
print('occurrences       : %d' % len(OCC))
print('dict entries      : %d' % len(d))
print('context entries   : %d' % len(ctx))
print('bad occurrences   : %d' % len(bad))
print('uncovered kanji   : %d' % len(miss_set))
print('ignored groups    : %d' % len(IGNORED))


