/* Quy ước trích các đoạn tiếng Nhật của mỗi đề — DÙNG CHUNG cho
   dump.mjs (sinh corpus texts.jsonl) và check_repo.mjs (kiểm tra bản phát hành).
   Sửa ở đây thì cả hai chạy theo, không lệch nhau.

   Một dòng corpus = {file, id, field, idx, text}:
     field = passage | question | option | translation | explanation
             | heading (tên 問題) | instruction (hướng dẫn 問題)
     id    = id câu hỏi, hoặc '@s<chỉ số section>' cho heading/instruction
     idx   = chỉ số option (0..3), -1 cho các field còn lại
   (translation là tiếng Việt nhưng có trích tiếng Nhật trong ngoặc -> kanji
   nào có thì thêm furigana, kanji không có thì giữ nguyên.)                 */

export const TEXT_FIELDS = ['passage', 'question', 'translation', 'explanation'];

export function textsOf(file, exam) {
  const out = [];
  (exam.data || []).forEach((sec, si) => {
    const sid = '@s' + si;
    if (sec.section) out.push({ file, id: sid, field: 'heading', idx: -1, text: sec.section });
    if (sec.instruction) out.push({ file, id: sid, field: 'instruction', idx: -1, text: sec.instruction });
    for (const q of sec.questions || []) {
      for (const k of TEXT_FIELDS) if (q[k]) out.push({ file, id: q.id, field: k, idx: -1, text: q[k] });
      (q.options || []).forEach((o, i) => {
        if (o) out.push({ file, id: q.id, field: 'option', idx: i, text: o });
      });
    }
  });
  return out;
}

export const keyOf = (r) => r.file + '|' + r.id + '|' + r.field + '|' + r.idx;
