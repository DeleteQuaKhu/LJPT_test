/* Dumps every Japanese text of every exam to JSONL: one line per text
   {file, id, field, idx, text} — the corpus that build_dict.py reads
   (texts.jsonl). Field convention lives in corpus-fields.mjs. */
import fs from 'node:fs';
import path from 'node:path';
import { textsOf } from './corpus-fields.mjs';

const ROOT = process.argv[2] || 'C:/Users/TechnoStar/.cline/data/workspaces/chat/LJPT_test';
const N2 = path.join(ROOT, 'N2');

const files = fs.readdirSync(N2).filter((f) => /^data_.*\.js$/.test(f)).sort();
const out = [];
for (const f of files) {
  const src = fs.readFileSync(path.join(N2, f), 'utf8');
  let exam = null;
  new Function('JLPT_REGISTER', 'window', src)((e) => { exam = e; }, {});
  if (!exam) throw new Error('no register in ' + f);
  out.push(...textsOf(f, exam));
}
fs.writeFileSync('texts.jsonl', out.map((o) => JSON.stringify(o)).join('\n'), 'utf8');

const byField = {};
for (const o of out) byField[o.field] = (byField[o.field] || 0) + 1;
console.log('texts: ' + out.length + '  chars: ' + out.reduce((a, b) => a + b.text.length, 0) +
  '  ' + JSON.stringify(byField));

