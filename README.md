# LJPT_test

JLPT N2 practice quiz — a modular web app: one `index.html` (UI + logic) plus one
`data_*.js` file per exam (each self-registers through `JLPT_REGISTER()`).

## Structure

```
LJPT_test/
├── N2/
│   ├── index.html        # App shell: UI + logic (EXAM_FILES, JLPT_REGISTER)
│   ├── data_2024_07.js   # JLPT N2 — 2024年7月 (07/2024)  ← NEW
│   ├── data_2023_07.js   # JLPT N2 — 2023年7月 (07/2023)
│   ├── data_2023_12.js   # JLPT N2 — 2023年12月 (12/2023)
│   ├── data_2022_12.js   # JLPT N2 — 2022年12月 (12/2022)
│   ├── data_2022_07.js   # JLPT N2 — 2022年7月 (07/2022)
│   ├── data_2021_12.js   # JLPT N2 — 2021年12月 (12/2021)
│   ├── data_2021_07.js   # JLPT N2 — 2021年7月 (07/2021)
│   ├── data_2020_12.js   # JLPT N2 — 2020年12月 (12/2020)
│   ├── data_2019_07.js   # JLPT N2 — 2019年7月 (07/2019)
│   ├── data_2019_12.js   # JLPT N2 — 2019年12月 (12/2019)
│   ├── data_2018_07.js   # JLPT N2 — 2018年7月 (07/2018)
│   ├── furi-dict.js      # Bảng đọc furigana (sinh tự động, mọi đoạn tiếng Nhật)
│   ├── furi-fix.js       # Ngoại lệ theo đúng đoạn text (sinh tự động)
│   └── furi-engine.js    # toRuby() — bọc <ruby>
├── tools/                # Bộ công cụ tạo/kiểm tra dữ liệu (xem tools/README.md)
│   ├── extract_pdf.py    # PDF -> ảnh từng trang
│   ├── downscale.py      # thu nhỏ ảnh cho OCR
│   ├── ocr_pages.py      # OCR song song nhiều worker
│   ├── crop.ps1          # cắt & phóng to vùng ảnh để đọc bằng mắt
│   ├── brackets.py       # kiểm tra cân bằng ngoặc của data_*.js
│   ├── validate_data.py  # kiểm tra cấu trúc + đối chiếu đáp án
│   ├── furi/             # sinh furigana cho mọi đoạn tiếng Nhật (xem tools/furi/README.md)
│   └── keys/             # đáp án chuẩn (1-based) & baseline
├── pdf_data/             # Source exam PDFs (not read by the app)
└── ADD_EXAM.md           # Prompt mẫu: gõ tên đề -> thêm đề mới
```

## Usage

Open `N2/index.html` in a browser and pick an exam from the **Đề thi** dropdown.

> Some browsers block `<script src="data_*.js">` when the page is opened directly
> from disk (`file://`). If an exam shows *"chưa có dữ liệu"*, either serve the
> folder over HTTP (e.g. `python -m http.server` inside `N2/`) or use the app's
> **Nạp dữ liệu** paste panel.

## Data format

Each exam is `{ metadata, data }`:

```js
JLPT_REGISTER({
  metadata: { id:"n2_YYYY_MM", label:"MM/YYYY", title:"…", file:"data_YYYY_MM.js" },
  data: [
    { tab:"文字・語彙", section:"問題1 漢字読み", instruction:"…",
      questions:[ { id:"…", passage:"", audioUrl:"", question:"…",
                    options:["…","…","…","…"], answer:0,
                    translation:"…", explanation:"…" } ] }
  ]
});
```

Tabs: `文字・語彙` / `用法` / `文法` / `読解` / `聴解`.

## Furigana (toàn bộ nội dung tiếng Nhật)

App nạp `N2/furi-dict.js` (bảng đọc) + `N2/furi-fix.js` (ngoại lệ theo đoạn) +
`N2/furi-engine.js` (`toRuby()`) và chú thích kanji ở **mọi chỗ là tiếng Nhật**:
問題文 (`q.passage`), 質問 (`q.question`), 選択肢 (từng `option`), 訳
(`q.translation`), 💡 Giải thích (`q.explanation`), tên/hướng dẫn 問題
(`sec.section`, `sec.instruction`):

```js
<div class="text-slate-300">${furi(q.explanation) || "⚠️ THIẾU DỮ LIỆU TRONG FILE"}</div>
<button …><span class="jpn">${furi(opt)}</span></button>
```

* Nút **ふりがな ON/OFF** ở header để tắt/mở (lưu `localStorage["n2furi"]`).
* Kanji cố ý không chú thích (từ một kanji, dạng chữ Hán UniDic không đọc được)
  giữ nguyên trần — xem `ignored.json`.
* Bảng đọc **sinh tự động**, đừng sửa tay: `node tools/furi/dump.mjs .` →
  `python tools/furi/build_dict.py` → `node tools/furi/check.mjs` →
  `python tools/furi/emit_js.py N2` → `node tools/furi/check_repo.mjs N2`
  (chi tiết: `tools/furi/README.md`).
* Số liệu hiện tại: 8549 đoạn text, 6755 khoá, 41 884 khối `<ruby>`, 0 lỗi
  (`check_repo.mjs`: bad / missing / problem = 0).
* Nếu các file trên không nạp được (vd. `file://` bị chặn) thì nội dung vẫn hiển
  thị nguyên văn — `furi()` tự kiểm tra `typeof toRuby`.

## Adding a new exam

1. Create `N2/data_YYYY_MM.js` in the format above.
2. Add one line to `EXAM_FILES` inside `N2/index.html`.

Xem `ADD_EXAM.md` (prompt mẫu: chỉ cần gõ tên đề) và `tools/README.md` (quy trình
trích ảnh → OCR → đối chiếu 正解表 → kiểm tra bằng `validate_data.py`).

## Kiểm tra dữ liệu

```powershell
python tools\brackets.py     N2\data_2021_07.js
python tools\validate_data.py N2\data_2021_07.js tools\keys\2021_07.json
```

`exit 0` + `LOI CUNG (0)` = file hợp lệ và đáp án khớp bảng 正解表.

## Requirements

- Any modern browser — no build step, no dependencies.