# -*- coding: utf-8 -*-
"""Kiem tra file data_YYYY_MM.js cua app JLPT_test.

usage:
  python validate_data.py <data_YYYY_MM.js> [keys.json] [--snapshot out.json] [--report out.txt]

  <keys.json>  : doi chieu dap an (1-based) theo tung section, dang
                 { "問題1 漢字読み": [4,3,1,2,4], "聴解問題1 課題理解": [4,4,2,3,3], ... }
  --snapshot   : ghi dap an hien co cua file ra keys.json (lam baseline cho cac lan sua sau)
  --report     : ghi ket qua ra file (tien cho viec doc lai bang tool)

Kiem tra: cu phap JS (esprima) / so section / so cau / id trung / so luong lua chon
          (cau 即時応答 chi co 3) / answer trong khoang / thieu question (loi cung)
          / thieu passage-translation-explanation (canh bao).
Exit code 1 neu co loi cung.
Can: esprima (C:\\ProgramData\\Lib hoac site-packages).
"""
import io, os, sys, json

try:                                   # in tieng Nhat/Viet du stdout bi redirect (cp1252)
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

LIB = r'C:\ProgramData\Lib'
if os.path.isdir(LIB) and LIB not in sys.path:
    sys.path.insert(0, LIB)
try:
    import esprima
except ImportError:
    sys.exit('Thieu esprima. Cai bang:  python -m pip install --target "%s" esprima' % LIB)

argv = sys.argv[1:]
snapshot = report = None
pos = []
i = 0
while i < len(argv):
    if argv[i] == '--snapshot':
        snapshot = argv[i + 1]; i += 2
    elif argv[i] == '--report':
        report = argv[i + 1]; i += 2
    else:
        pos.append(argv[i]); i += 1
if not pos:
    sys.exit(__doc__)
path = pos[0]
keys_path = pos[1] if len(pos) > 1 else None

src = io.open(path, encoding='utf-8').read()
if src.startswith('\ufeff'):
    sys.exit('!! File co BOM UTF-8 — phai luu khong BOM.')

buf = []


def P(*a):
    s = ' '.join(str(x) for x in a)
    print(s)
    buf.append(s)


try:
    tree = esprima.parseScript(src)
except Exception as e:
    P('!! LOI CU PHAP: %s' % e)
    P('   (thu chay: python tools/brackets.py "%s")' % path)
    if report:
        io.open(report, 'w', encoding='utf-8').write('\n'.join(buf) + '\n')
    sys.exit(1)


def to_py(n):
    if n is None:
        return None
    t = n.type
    if t == 'ObjectExpression':
        d = {}
        for p in n.properties:
            k = p.key.name if p.key.type == 'Identifier' else p.key.value
            d[k] = to_py(p.value)
        return d
    if t == 'ArrayExpression':
        return [to_py(e) for e in n.elements]
    if t == 'Literal':
        return n.value
    raise Exception('unhandled node %s' % t)


call = None
for st in tree.body:
    e = getattr(st, 'expression', None)
    if e is not None and getattr(e, 'type', '') == 'CallExpression' \
            and getattr(e.callee, 'name', '') == 'JLPT_REGISTER':
        call = e
if call is None:
    sys.exit('!! Khong tim thay JLPT_REGISTER({...})')
reg = to_py(call.arguments[0])
meta, data = reg['metadata'], reg['data']

keys = json.load(io.open(keys_path, encoding='utf-8')) if keys_path else None
snap = {}
ids = {}
problems, warns = [], []
total = 0

P('metadata:', json.dumps(meta, ensure_ascii=False))
P('sections:', len(data))
for si, sec in enumerate(data):
    head, tab, qs = sec['section'], sec['tab'], sec['questions']
    total += len(qs)
    snap[head] = [(q['answer'] + 1) if isinstance(q.get('answer'), int) else None for q in qs]
    want = 3 if ('聴解' in tab and '即時応答' in head) else 4
    key = keys.get(head) if keys else None
    if keys and key is None:
        problems.append('!! section "%s" khong co trong keys.json' % head)
    elif keys and len(key) != len(qs):
        problems.append('!! "%s": %d cau nhung key co %d' % (head, len(qs), len(key)))
    for qi, q in enumerate(qs):
        qid = q.get('id')
        ids[qid] = ids.get(qid, 0) + 1
        nopt = len(q.get('options') or [])
        if nopt != want:
            problems.append('!! "%s" #%d (%s): %d lua chon (mong doi %d)' % (head, qi + 1, qid, nopt, want))
        a = q.get('answer')
        if a is None or not (0 <= a < nopt):
            problems.append('!! "%s" #%d (%s): answer=%s' % (head, qi + 1, qid, a))
        elif key and qi < len(key) and a + 1 != key[qi]:
            problems.append('!! LECH DAP AN "%s" #%d (%s): data=%d key=%d' % (head, qi + 1, qid, a + 1, key[qi]))
        if not q.get('question'):
            problems.append('!! thieu question: %s (%s #%d)' % (qid, head, qi + 1))
        for f in ('passage', 'translation', 'explanation'):
            if not q.get(f):
                warns.append('.. thieu %s: %s (%s #%d)' % (f, qid, head, qi + 1))
    P('%-34s %2d cau  note=%s' % (head, len(qs), ('key ok' if key and len(key) == len(qs) else ('khong co key' if not keys else 'KEY LECH'))))

dup = [k for k, v in ids.items() if v > 1]
if dup:
    problems.append('!! id trung: %s' % dup)
P('TOTAL: %d cau | %d section | id duy nhat: %d' % (total, len(data), len(ids)))
P('LOI CUNG (%d):' % len(problems))
for p in problems:
    P(' ', p)
P('CANH BAO (%d):' % len(warns))
for w in warns:
    P(' ', w)

if snapshot:
    io.open(snapshot, 'w', encoding='utf-8').write(json.dumps(snap, ensure_ascii=False, indent=1))
    P('da ghi snapshot ->', snapshot)
if report:
    io.open(report, 'w', encoding='utf-8').write('\n'.join(buf) + '\n')
sys.exit(1 if problems else 0)
