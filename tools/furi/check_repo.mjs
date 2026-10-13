/* Kiểm tra bản furigana SẼ PHÁT HÀNH: nạp N2/furi-dict.js + N2/furi-engine.js
   rồi render MỌI đoạn tiếng Nhật của N2/data_*.js (theo đúng quy ước ở
   corpus-fields.mjs: passage / question / option / translation / explanation /
   heading / instruction), đối chiếu với expected.jsonl (bản chuẩn do
   build_dict.py sinh ra).

     node check_repo.mjs <thư mục N2 của app>
*/
import fs from 'node:fs';
import path from 'node:path';
import { textsOf, keyOf } from './corpus-fields.mjs';

const dir = process.argv[2] || '../LJPT_test/N2';
const here = path.dirname(new URL(import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, '$1'));

/* bảng đọc + ngoại lệ + engine lấy từ chính repo (không phải bản build trong furi-work) */
const dictSrc = fs.readFileSync(path.join(dir, 'furi-dict.js'), 'utf8');
const FURI = new Function(dictSrc + '\nreturn FURI;')();
const fixSrc = fs.readFileSync(path.join(dir, 'furi-fix.js'), 'utf8');
const FURI_FIX = new Function(fixSrc + '\nreturn FURI_FIX;')();
const engine = fs.readFileSync(path.join(dir, 'furi-engine.js'), 'utf8');
const { toRuby, rubify, FURI_MISS } = new Function('FURI', 'FURI_FIX', engine +
  '\nreturn {toRuby, rubify, FURI_MISS};')(FURI, FURI_FIX);

const files = fs.readdirSync(dir).filter((f) => /^data_.*\.js$/.test(f)).sort();
const texts = [];
for (const f of files) {
  const src = fs.readFileSync(path.join(dir, f), 'utf8');
  new Function('JLPT_REGISTER', src)((exam) => texts.push(...textsOf(f, exam)));
}

const exp = new Map();
for (const l of fs.readFileSync(path.join(here, 'expected.jsonl'), 'utf8').split('\n').filter(Boolean)) {
  const e = JSON.parse(l);
  exp.set(e.file + '|' + e.id + '|' + e.field + '|' + e.idx, e);
}

/* ngoại lệ phải khớp đúng đoạn text (nếu data_*.js đổi thì entry thành vô nghĩa) */
const fixIssues = [];
for (const [t, m] of Object.entries(FURI_FIX)) {
  for (const [k, v] of Object.entries(m)) {
    if (t.substr(+k, String(v[0]).length) !== v[0]) {
      fixIssues.push('FIX LỆCH TEXT @' + k + ' ' + JSON.stringify(v[0]) + ' trong ' + JSON.stringify(t.slice(0, 40)));
    }
  }
}

const pairsOf = (html) => [...html.matchAll(/<ruby>(.*?)<rt>(.*?)<\/rt><\/ruby>/g)].map((m) => [m[1], m[2]]);

/* vị trí các kanji "trần" (không có ruby) trong HTML đã render.
   Engine chỉ sinh thêm 4 thẻ ruby/rt; mọi thứ khác (kể cả "<br>" có sẵn trong
   đề) đều là ký tự của đoạn text -> phải đếm để vị trí khớp với text gốc. */
const KANJI_RE = /[\u3400-\u4DBF\u4E00-\u9FFF\uF900-\uFAFF]/;
function plainPositions(html) {
  const out = [];
  let pos = 0, rt = 0, ruby = 0;
  for (const tok of html.match(/<ruby>|<\/ruby>|<rt>|<\/rt>|[\s\S]/g) || []) {
    if (tok === '<ruby>') { ruby++; continue; }
    if (tok === '</ruby>') { ruby--; continue; }
    if (tok === '<rt>') { rt++; continue; }
    if (tok === '</rt>') { rt--; continue; }
    if (rt === 0) {
      if (ruby === 0 && KANJI_RE.test(tok)) out.push(pos);   // không có ruby -> để trần
      pos++;
    }
  }
  return out;
}

