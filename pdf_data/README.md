# pdf_data

Thư mục chứa **file PDF đề thi gốc (nguồn)** dùng để tạo dữ liệu cho app JLPT N2.

> Đây là dữ liệu nguồn để tham chiếu — app **không** đọc trực tiếp các file trong đây.

## Quy trình thêm đề mới

1. **Upload file PDF** đề thi vào thư mục này, đặt tên theo kỳ thi, ví dụ:
   - `JLPT_N2_2024_07.pdf`
   - `JLPT_N2_2024_12.pdf`
2. **Tạo file dữ liệu** `N2/data_YYYY_MM.js` theo định dạng `JLPT_REGISTER({ metadata, data })`
   (xem hướng dẫn đầy đủ trong `README.md` ở thư mục gốc repo).
3. **Đăng ký đề** bằng cách thêm 1 dòng vào `EXAM_FILES` trong `N2/index.html`:

   ```js
   { id:"n2_2024_07", label:"07/2024", file:"data_2024_07.js" },
   ```

## Cấu trúc repo

```
LJPT_test/
├── N2/               <- app (index.html + data_*.js)
└── pdf_data/         <- (thư mục này) PDF đề thi gốc
```
