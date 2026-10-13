# tools/furi/ — Sinh furigana cho **mọi đoạn tiếng Nhật** của N2

Chỗ nào trong `N2/data_*.js` là tiếng Nhật thì app hiển thị qua `toRuby()` để
chèn `<ruby>漢字<rt>かんじ</rt></ruby>`: 問題文 (`passage`), 質問 (`question`),
選択肢 (`option`), 訳 (`translation`), 解説 (`explanation`), tên/hướng dẫn 問題
(`section`, `instruction`). Bảng đọc **không** viết tay: nó được sinh tự động
từ chính các chuỗi đó, nên khi sửa/thêm đề chỉ cần chạy lại pipeline.

## Kết quả (file chạy thật, nằm trong `N2/`)

| File | Việc |
|---|---|
| `N2/furi-dict.js` | `var FURI = {...}` — bảng `mặt_chữ -> cách_đọc` (khoá rỗng = "chặn": giữ nguyên, không chú thích) |
| `N2/furi-fix.js` | `var FURI_FIX = {...}` — ngoại lệ theo **đúng đoạn text** (19 đoạn): `{ vị_trí: [mặt_chữ, cách_đọc] }`, luôn thắng bảng đọc |
| `N2/furi-engine.js` | `function toRuby(text)` — khớp dài nhất (longest match) rồi bọc `<ruby>`, áp ngoại lệ trước |

`N2/index.html` nạp 3 file trên và gọi `furi()` cho `sec.section`,
`sec.instruction`, `q.passage`, `q.question`, từng `option`, `q.translation`,
`q.explanation` (nút **ふりがな ON/OFF** để tắt/mở, lưu `localStorage["n2furi"]`).
Nếu 3 file không nạp được (vd. mở bằng `file://` bị chặn) thì nội dung vẫn hiển
thị nguyên văn — không lỗi.

## Pipeline

```powershell
cd tools\furi

# 0) Trích mọi đoạn tiếng Nhật của app -> texts.jsonl
#    (quy ước field nằm ở corpus-fields.mjs, dùng chung với check_repo.mjs)
node dump.mjs ..\..\                 # -> texts.jsonl

# 1) Sinh lại các ca ghim tay từ text gốc (UniDic đọc sai)
python mk_manual.py                  # -> manual_keys.json, fix.json

# 2) Đọc cách đọc từ UniDic (fugashi) -> bảng đọc
python build_dict.py                 # -> dict.json, expected.jsonl, ignored.json,
                                     #    fix_text.json, rules.txt
#    in ra: bad occurrences / uncovered kanji / ignored groups / số ngoại lệ

# 3) Đối chiếu engine (port Python trong build_dict.py) với expected.jsonl
node check.mjs                       # 8549/8549 đoạn khớp

# 4) Sinh file chạy thật vào N2/
python emit_js.py ..\..\N2           # -> N2/furi-dict.js, furi-fix.js, furi-engine.js

# 5) Kiểm tra đầu-cuối: nạp asset đã ship, render lại toàn bộ đoạn tiếng Nhật
node check_repo.mjs ..\..\N2         # 0 bad block / 0 missing furigana / 0 problem
```

| File | Việc |
|---|---|
| `corpus-fields.mjs` | Quy ước `{file, id, field, idx, text}` — dùng chung cho `dump.mjs` và `check_repo.mjs` |
| `dump.mjs` | Sinh `texts.jsonl` (passage / question / option / translation / explanation / heading / instruction) |
| `build_dict.py` | Token hoá UniDic → gộp cụm kanji (`想像` + `力` → `想像力`, chỉ gộp khi token sau là 名詞/接尾辞) → gán ngữ cảnh (`中` = なか/ちゅう, `日` = ひ/か …) bằng vòng lặp tự sửa → ghim ngoại lệ còn lại; xuất `dict.json` + `expected.jsonl` |
| `mk_manual.py` | Sinh lại `manual_keys.json` / `fix.json` từ text gốc (các ca UniDic đọc sai) |
| `override.json`, `manual_keys.json`, `fix.json` | Cách đọc ghim bằng tay (`surface -> reading`, `file\|id\|field\|idx\|offset -> reading`) |
| `read_fix.json` | `[regex, reading, target]` — sửa cách đọc UniDic theo ngữ cảnh (この間 → あいだ, 10月 → がつ, 他の → ほか …); `target` = bỏ trống (cụm kanji cuối) / số (vị trí trong đoạn khớp) / regex con |
| `ignored.json` | Nhóm **cố ý** không chú thích (từ 1 kanji đứng một mình, dạng chữ Hán UniDic không đọc được: 帰勢, 演修, 别 …) → ghi vào dict với khoá rỗng |
| `fix_text.json` | Ngoại lệ theo đoạn text (đã soát tay) cho các câu mà bảng đọc **không thể** phân biệt: cùng ngữ cảnh nhưng khác cách đọc, hoặc bị khoá của câu khác "cướp" chỗ (vd. お出かけ後の変更 = ご, 作り方 = かた) |
| `texts.jsonl` | Toàn bộ đoạn tiếng Nhật (`file`, `id`, `field`, `idx`, `text`) — đầu vào, sinh lại bằng `dump.mjs` |
| `expected.jsonl` | Cặp base/rt + vị trí mà engine JS phải tạo ra — dùng để kiểm tra |
| `check.mjs` | Engine Python ↔ `expected.jsonl` |
| `check_repo.mjs` | Asset trong `N2/` ↔ `expected.jsonl` (bắt lỗi thiếu furigana / `<rt></rt>` rỗng / ngoại lệ không còn khớp text) |

## Quy ước

* Sửa `data_*.js` (thêm đề / sửa câu) rồi **chạy lại pipeline**; không sửa tay
  `furi-dict.js` / `furi-fix.js`.
* UniDic đọc sai trong ngữ cảnh → thêm dòng vào `read_fix.json` (kèm `target`).
* Kanji đứng một mình hoặc chữ Trung bị UniDic bỏ qua → nằm trong `ignored.json`
  (khoá rỗng trong dict) thay vì để `<rt></rt>` rỗng.
* Câu mà bảng đọc không thể phân biệt → `build_dict.py` tự ghim vào
  `fix_text.json` (in ra + ghi vào `rules.txt` mục NGOẠI LỆ…); nên đọc lại mục đó
  sau mỗi lần thêm đề để chắc cách đọc ghim là đúng.
* Mọi ký tự kanji trong corpus phải thuộc một trong ba loại: có furigana đúng,
  thuộc `ignored.json`, hoặc đã ghim trong `fix_text.json` — `check_repo.mjs`
  báo lỗi nếu còn kanji trần nào khác.

## Môi trường

* `python` + `fugashi` (UniDic) cho `build_dict.py`, `mk_manual.py`.
* `node` cho `dump.mjs`, `check.mjs`, `check_repo.mjs` (không cần package ngoài).
* Ghi file bằng Python/Node (đừng `>` trong PowerShell — sẽ ra UTF-16 và lệch mã).
* Gỡ lỗi: `python build_dict.py units data_2021_07.js c2-3 passage -1` (in token
  hoá của một đoạn), `python dbg_pat.py "この間"` (xem `read_fix.json` khớp ở đâu).
