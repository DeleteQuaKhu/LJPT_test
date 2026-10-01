# tools/ — Bộ công cụ tạo & kiểm tra dữ liệu đề thi

Dùng khi thêm một đề JLPT N2 mới vào `N2/data_YYYY_MM.js` từ PDF scan trong `pdf_data/`.

| File | Việc |
|---|---|
| `extract_pdf.py` | Trích ảnh từng trang PDF (độ phân giải gốc) → `pNN.png` |
| `downscale.py` | Thu nhỏ ảnh (mặc định 50%) để OCR nhanh hơn |
| `ocr_pages.py` | OCR một trang/1 process; chạy nhiều worker song song an toàn (file `.lock`) |
| `crop.ps1` | Cắt & phóng to một vùng của trang scan để **đọc bằng mắt** (xác minh OCR / đọc bảng 正解表) |
| `brackets.py` | Kiểm tra cân bằng ngoặc `{}`/`[]` và chuỗi trích dẫn của file `data_*.js` |
| `validate_data.py` | Kiểm tra cấu trúc + **đối chiếu đáp án** với file key (1-based) |
| `keys/2021_07.json` | Đáp án chuẩn đọc từ bảng 正解表 của `pdf_data/2021_7.pdf` |
| `keys/*.snapshot.json` | Baseline sinh từ chính file data cũ (để sau này phát hiện thay đổi ngoài ý muốn) |

## Quy trình chuẩn

```powershell
# 1) PDF -> ảnh trang (thư mục tạm)
python tools/extract_pdf.py pdf_data\2024_7.pdf "$env:TEMP\pg"
python tools/downscale.py   "$env:TEMP\pg" "$env:TEMP\pg_h" 0.5

# 2) OCR song song 5 worker (mobile = PP-OCRv5_mobile_*)
$env:OMP_NUM_THREADS='2'
1..5 | ForEach-Object { Start-Process python -ArgumentList 'tools/ocr_pages.py',
        "$env:TEMP\pg_h", "$env:TEMP\ocr", "w$_", 'mobile', '2' -WindowStyle Hidden }
#   -> "$env:TEMP\ocr\pNN.txt" (text) và "pNN.tsv" (toạ độ + độ tin cậy)

# 3) Đọc vùng khó bằng mắt (y0 y1 x0 x1 scale)
powershell -File tools\crop.ps1 "$env:TEMP\pg\p17.png" 800 1200 120 2280 2.0

# 4) Kiểm tra file dữ liệu vừa soạn
python tools/brackets.py     N2\data_2024_07.js
python tools/validate_data.py N2\data_2024_07.js tools\keys\2024_07.json
```

`validate_data.py` trả về **exit 0** khi không có lỗi cứng; in ra danh sách
`LOI CUNG` (syntax / lệch đáp án / id trùng / sai số lựa chọn / thiếu `question`)
và `CANH BAO` (thiếu `passage`/`translation`/`explanation`).
Thêm `--snapshot out.json` để ghi lại đáp án hiện có, `--report out.txt` để lưu kết quả.

## Quy ước tên

* PDF nguồn: `pdf_data/<YYYY>_<M>.pdf` — tháng **không** có số 0 đầu (`2021_7.pdf`, `2023_12.pdf`).
* File dữ liệu: `N2/data_<YYYY>_<MM>.js` — tháng **có** số 0 đầu (`data_2021_07.js`).
* `metadata.label = "MM/YYYY"`, `metadata.id = "n2_<YYYY>_<MM>"`.

## Trạng thái (chạy `validate_data.py` ngày 01/10/2026)

| Đề | Section | Câu | Lỗi cứng | Ghi chú |
|---|---|---|---|---|
| 2021_07 | 19 | 102 | **0** | Đủ 100%: có 問題11 (9 câu) + toàn bộ 聴解; đáp án đã đối chiếu 正解表 |
| 2021_12 | 19 | 101 | 0 | |
| 2022_07 | 19 | 101 | 17 | thiếu `answer` ở 聴解問題3/4/5 |
| 2022_12 | 19 | 101 | 3 | thiếu `answer` ở 聴解問題5 |
| 2023_07 | 19 | 96 | 3 | thiếu `answer` ở 聴解問題5; thiếu câu |
| 2023_12 | 19 | 100 | 2 | thiếu `answer` ở 聴解問題5 |
| 2020_12 | 19 | 102 | **0** | Đủ 100%: có 問題11 (9 câu) + toàn bộ 聴解 (問題5 = 3 câu); đáp án đã đối chiếu 正解表 |
| 2019_07 | 19 | 103 | **0** | Đủ 100%: 問題11 (9 câu); 聴解問題2 = 5 câu, 問題5 = 4 câu; đáp án đã đối chiếu 正解表 (& 详解) |
| 2018_07 | 19 | 105 | **0** | Đủ 100%: 問題11 (9 câu); 聴解問題2 = 5 câu, 問題4 = 11 câu, 問題5 = 4 câu (3番 có 2 質問); đáp án đã đối chiếu 正解表 (& 详解) |

## Môi trường

* `esprima` nằm trong `C:\ProgramData\Lib` (script tự thêm vào `sys.path`).
* OCR cần `pymupdf`, `opencv-python`, `paddleocr` + `paddlepaddle`.
  ⚠️ Đừng cài bằng `pip install --target C:\ProgramData\Lib ...` khi thư mục đó đang
  dùng chung — pip sẽ **xoá** các package khác trong đó (đã từng làm mất paddleocr/cv2).
