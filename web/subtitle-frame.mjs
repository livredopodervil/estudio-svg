// M1L: single declarative subtitle renderer for viewport and browser export.
// Automatic timing is an estimate; explicit cue times are authoritative.
export const SUBTITLE_DEFAULTS=Object.freeze({enabled:false,mode:'karaoke',effect:'rise',position:'bottom',font_scale:1,max_words:6,text_color:'#ffffff',highlight_color:'#ffe49a',background_color:'#091627',background_opacity:.8,cues:[]});
const clamp=(n,a,b)=>Math.max(a,Math.min(b,Number.isFinite(+n)?+n:a));
const escapeXML=x=>String(x).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&apos;'}[c]));
const measureCtx=typeof document!=='undefined'?document.createElement('canvas').getContext('2d'):null;
function textWidth(text,size){if(measureCtx){measureCtx.font=`700 ${size}px Arial, sans-serif`;return measureCtx.measureText(text).width;}return [...text].reduce((n,c)=>n+(c==='W'||c==='M'?0.8:c==='i'||c==='l'?0.32:c===' '?0.33:0.54)*size,0);}
const words=s=>String(s||'').trim().split(/\s+/u).filter(Boolean);
const weight=w=>Math.min(14,Math.max(2,[...w].length))+( /[.!?…]$/.test(w)?6:/[,;:]$/.test(w)?3:0);
function config(scene){return {...SUBTITLE_DEFAULTS,...(scene?.legendas||{})};}
function autoWords(scene,duration){
 const text=scene?.audio?.voice_text||scene?.fala||'',list=words(text);
 const delay=clamp(scene?.audio?.voice_delay??0,0,30),remaining=Math.max(.05,Number(duration)-delay-.26),total=list.reduce((n,w)=>n+weight(w),0)||1;
 let offset=delay;return list.map(word=>{const span=remaining*weight(word)/total;
  const item={text:word,start:offset,end:offset+span};offset+=span;return item;});
}
const timeStamp=/^(?:(\d{1,2}):)?(\d{1,2}):(\d{2})[,.](\d{1,3})$/;
function parseStamp(s){const m=String(s).trim().match(timeStamp);if(!m)throw Error('Horário inválido: '+s);return +(+(m[1]||0)*3600+ +m[2]*60+ +m[3]+ +(m[4].padEnd(3,'0'))/1000).toFixed(3);}
/** Receives SRT, VTT or native JSON with seconds relative to scene start. */
export function parseSubtitleText(text){
 text=String(text||'');if(text.length>250000)throw Error('Arquivo de tempos muito grande');
 const cleaned=text.trim();let out=[];
 if(cleaned.startsWith('[')){
  const data=JSON.parse(cleaned);if(!Array.isArray(data))throw Error('JSON deve ser lista de tempos');out=data;
 }else{
  for(const block of cleaned.replace(/\r\n/g,'\n').split(/\n\s*\n/)){
   const lines=block.split('\n').map(s=>s.trim());
   const idx=lines.findIndex(s=>s.includes('-->'));
   if(idx<0)continue;
   const m=lines[idx].match(/((?:\d{1,2}:)?\d{1,2}:\d{2}[,.]\d{1,3})\s*-->\s*((?:\d{1,2}:)?\d{1,2}:\d{2}[,.]\d{1,3})/);
   if(!m)continue;
   out.push({start:parseStamp(m[1]),end:parseStamp(m[2]),text:lines.slice(idx+1).filter(Boolean).join(' ')});
  }
 }
 if(!out.length||out.length>800||out.some(c=>!c||typeof c!=='object'||Object.keys(c).some(k=>!['start','end','text'].includes(k))||!Number.isFinite(c.start)||!Number.isFinite(c.end)||c.start<0||c.end<=c.start||c.end>3600||typeof c.text!=='string'||!c.text.trim()||c.text.length>180))throw Error('Tempos inválidos: até 800 trechos start/end/text');
 return out.map(c=>({start:c.start,end:c.end,text:c.text.trim()})).sort((a,b)=>a.start-b.start);
}
function explicitWords(cues){return cues.flatMap(cue=>{
 if(!cue||!Number.isFinite(cue.start)||!Number.isFinite(cue.end)||cue.start<0||cue.end<=cue.start||typeof cue.text!=='string')return [];
 const all=words(cue.text),share=(cue.end-cue.start)/(all.reduce((n,w)=>n+weight(w),0)||1);
 let offset=cue.start;return all.map(w=>{const item={text:w,start:offset,end:offset+share*weight(w)};offset=item.end;return item;});
});}
export function subtitleState(scene,time,duration){
 const c=config(scene);if(!c.enabled||!(duration>0)||!Number.isFinite(time)||time<0||time>=duration)return null;
 const items=Array.isArray(c.cues)&&c.cues.length?explicitWords(c.cues):autoWords(scene,duration);
 if(!items.length)return null;
 let active=items.findIndex(w=>time>=w.start&&time<w.end);
 if(active<0){const next=items.findIndex(w=>w.start>time);const previous=next===-1?items.length-1:next-1;if(previous>=0&&time>=items[previous].end&&time<Math.min(items[previous].end+.45,(next>=0?items[next].start:Infinity)))active=previous;}
 if(active<0)return null;
 const count=c.mode==='word'?1:Math.round(clamp(c.max_words,1,10));
 const offset=c.mode==='word'?active:Math.floor(active/count)*count;
 const showing=items.slice(offset,offset+count),current=active-offset;
 const start=showing[0].start,end=showing.at(-1).end,elapsed=Math.max(0,time-start),effect=c.effect;
 const fade=clamp(elapsed/.19,0,1),ease=1-(1-fade)**3;
 return {config:c,words:showing.map(x=>x.text),active:current,start,end,
   alpha:effect==='none'?1:fade,
   dy:effect==='rise'?(1-ease)*25:effect==='slide'?(1-ease)*16:0,
   dx:effect==='slide'?(1-ease)*30:0,
   scale:effect==='pop'?.78+.22*ease:1,
   visibleCharacters:effect==='typewriter'?Math.max(1,Math.round(showing.join(' ').length*ease)):Infinity};
}
function geom(state,width,height){
 const cfg=state.config,w=clamp(width,320,1920),h=clamp(height,320,1920),scale=clamp(cfg.font_scale,.55,1.6);
 let font=Math.round(Math.min(w*.042,h*.067)*scale),maxWidth=w*.86;
 const list=state.words.map((text,index)=>({text,index}));
 const build=size=>{let lines=[[]],widths=[0];for(const item of list){
  const gap=lines.at(-1).length?size*.33:0,extent=textWidth(item.text,size)+gap;
  if(widths.at(-1)+extent>maxWidth&&lines.at(-1).length&&lines.length<2){lines.push([]);widths.push(0);}
  const last=lines.length-1;const additional=textWidth(item.text,size)+(lines[last].length?size*.33:0);lines[last].push(item);widths[last]+=additional;
 }return {lines,widths,max:Math.max(1,...widths)};};
 let arrangement=build(font);
 if(arrangement.max>maxWidth){font=Math.max(11,Math.floor(font*maxWidth/arrangement.max));arrangement=build(font);}
 const lineHeight=font*1.23,totalH=arrangement.lines.length*lineHeight,pad=font*.38;
 const centerY=cfg.position==='top'?h*.15:cfg.position==='center'?h*.50:h*.87;
 const y=Math.min(h*.95-totalH/2-pad,Math.max(h*.06+totalH/2+pad,centerY));
 const spans=[];
 arrangement.lines.forEach((line,i)=>{let x=(w-arrangement.widths[i])/2;
  for(const [j,item] of line.entries()){
   if(j)x+=font*.33;const tw=textWidth(item.text,font);
   spans.push({text:item.text,index:item.index,x,y:y-totalH/2+(i+.72)*lineHeight,width:tw,font});x+=tw;
  }
 });
 const left=Math.max(w*.04,Math.min(...spans.map(s=>s.x))-pad),right=Math.min(w*.96,Math.max(...spans.map(s=>s.x+s.width))+pad);
 return {spans,rect:{x:left,y:y-totalH/2-pad,width:Math.max(1,right-left),height:totalH+pad*2},font,w,h};
}
function layout(scene,t,d,w,h){const state=subtitleState(scene,t,d);if(!state)return null;return {...geom(state,w,h),...state};}
function palette(c,index,state){return c.mode==='karaoke'&&index===state.active?c.highlight_color:c.text_color;}
export function subtitleSVG(scene,t,d,width,height){
 const frame=layout(scene,t,d,width,height);if(!frame)return '';
 const {w,h,rect,config:cfg,spans,alpha,dy,dx,scale,visibleCharacters}=frame;
 const opacity=clamp(cfg.background_opacity,0,1),cx=w/2,cy=rect.y+rect.height/2;
 let letters=visibleCharacters;
 const text=spans.map(s=>{let str=s.text;if(Number.isFinite(letters)){str=str.slice(0,Math.max(0,letters));letters-=s.text.length+1;}
   return `<text x="${s.x}" y="${s.y}" font-family="Arial, sans-serif" font-size="${s.font}" font-weight="700" fill="${escapeXML(palette(cfg,s.index,frame))}">${escapeXML(str)}</text>`;}).join('');
 return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${w} ${h}" width="100%" height="100%" preserveAspectRatio="none" aria-hidden="true"><g opacity="${alpha}" transform="translate(${cx+dx} ${cy+dy}) scale(${scale}) translate(${-cx} ${-cy})"><rect x="${rect.x}" y="${rect.y}" width="${rect.width}" height="${rect.height}" rx="${Math.max(7,frame.font*.27)}" fill="${escapeXML(cfg.background_color)}" fill-opacity="${opacity}"/>${text}</g></svg>`;
}
export function drawSubtitle(ctx,scene,t,d,width,height){
 const frame=layout(scene,t,d,width,height);if(!frame)return;
 const {w,rect,config:cfg,spans,alpha,dy,dx,scale,visibleCharacters}=frame;
 ctx.save();try{ctx.globalAlpha=alpha;
 const cx=w/2,cy=rect.y+rect.height/2;ctx.translate(cx+dx,cy+dy);ctx.scale(scale,scale);ctx.translate(-cx,-cy);
 ctx.fillStyle=cfg.background_color;ctx.globalAlpha=alpha*clamp(cfg.background_opacity,0,1);
 const r=Math.max(7,frame.font*.27);
 ctx.beginPath();if(typeof ctx.roundRect==='function')ctx.roundRect(rect.x,rect.y,rect.width,rect.height,r);else ctx.rect(rect.x,rect.y,rect.width,rect.height);ctx.fill();
 ctx.globalAlpha=alpha;ctx.textAlign='left';ctx.textBaseline='alphabetic';ctx.font=`700 ${frame.font}px Arial, sans-serif`;
 let letters=visibleCharacters;
 for(const s of spans){let value=s.text;if(Number.isFinite(letters)){value=value.slice(0,Math.max(0,letters));letters-=s.text.length+1;}
  ctx.fillStyle=palette(cfg,s.index,frame);ctx.fillText(value,s.x,s.y);
 }
 }finally{ctx.restore();}
}