/* tổ hợp kanji UniDic không đọc được (kanji sai / chữ Trung Quốc) -> cố ý để trần */
const ignored = JSON.parse(fs.readFileSync(path.join(here, 'ignored.json'), 'utf8'));
let ruby = 0, empty = 0, changed = 0, bad = 0, seenExpect = 0, plainOk = 0, plainBad = 0;
const problems = [], empties = [], leftovers = [];
const byField = new Map();
for (const t of texts) {
  const k = keyOf(t);
  const st = byField.get(t.field) || { n: 0, ruby: 0, bad: 0, missing: 0, plainOk: 0 };
  byField.set(t.field, st);
  st.n++;
  const e = exp.get(k);
  if (!e) { problems.push('no expectation ' + k); continue; }
  if (e.text !== t.text) { problems.push('TEXT DIFF ' + k); continue; }
  seenExpect++;
  const out = toRuby(t.text);
  const pairs = pairsOf(out);
  ruby += pairs.length; st.ruby += pairs.length;
  for (const p of pairs) if (!p[1]) {
    empty++;
    const at = t.text.indexOf(p[0]);
    empties.push(k + '  ' + JSON.stringify(p[0]) + '  ...' +
      t.text.slice(Math.max(0, at - 6), at + p[0].length + 6) + '...');
  }
  if (out.replace(/<ruby>(.*?)<rt>.*?<\/rt><\/ruby>/g, '$1') !== t.text) changed++;
  /* kanji để trần: trong vùng "ignored" là đúng ý, ngoài vùng đó là thiếu chú thích */
  const ign = ignored.filter((g) => g.file === t.file && g.id === t.id &&
    g.field === t.field && g.idx === t.idx);
  for (const p of plainPositions(out)) {
    if (ign.some((g) => g.start <= p && p < g.end)) { plainOk++; st.plainOk++; }
    else {
      plainBad++; st.missing++;
      if (leftovers.length < 60)
        leftovers.push(k + '  pos=' + p + '  ' + t.text[p] + '  ...' +
          t.text.slice(Math.max(0, p - 14), p + 14) + '...');
    }
  }
  const want = e.ruby.flatMap(([, base, rt]) => pairsOf(rubify(base, rt)));
  const diffs = [];
  for (let i = 0; i < Math.max(pairs.length, want.length); i++) {
    const g = pairs[i] || ['-', ''];
    const w = want[i] || ['-', ''];
    if (g[0] !== w[0] || g[1] !== w[1]) diffs.push(g.join('/') + ' != ' + w.join('/'));
  }
  if (diffs.length) {
    bad += diffs.length; st.bad += diffs.length;
    problems.push(k + '  ' + diffs.slice(0, 6).join('  '));
  }
}

const fieldLines = [...byField].sort().map(([f, s]) =>
  '  ' + f.padEnd(12) + String(s.n).padStart(5) + String(s.ruby).padStart(8) +
  String(s.bad).padStart(7) + String(s.missing).padStart(6) + String(s.plainOk).padStart(7));

fs.writeFileSync(path.join(here, 'check_repo.txt'),
  'data files        : ' + files.length + '\n' +
  'dict entries      : ' + Object.keys(FURI).length + '\n' +
  'exception texts   : ' + Object.keys(FURI_FIX).length +
  ' (' + Object.values(FURI_FIX).reduce((a, m) => a + Object.keys(m).length, 0) + ' vị trí)\n' +
  'texts             : ' + texts.length + ' (có bản chuẩn: ' + seenExpect + ')\n' +
  'ruby blocks       : ' + ruby + '\n' +
  'mismatching blocks: ' + bad + '\n' +
  'text changed      : ' + changed + '\n' +
  'empty readings    : ' + empty + '\n' +
  'plain kanji       : ' + plainOk + ' (đúng: tổ hợp UniDic không đọc được)\n' +
  'missing furigana  : ' + plainBad + '\n' +
  'engine FURI_MISS  : ' + new Set(FURI_MISS.map((m) => m.split('\t')[0])).size + ' ký tự\n' +
  'fix entries lệch  : ' + fixIssues.length + '\n\n' +
  (fixIssues.length ? '=== NGOẠI LỆ KHÔNG KHỚP TEXT ===\n' + fixIssues.join('\n') + '\n\n' : '') +
  '=== PER FIELD (texts / ruby / bad / missing / plainIgnored) ===\n' + fieldLines.join('\n') + '\n\n' +
  '=== EMPTY READINGS (' + empties.length + ') ===\n' + empties.join('\n') + '\n\n' +
  '=== MISSING FURIGANA (' + plainBad + ') ===\n' + leftovers.join('\n') + '\n\n' +
  problems.slice(0, 200).join('\n'), 'utf8');
console.log('files: ' + files.length + '  texts: ' + texts.length + '  blocks: ' + ruby +
  '  bad: ' + bad + '  textChanged: ' + changed + '  emptyRt: ' + empty +
  '  plainIgnored: ' + plainOk + '  missing: ' + plainBad + '  problems: ' +
  (problems.length + fixIssues.length));

