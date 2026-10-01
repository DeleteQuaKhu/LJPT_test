# -*- coding: utf-8 -*-
"""Trich anh tung trang tu PDF de thi (ban scan) o do phan giai goc.

usage: python extract_pdf.py <pdf> [outdir]
   outdir mac dinh: %TEMP%/jlpt_pages
Moi trang luu thanh pNN.png (NN = so trang, 2 chu so).
Can: pymupdf  (C:\\ProgramData\\Lib hoac site-packages).
"""
import os, sys
import pymupdf

src = sys.argv[1]
out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(os.environ.get('TEMP', '.'), 'jlpt_pages')
os.makedirs(out, exist_ok=True)
doc = pymupdf.open(src)
print('pages:', doc.page_count)
for i, page in enumerate(doc, 1):
    imgs = page.get_images(full=True)
    if imgs:                                   # scan: lay anh lon nhat tren trang
        best = max(imgs, key=lambda x: x[2] * x[3])
        pix = pymupdf.Pixmap(doc, best[0])
        if pix.n - pix.alpha >= 4:             # CMYK -> RGB
            pix = pymupdf.Pixmap(pymupdf.csRGB, pix)
    else:                                      # PDF text: render lai
        pix = page.get_pixmap(dpi=200)
    fn = os.path.join(out, 'p%02d.png' % i)
    pix.save(fn)
    print('p%02d %dx%d imgs=%d -> %s' % (i, pix.width, pix.height, len(imgs), os.path.basename(fn)))
print('OUT:', out)
