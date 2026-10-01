# -*- coding: utf-8 -*-
"""OCR hang doi nhieu worker (chay song song an toan nho file .lock).

usage: python ocr_pages.py <indir> <outdir> <worker_name> [mobile|medium] [threads] [pages]
   indir  : thu muc anh pNN.png
   outdir : noi ghi ket qua
   pages  : "1,2,3" (mac dinh: tat ca pNN.png co trong indir)
Ket qua moi trang: pNN.txt (chi text, de doc) va pNN.tsv (x<TAB>y<TAB>score<TAB>text).

Vi du chay 5 worker song song (PowerShell):
   $env:OMP_NUM_THREADS='2'
   1..5 | ForEach-Object { Start-Process python -ArgumentList 'tools/ocr_pages.py',
       "$env:TEMP\\pg_h","$env:TEMP\\ocr","w$_",'mobile','2' -WindowStyle Hidden }
Can: paddleocr + paddlepaddle.
"""
import os, sys, time, warnings
warnings.filterwarnings('ignore')

inp = sys.argv[1]
out = sys.argv[2]
name = sys.argv[3]
mode = sys.argv[4] if len(sys.argv) > 4 else 'mobile'
threads = sys.argv[5] if len(sys.argv) > 5 else '3'
os.environ['OMP_NUM_THREADS'] = threads
from paddleocr import PaddleOCR

os.makedirs(out, exist_ok=True)
if len(sys.argv) > 6:
    order = [int(x) for x in sys.argv[6].split(',')]
else:
    order = sorted(int(fn[1:3]) for fn in os.listdir(inp)
                   if fn.startswith('p') and fn.endswith('.png'))

kw = dict(lang='japan', use_doc_orientation_classify=False, use_doc_unwarping=False,
          use_textline_orientation=False, enable_mkldnn=False)
if mode == 'mobile':                     # nhe & nhanh (chi tiet van ban)
    kw.update(ocr_version='PP-OCRv5',
              text_detection_model_name='PP-OCRv5_mobile_det',
              text_recognition_model_name='PP-OCRv5_mobile_rec')
# mode 'medium' = mac dinh cua PaddleOCR (PP-OCRv5_server_*), chinh xac hon, cham hon
ocr = PaddleOCR(**kw)


def work(i):
    src = os.path.join(inp, 'p%02d.png' % i)
    rows = []
    for r in ocr.predict(src):
        texts = r['rec_texts']
        scores = r['rec_scores']
        polys = r.get('rec_polys')
        if polys is None:
            polys = r.get('dt_polys') or []
        for k, (t, s) in enumerate(zip(texts, scores)):
            cx = cy = 0.0
            if k < len(polys):
                try:
                    p = polys[k]
                    xs = [float(q[0]) for q in p]
                    ys = [float(q[1]) for q in p]
                    cx, cy = sum(xs) / len(xs), sum(ys) / len(ys)
                except Exception:
                    pass
            rows.append((cx, cy, t, float(s)))
    with open(os.path.join(out, 'p%02d.txt' % i), 'w', encoding='utf-8') as f:
        f.write('\n'.join(r[2] for r in rows))
    with open(os.path.join(out, 'p%02d.tsv' % i), 'w', encoding='utf-8') as f:
        for cx, cy, t, s in rows:
            f.write('%.0f\t%.0f\t%.2f\t%s\n' % (cx, cy, s, t))
    print('[%s] p%02d ok -> %d' % (name, i, len(rows)), flush=True)


while True:
    got = None
    for i in order:
        dst = os.path.join(out, 'p%02d.txt' % i)
        if os.path.exists(dst) and os.path.getsize(dst) > 150:
            continue
        lock = os.path.join(out, 'p%02d.lock' % i)
        try:
            fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, b'1')
            os.close(fd)
        except FileExistsError:
            if time.time() - os.path.getmtime(lock) > 3600:
                os.remove(lock)
            continue
        got = i
        break
    if got is None:
        print('[%s] nothing left' % name, flush=True)
        break
    try:
        work(got)
    except Exception as e:
        print('[%s] ERR p%02d: %s %s' % (name, got, type(e).__name__, e), flush=True)
    try:
        os.remove(os.path.join(out, 'p%02d.lock' % got))
    except OSError:
        pass
print('[%s] EXIT' % name, flush=True)
