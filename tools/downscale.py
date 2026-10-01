# -*- coding: utf-8 -*-
"""Thu nho anh trang (mac dinh 50%) cho OCR nhanh hon.

usage: python downscale.py <indir> [outdir] [scale]
   outdir mac dinh: <indir>_h
Can: opencv-python (cv2).
"""
import os, sys
import cv2

src = sys.argv[1]
dst = sys.argv[2] if len(sys.argv) > 2 else src.rstrip('\\/') + '_h'
s = float(sys.argv[3]) if len(sys.argv) > 3 else 0.5
os.makedirs(dst, exist_ok=True)
for fn in sorted(os.listdir(src)):
    if not fn.lower().endswith('.png'):
        continue
    img = cv2.imread(os.path.join(src, fn), cv2.IMREAD_GRAYSCALE)
    h, w = img.shape[:2]
    small = cv2.resize(img, (int(w * s), int(h * s)), interpolation=cv2.INTER_AREA)
    cv2.imwrite(os.path.join(dst, fn), small, [cv2.IMWRITE_PNG_COMPRESSION, 3])
    print(fn, w, '->', small.shape[1], flush=True)
print('OUT:', dst)
