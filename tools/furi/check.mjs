/* Renders every explanation with the real engine + dict and compares the
   resulting ruby sequence with the expected one from expected.jsonl. */
import fs from 'node:fs';

const FURI = JSON.parse(fs.readFileSync('dict.json', 'utf8'));
const FURI_FIX = fs.existsSync('fix_text.json')
  ? JSON.parse(fs.readFileSync('fix_text.json', 'utf8')) : {};
const engine = fs.readFileSync('furi-engine.js', 'utf8');
const { toRuby, rubify, FURI_MISS } = new Function('FURI', 'FURI_FIX', engine +
  '\nreturn {toRuby, rubify, FURI_MISS};')(FURI, FURI_FIX);

const expected = fs.readFileSync('expected.jsonl', 'utf8').split('\n').filter(Boolean).map((l) => JSON.parse(l));

const misc = [];
const pairsOf = (html) => [...html.matchAll(/<ruby>(.*?)<rt>(.*?)<\/rt><\/ruby>/g)].map((m) => [m[1], m[2]]);
let ok = 0, rubyTotal = 0, badRuby = 0, miss = 0;
for (const e of expected) {
  const out = toRuby(e.text);
  const plain = out.replace(/<ruby>(.*?)<rt>.*?<\/rt><\/ruby>/g, '$1');
  if (plain !== e.text) { misc.push({ id: e.id, why: 'TEXT CHANGED', got: plain, want: e.text }); continue; }
  const pairs = pairsOf(out);
  rubyTotal += pairs.length;
  /* the expected side is expanded the same way the engine splits a block:
     one base may hold several kanji groups (取り消 -> 取(と) 消(け)). */
  const want = e.ruby.flatMap(([, base, rt]) => pairsOf(rubify(base, rt)));
  const diffs = [];
  for (let i = 0; i < Math.max(pairs.length, want.length); i++) {
    const g = pairs[i] || ['-- none --', ''];
    const w = want[i] || ['-- none --', ''];
    if (g[0] !== w[0] || g[1] !== w[1]) diffs.push({ at: i, got: g.join('/'), want: w.join('/') });
  }
  if (diffs.length) { badRuby += diffs.length; misc.push({ id: e.id, file: e.file, text: e.text, diffs }); }
  else ok++;
}

fs.writeFileSync('check.txt',
  'explanations      : ' + expected.length + '\n' +
  'exact matches     : ' + ok + '\n' +
  'ruby blocks       : ' + rubyTotal + '\n' +
  'mismatching blocks: ' + badRuby + '\n' +
  'explanations with mismatches: ' + misc.length + '\n' +
  'uncovered kanji   : ' + new Set(FURI_MISS.map((m) => m.split('\t')[0])).size + '\n' +
  'uncovered detail  : ' + FURI_MISS.length + '\n\n' +
  misc.slice(0, 400).map((m) => JSON.stringify(m)).join('\n'), 'utf8');
fs.writeFileSync('miss.txt', [...new Set(FURI_MISS.map((m) => m.split('\t')[0] + '  |  ' + m.split('\t')[1]))].join('\n'), 'utf8');
console.log('exact: ' + ok + '/' + expected.length + '  bad blocks: ' + badRuby + '  miss: ' + new Set(FURI_MISS.map((m) => m.split('\t')[0])).size);
