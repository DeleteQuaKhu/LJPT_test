/* Kiểm tra bản furigana SẼ PHÁT HÀNH: nạp N2/furi-dict.js + N2/furi-engine.js
   rồi render mọi phần "explanation" trong N2/data_*.js, đối chiếu với
   expected.jsonl (bản chuẩn do build_dict.py sinh ra).

     node check_repo.mjs <thư mục N2 của app>
*/
import fs from 'node:fs';
import path from 'node:path';

const dir = process.argv[2] || '../LJPT_test/N2';
const here = path.dirname(new URL(import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, '$1'));

/* bảng đọc + engine lấy từ chính repo (không phải bản build trong furi-work) */
const dictSrc = fs.readFileSync(path.join(dir, 'furi-dict.js'), 'utf8');
const FURI = new Function(dictSrc + '\nreturn FURI;')();
const engine = fs.readFileSync(path.join(dir, 'furi-engine.js'), 'utf8');
const { toRuby, rubify, FURI_MISS } = new Function('FURI', engine + '\nreturn {toRuby, rubify, FURI_MISS};')(FURI);

const files = fs.readdirSync(dir).filter((f) => /^data_.*\.js$/.test(f)).sort();
const exams = [];
for (const f of files) {
  const src = fs.readFileSync(path.join(dir, f), 'utf8');
  new Function('JLPT_REGISTER', src)((exam) => exams.push({ file: f, exam }));
}

const exp = new Map();
for (const l of fs.readFileSync(path.join(here, 'expected.jsonl'), 'utf8').split('\n').filter(Boolean)) {
  const e = JSON.parse(l);
  exp.set(e.file + '|' + e.id, e);
}

const pairsOf = (html) => [...html.matchAll(/<ruby>(.*?)<rt>(.*?)<\/rt><\/ruby>/g)].map((m) => [m[1], m[2]]);

/* vị trí các kanji "trần" (không có ruby) trong HTML đã render */
const KANJI_RE = /[\u3400-\u4DBF\u4E00-\u9FFF\uF900-\uFAFF]/;
function plainPositions(html) {
  const out = [];
  let pos = 0, rt = 0, ruby = 0;
  for (const tok of html.match(/<\/?[a-zA-Z]+>|[\s\S]/g) || []) {
    if (tok[0] === '<') {
      if (tok === '<ruby>') ruby++;
      else if (tok === '</ruby>') ruby--;
      else if (tok === '<rt>') rt++;
      else if (tok === '</rt>') rt--;
      continue;
    }
    if (rt === 0) {
      if (ruby === 0 && KANJI_RE.test(tok)) out.push(pos);   // không có ruby -> để trần
      pos++;
    }
  }
  return out;
}

/* tổ hợp kanji UniDic không đọc được (kanji sai / chữ Trung Quốc) -> cố ý để trần */
const ignored = JSON.parse(fs.readFileSync(path.join(here, 'ignored.json'), 'utf8'));
let expl = 0, ruby = 0, empty = 0, changed = 0, bad = 0, seenExpect = 0, plainOk = 0, plainBad = 0;
const problems = [], empties = [], leftovers = [];
for (const { file, exam } of exams) {
  for (const sec of exam.data) {
    for (const q of sec.questions || []) {
      const e = exp.get(file + '|' + q.id);
      if (q.explanation && e) {
        if (e.text !== q.explanation) { problems.push('TEXT DIFF ' + file + ' ' + q.id); continue; }
      }
      if (!q.explanation) continue;
      expl++; seenExpect += e ? 1 : 0;
      const out = toRuby(q.explanation);
      const pairs = pairsOf(out);
      ruby += pairs.length;
      empty += pairs.filter((p) => !p[1]).length;
      for (const p of pairs) if (!p[1]) {
        const at = q.explanation.indexOf(p[0]);
        empties.push(file + ' ' + q.id + '  ' + JSON.stringify(p[0]) + '  ...' +
          q.explanation.slice(Math.max(0, at - 6), at + p[0].length + 6) + '...');
      }
      if (out.replace(/<ruby>(.*?)<rt>.*?<\/rt><\/ruby>/g, '$1') !== q.explanation) changed++;
      /* kanji để trần: trong vùng "ignored" là đúng ý, ngoài vùng đó là thiếu chú thích */
      const ign = ignored.filter((g) => g.file === file && g.id === q.id);
      for (const p of plainPositions(out)) {
        const inIgn = ign.some((g) => g.start <= p && p < g.end);
        if (inIgn) plainOk++;
        else {
          plainBad++;
          if (leftovers.length < 50)
            leftovers.push(file + ' ' + q.id + '  pos=' + p + '  ' + q.explanation[p] + '  ...' +
              q.explanation.slice(Math.max(0, p - 14), p + 14) + '...');
        }
      }
      if (!e) { problems.push('no expectation ' + file + ' ' + q.id); continue; }
      const want = e.ruby.flatMap(([, base, rt]) => pairsOf(rubify(base, rt)));
      const diffs = [];
      for (let i = 0; i < Math.max(pairs.length, want.length); i++) {
        const g = pairs[i] || ['-', ''];
        const w = want[i] || ['-', ''];
        if (g[0] !== w[0] || g[1] !== w[1]) diffs.push(g.join('/') + ' != ' + w.join('/'));
      }
      if (diffs.length) { bad += diffs.length; problems.push(file + ' ' + q.id + '  ' + diffs.slice(0, 6).join('  ')); }
    }
  }
}

fs.writeFileSync(path.join(here, 'check_repo.txt'),
  'data files        : ' + files.length + '\n' +
  'dict entries      : ' + Object.keys(FURI).length + '\n' +
  'explanations      : ' + expl + ' (có bản chuẩn: ' + seenExpect + ')\n' +
  'ruby blocks       : ' + ruby + '\n' +
  'mismatching blocks: ' + bad + '\n' +
  'text changed      : ' + changed + '\n' +
  'empty readings    : ' + empty + '\n' +
  'plain kanji       : ' + plainOk + ' (đúng: tổ hợp UniDic không đọc được) \n' +
  'missing furigana  : ' + plainBad + '\n' +
  'engine FURI_MISS  : ' + new Set(FURI_MISS.map((m) => m.split('\t')[0])).size + ' ký tự\n\n' +
  '=== EMPTY READINGS (' + empties.length + ') ===\n' + empties.join('\n') + '\n\n' +
  '=== MISSING FURIGANA (' + plainBad + ') ===\n' + leftovers.join('\n') + '\n\n' +
  problems.slice(0, 200).join('\n'), 'utf8');
console.log('files: ' + files.length + '  explanations: ' + expl + '  blocks: ' + ruby +
  '  bad: ' + bad + '  textChanged: ' + changed + '  emptyRt: ' + empty +
  '  plainIgnored: ' + plainOk + '  missing: ' + plainBad + '  problems: ' + problems.length);
