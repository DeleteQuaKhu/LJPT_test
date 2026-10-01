# PROMPT — Thêm / cập nhật một đề JLPT N2 vào app LJPT_test

**Cách dùng:** mở chat mới với agent trong repo này, dán nguyên khối dưới đây làm
tin nhắn đầu tiên, rồi về sau chỉ cần gõ **tên đề** — ví dụ `2024_7`, `2024_12`,
`add 2024_7`, `làm đề 2024_7` — là agent tự chạy toàn bộ quy trình.

---

## 📋 DÁN KHỐI NÀY

```text
Bối cảnh: repo C:\Users\TechnoStar\Documents\macro\LJPT_test — app web tĩnh luyện
thi JLPT N2 (N2/index.html + mỗi đề một file N2/data_<YYYY>_<MM>.js tự đăng ký qua
JLPT_REGISTER). Đề gần nhất đã làm: 2021_07 (19 section, 102 câu, đáp án đã đối
chiếu bảng 正解表). Đã có sẵn bộ công cụ trong tools/ (xem tools/README.md).

QUY TẮC CHUNG
- Tôi có thể gõ tên đề dạng 2024_7 / 2024_12 / "add 2024_7" -> đó là yêu cầu thêm đề.
- Đừng hỏi lại nếu đã đủ dữ liệu; cứ làm và báo cáo. Chỉ hỏi khi thiếu PDF nguồn
  hoặc phần cần xác nhận bằng mắt mà không tự quyết được.
- Tuyệt đối không bịa đáp án. Mọi đáp án phải lấy từ bảng 正解表 của chính file đề
  (đối chiếu chéo với trang 解説 nếu file có). Nếu không tìm được 正解表 -> DỪNG, báo tôi.
- Luôn suy nghĩ/tìm kiếm/làm song song khi độc lập; đọc ảnh bằng mắt khi OCR mơ hồ.

QUY ƯỚC
- PDF nguồn: pdf_data\<YYYY>_<M>.pdf  (tháng KHÔNG có số 0 đầu: 2021_7.pdf)
- File dữ liệu: N2\data_<YYYY>_<MM>.js (tháng CÓ số 0 đầu), metadata
  { id:"n2_<YYYY>_<MM>", label:"MM/YYYY", title:"JLPT N2 — <YYYY>年<M>月 (MM/YYYY)",
    file:"data_<YYYY>_<MM>.js" }
- Tab: 文字・語彙 / 用法 / 文法 / 読解 / 聴解. Section: 19 section (問題1..14 + 聴解問題1..5)
  theo đúng tên trong các file data_*.js hiện có (ví dụ "問題8 文の文法2 (sắp xếp - ★)",
  "問題9 文章の文法 (điền vào đoạn văn)", "問題12 統合理解 (đối chiếu 2 văn bản A/B)").
- Mỗi câu: { id, passage, audioUrl:"", question, options, answer, translation, explanation }
  + answer là 0-based (option 1 -> answer:0). options: 4 lựa chọn; riêng 聴解問題4 即時応答
  chỉ 3 lựa chọn. question có thẻ <u>…</u> cho từ được hỏi; câu 問題8 dùng "＿＿ ＿＿★ ＿＿ ＿＿".
  + id: a1-1..a1-5 (漢字読み), a2-* (表記), a3-* (語形成), a4-* (文脈規定), a5-* (言い換え類義),
    a6-* (用法), a7-* (文の文法1), a8-* (文の文法2), a9-* (文章の文法),
    b10-*..b14-* (読解), c1-*..c5-* (聴解). Không trùng id trong toàn file.
  + translation: dịch nghĩa tiếng Việt; explanation: giải thích vì sao chọn + vì sao các
    phương án khác sai (tiếng Việt).
  + passage: "" cho 問題1–8; điền đoạn văn cho 問題9–14 (問題11 là 1 đoạn dùng chung cho
    cả nhóm câu -> để ở câu đầu); 聴解 điền 台本 (听力原文) kèm 選択肢 vào passage từng câu.
- File lưu UTF-8 KHÔNG BOM, mỗi section đóng bằng "]},", có comment tiếng Việt như
  data_2021_07.js.

QUY TRÌNH KHI TÔI GÕ TÊN ĐỀ <YYYY>_<M>
1. Kiểm tra pdf_data\<YYYY>_<M>.pdf. Nếu thiếu -> báo tôi bỏ PDF vào (đúng tên). Nếu có
   PDF tên lạ trong pdf_data/ -> đoán theo nội dung rồi xác nhận với tôi.
2. Trích ảnh + OCR:
     python tools\extract_pdf.py pdf_data\<YYYY>_<M>.pdf "$env:TEMP\pg"
     python tools\downscale.py  "$env:TEMP\pg" "$env:TEMP\pg_h" 0.5
     $env:OMP_NUM_THREADS='2'
     1..5 | ForEach-Object { Start-Process python -ArgumentList 'tools/ocr_pages.py',
         "$env:TEMP\pg_h","$env:TEMP\ocr","w$_",'mobile','2' -WindowStyle Hidden }
   Lượt mobile để soạn nhanh; chỗ mơ hồ thì đọc bằng mắt:
     powershell -File tools\crop.ps1 "$env:TEMP\pg\pNN.png" <y0> <y1> <x0> <x1> 2.0
3. Đọc "$env:TEMP\ocr\pNN.txt": xác định trang đề, trang 正解表 (bảng số/đáp án), trang
   解説, trang 台本 聴解. Trích ĐẦY ĐỦ nội dung đề + đáp án.
4. Soạn N2\data_<YYYY>_<MM>.js theo quy ước trên (đủ 19 section; bám đúng số câu từng
   問題 in trong đề — ví dụ 2021_07 có 問題11 = 9 câu, 聴解問題4 = 11 câu).
5. Cổng kiểm tra (bắt buộc, đạt hết mới đi tiếp):
     python tools\brackets.py N2\data_<YYYY>_<MM>.js          # -> "OK: ..."
     # tạo tools\keys\<YYYY>_<MM>.json (đáp án 1-based) từ bảng 正解表, rồi:
     python tools\validate_data.py N2\data_<YYYY>_<MM>.js tools\keys\<YYYY>_<MM>.json
     # -> phải "LOI CUNG (0)" và exit 0; chưa có 正解表 thì thêm --snapshot
   Nếu lệch đáp án -> SỬA FILE DATA cho khớp 正解表 (không sửa key theo data).
6. Đăng ký đề: thêm đúng 1 dòng vào EXAM_FILES trong N2\index.html (đề mới nhất lên đầu,
   giữ định dạng) + 1 dòng <script src="data_<YYYY>_<MM>.js"> cạnh các dòng script khác;
   thêm 1 dòng vào cây thư mục trong README.md.
7. Git:
     git add <các file đã sửa>
     git commit -m "Add data_<YYYY>_<MM>.js (JLPT N2 <YYYY>-<MM>) from scanned pdf_data/<YYYY>_<M>.pdf"
     git push origin main       (remote: https://github.com/DeleteQuaKhu/LJPT_test.git)
   Không commit PDF mới vào pdf_data/ trừ khi tôi yêu cầu.
8. Báo cáo cuối: số section/câu, bảng đáp án từng 問題, các chỗ phải sửa sau khi đối chiếu
   ảnh gốc, cảnh báo (thiếu passage/translation…), và cập nhật bảng trạng thái trong
   tools/README.md.

LỖI CẦN TRÁNH (đã từng gặp)
- Thiếu "]}" / "]}," đóng section -> tìm bằng tools\brackets.py.
- Lưu file có BOM -> validator cảnh báo ngay (phải no-BOM).
- 問題11 dùng chung 1 đoạn văn: chỉ đặt passage ở câu đầu của nhóm.
- 聴解問題3/4 thường KHÔNG in options trên đề -> lấy từ 台本, ghi rõ trong instruction.
- Không cài pip bằng --target C:\ProgramData\Lib khi thư mục đó đang dùng chung
  (đã từng làm mất paddleocr/cv2).
- Nợ kỹ thuật hiện có: data_2022_07 (17), data_2022_12 (3), data_2023_07 (3),
  data_2023_12 (2) đang thiếu answer ở 聴解問題3/4/5. Nếu tôi yêu cầu "hoàn thiện đề cũ"
  thì bổ sung rồi chạy lại validator.
```

---

## Bản ngắn (khi repo đã có sẵn `tools/`)

```text
Repo LJPT_test (app JLPT N2 tĩnh). Hãy thêm đề <TÊN ĐỀ> vào N2/data_*.js theo đúng quy ước
của data_2021_07.js, dùng bộ công cụ trong tools/ (đọc tools/README.md): extract_pdf.py ->
downscale.py -> ocr_pages.py (OCR mobile song song) -> đọc bảng 正解表 trong PDF -> soạn file
-> tools/brackets.py + tools/validate_data.py phải "LOI CUNG (0)" -> thêm dòng vào EXAM_FILES
trong N2/index.html + README.md -> git commit & push. Đáp án phải khớp 正解表, không bịa;
đọc ảnh bằng mắt (tools/crop.ps1) khi OCR mơ hồ.
```

## Lưu ý

Phần **đọc đề + dịch nghĩa + giải thích từng câu** vẫn cần agent/người làm (không thể
script hoá hoàn toàn), nên hiện tại đây là quy trình hợp lý nhất. Nếu muốn, có thể viết
`tools/add_exam.py` chỉ để tự động bước 2 (trích ảnh + OCR) khi gõ một tên đề.
