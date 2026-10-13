/* ===== FURIGANA ENGINE =====
   Sinh chú thích furigana (<ruby>) phía trên mỗi kanji, dùng bảng FURI
   (nạp trước bằng furi-dict.js). Nếu bảng chưa có thì trả về nguyên văn.
   Bản dùng trong app: N2/furi-engine.js — sinh tự động từ furi-work/. */
var KANJI_RE=/[\u3400-\u4DBF\u4E00-\u9FFF\uF900-\uFAFF\u3005]/;
var isKanji=ch=>KANJI_RE.test(ch);
var FURI_MISS=[];
var FURI_MAX=1;
if(typeof FURI!=='undefined')
  for(const k in FURI) if(k.length>FURI_MAX) FURI_MAX=k.length;

/* core: chuỗi chỉ gồm kanji/kana (kết thúc bằng kanji); rd: cách đọc của core */

function rubifyCore(core,rd){
  const segs=[];
  let buf='',t=null;
  for(const ch of core){
    const tt=isKanji(ch)?'j':'k';
    if(tt!==t){ if(buf)segs.push({t:t,text:buf}); buf=''; t=tt; }
    buf+=ch;
  }
  if(buf)segs.push({t:t,text:buf});
  let pos=0,out='';
  for(let i=0;i<segs.length;i++){
    const s=segs[i];
    if(s.t==='k'){
      if(i===0){ const idx=rd.indexOf(s.text,pos); if(idx>=0) pos=idx+s.text.length; }
      out+=s.text;
      continue;
    }
    const nx=segs[i+1];
    let r;
    if(nx&&nx.t==='k'){
      let idx=rd.indexOf(nx.text,pos);
      if(idx===pos){ const alt=rd.indexOf(nx.text,pos+1); if(alt>=0) idx=alt; }
      if(idx>=0){ r=rd.slice(pos,idx); pos=idx+nx.text.length; }
      else { r=rd.slice(pos); pos=rd.length; }
    } else { r=rd.slice(pos); pos=rd.length; }
    if(!r){ out+=s.text; continue; }        // không có cách đọc -> để trần
    out+='<ruby>'+s.text+'<rt>'+r+'</rt></ruby>';
  }
  return out;
}
function rubify(key,reading){
  let lastK=-1;
  for(let i=0;i<key.length;i++) if(isKanji(key[i])) lastK=i;
  const core=key.slice(0,lastK+1), tail=key.slice(lastK+1);
  let rd=reading;
  if(tail&&rd.endsWith(tail)) rd=rd.slice(0,rd.length-tail.length);
  return rubifyCore(core,rd)+tail;
}
function toRuby(text){
  if(text==null) return '';
  const s=String(text), n=s.length;
  if(typeof FURI==='undefined') return s;      // chưa nạp bảng đọc -> giữ nguyên
  let out='',i=0;
  while(i<n){
    let hit=null;
    const maxL=Math.min(FURI_MAX,n-i);
    for(let L=maxL;L>=1;L--){
      const cand=s.substr(i,L);
      if(FURI[cand]!==undefined){ hit=cand; break; }
    }
    if(hit){ const rd=FURI[hit]; out+=(rd?rubify(hit,rd):hit); i+=hit.length; continue; }
    const ch=s[i];
    if(isKanji(ch)) FURI_MISS.push(ch+'\t'+s.slice(Math.max(0,i-6),i+7));
    out+=ch; i++;
  }
  return out;
}
/* ===== /FURIGANA ===== */
