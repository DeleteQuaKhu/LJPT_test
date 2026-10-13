# tools/furi/ — Sinh furigana cho phần **Giải thích** của N2

Phần giải thích trong `N2/data_*.js` là tiếng Nhật; app hiển thị nó qua
`toRuby()` để chèn `<ruby>漢字<rt>かんじ</rt></ruby>`. Bảng đọc **không** viết
tay: nó được sinh tự động từ chính các chuỗi giải thích, nên khi sửa/thêm đề
chỉ cần chạy lại pipeline dưới đây.

## Kết quả (file chạy thật, nằm trong `N2/`)

| File | Việc |
|---|---|
| `N2/furi-dict.js` | `const FURI = {...}` — bảng `mặt_chữ -> cách_đọc` (khoá rỗng = "chặn": giữ nguyên, không chú thích) |
| `N2/furi-engine.js` | `function toRuby(text)` — khớp dài nhất (longest match) rồi bọc `<ruby>` |

`N2/index.html` nạp 2 file trên và gọi `toRuby()` cho `q.explanation`
(nút **ふりがな ON/OFF** để tắt/mở, lưu trong `localStorage["n2furi"]`).
Nếu 2 file không nạp được (vd. mở bằng `file://` bị chặn) thì giải thích vẫn
hiển thị nguyên văn — không lỗi.

## Pipeline

```powershell
cd tools\furi

# 1) Đọc cách đọc từ UniDic (fugashi) cho mọi giải thích -> dict.json
#    (cần explanations.jsonl; units_cache.json chỉ là cache token hoá)
python build_dict.py
#  -> dict.json, expected.jsonl (cặp base/rt kỳ vọng), ignored.json, rules.txt
#  -> in ra: bad occurrences / uncovered kanji / ignored groups

# 2) Đối chiếu engine Python (port trong build_dict.py) với expected.jsonl
node check.mjs                     # 1114/1114 ký tự khớp

# 3) Sinh file chạy thật vào N2/
python emit_js.py ..\..\N2         # -> N2/furi-dict.js + N2/furi-engine.js

# 4) Kiểm tra đầu-cuối: nạp asset đã ship, render lại toàn bộ giải thích
node check_repo.mjs ..\..\N2       # 0 bad block / 0 missing furigana / 0 problem
```

| File | Việc |
|---|---|
| `build_dict.py` | Token hoá UniDic → gộp cụm kanji (`想像` + `力` → `想像力`) → gán ngữ cảnh (`中` = なか/ちゅう, `日` = ひ/か …) bằng vòng lặp tự sửa; xuất `dict.json` + `expected.jsonl` |
| `mk_manual.py` | Sinh lại `manual_keys.json` / `fix.json` từ text gốc (các ca UniDic đọc sai) |
| `override.json`, `manual_keys.json`, `fix.json` | Cách đọc ghim bằng tay (`surface -> reading`, `file\|id\|offset -> reading`) |
| `ignored.json` | Nhóm **cố ý** không chú thích (từ 1 kanji đứng một mình, dạng chữ Hán giản thể UniDic không đọc được: 帰勢, 演修, 别 …) → ghi vào dict với khoá rỗng |
| `explanations.jsonl` | Toàn bộ giải thích (`file`, `id`, `text`) — đầu vào |
| `expected.jsonl` | Cặp base/rt + vị trí mà engine JS phải tạo ra — dùng để kiểm tra |
| `check.mjs` | Engine Python ↔ `expected.jsonl` |
| `check_repo.mjs` | Asset trong `N2/` ↔ `expected.jsonl` (bắt lỗi thiếu furigana / `<rt></rt>` rỗng) |

## Quy ước

* Sửa `data_*.js` (thêm đề / sửa giải thích) rồi **chạy lại 4 bước**; không sửa
  tay `furi-dict.js`.
* Kanji đứng một mình hoặc chữ Trung bị UniDic bỏ qua → thêm vào `ignored.json`
  (khoá rỗng trong dict) thay vì để `<rt></rt>` rỗng.
* Mọi ký tự kanji trong giải thích phải thuộc một trong ba loại: có furigana
  đúng, thuộc `ignored.json`, hoặc bị engine "chặn" — `check_repo.mjs` báo lỗi
  nếu còn kanji trần nào khác.

## Môi trường

* `python` + `fugashi` (UniDic) cho `build_dict.py`, `mk_manual.py`.
* `node` cho `check.mjs`, `check_repo.mjs` (không cần package ngoài).
* Ghi file bằng Python/Node (đừng `>` trong PowerShell — sẽ ra UTF-16).
