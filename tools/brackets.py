# -*- coding: utf-8 -*-
"""Kiem tra can bang ngoac {} [] va chuoi trich dan cua file data_*.js.

usage: python brackets.py <data_*.js> [out.txt]
Exit code 1 neu phat hien loi (rat huu ich khi file data bi thieu ]}, sau mot section).
"""
import io, sys

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

path = sys.argv[1]
src = io.open(path, encoding='utf-8').read()
stack, line, in_str, esc, out, i = [], 1, None, False, [], 0
while i < len(src):
    c = src[i]
    if in_str:
        if esc:
            esc = False
        elif c == '\\':
            esc = True
        elif c == in_str:
            in_str = None
    else:
        if c in ('"', "'"):
            in_str = c
        elif c in '[{':
            stack.append((c, line))
        elif c in ']}':
            if not stack:
                out.append('!! line %d: dong %r nhung khong co ngoac mo' % (line, c))
            else:
                op, ol = stack.pop()
                if (op, c) not in (('{', '}'), ('[', ']')):
                    out.append('!! line %d: %r khong khop voi %r mo o line %d' % (line, c, op, ol))
    if c == '\n':
        line += 1
    i += 1

if in_str:
    out.append('!! chuoi trich dan chua dong (mo bang %r)' % in_str)
if stack:
    out.append('!! con %d ngoac chua dong, mo gan nhat o line: %s'
               % (len(stack), [ol for _, ol in stack][-8:]))

txt = '\n'.join(out) if out else 'OK: ngoac can bang, chuoi trich dan dong day du'
print(txt)
if len(sys.argv) > 2:
    io.open(sys.argv[2], 'w', encoding='utf-8').write(txt + '\n')
sys.exit(1 if out else 0)
