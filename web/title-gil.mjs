// Títulos como fontes GIL Timeline 0.1. Sem PNG intermediário nem renderizador adicional.
const clamp=(n,a,b)=>Math.max(a,Math.min(b,n));
const graphemes=text=>typeof Intl!=='undefined'&&Intl.Segmenter?[...new Intl.Segmenter('pt',{granularity:'grapheme'}).segment(text)].map(x=>x.segment):Array.from(text);
export const TITLE_ENTRIES=Object.freeze([
 ['cascade','Cascata por letra'],['typewriter','Digitação progressiva'],['rise','Letras ascendentes'],
 ['fall','Letras descendentes'],['scatter','Dispersão convergente'],['zoom','Escala por letra'],
 ['wave','Onda de entrada'],['fade','Dissolução progressiva'],['none','Sem entrada']]);
export const TITLE_EXITS=Object.freeze([['fade','Dissolver letras'],['rise','Subir letras'],['scatter','Dispersar letras'],['none','Sem saída']]);
function lines(ctx,text,limit,cap=3){
 const res=[];
 for(const raw of String(text).split(/\n/)){
  let line='';for(const word of raw.split(/\s+/).filter(Boolean)){
   if(ctx.measureText(line?`${line} ${word}`:word).width>limit&&line){res.push(line);line=word;}
   else line=line?`${line} ${word}`:word;
  }if(line)res.push(line);
 }return res.slice(0,cap);
}
function clean(x){return Math.round(x*10000)/10000;}
function keys(parts){const arr=[];for(const [time,value] of parts){const t=clean(time);if(arr.length&&t<=arr.at(-1)[0]){if(t===arr.at(-1)[0])arr[arr.length-1][1]=clean(value);continue;}arr.push([t,clean(value)]);}return arr;}
// A transformação/seleção do título ocorre no objeto GIL exterior. Dentro dele,
// cada grafema é um objeto real do documento GIL e possui a própria faixa temporal.
export function createTitleGIL({text,subtitle='',style='editorial',entry='cascade',exit='fade',duration=7,width=1280,height=720,measureText,textMode='letters'}={}){
 const d=clamp(Number(duration)||7,.5,60),title=String(text||'').trim(),sub=String(subtitle||'').trim();
 if(!title||graphemes(title).length>110||graphemes(sub).length>100)throw Error('Texto do título obrigatório; limites: 110 e 100 caracteres.');
 if(!TITLE_ENTRIES.some(x=>x[0]===entry)||!TITLE_EXITS.some(x=>x[0]===exit))throw Error('Movimento desconhecido.');
 if(!['letters','words'].includes(textMode))throw Error('Agrupamento tipográfico inválido.');
 // M1R1_PORTRAIT: GIL maps pixels using height/8, not a fixed 90px unit.
 const stageWidth=Math.round(Number(width)),stageHeight=Math.round(Number(height));
 if(!Number.isFinite(stageWidth)||!Number.isFinite(stageHeight)||stageWidth<320||stageHeight<320||stageWidth>3840||stageHeight>3840)throw Error('Dimensões de título inválidas');
 const portrait=stageHeight>stageWidth,pp=stageHeight/8;
 const measure=measureText||((s,size)=>graphemes(s).length*size*.58);
 const styles={editorial:['#f7efe1','#e7bd76',70,340],lower:['#f7efe1','#9ae2da',57,570],cinema:['#fff7ea','#f0cc9e',76,320],neon:['#bffcff','#ffb5d9',73,330],minimal:['#fff7ea','#e7bd76',66,335],signal:['#c9fff0','#8ae2cf',64,330],poster:['#f7efe1','#e9ad61',79,315],caption:['#fff7ea','#e7bd76',53,580]};
 const [foreground,secondary,fontSize,yCenter]=styles[style]||styles.editorial;
 const titleCenter=portrait?Math.round(stageHeight*.21):yCenter;
 const titleLimit=portrait?Math.round(stageWidth*.84):1110;
 const titleCap=portrait?4:3;
 // Scale only new portrait titles. Legacy 16:9 programs retain original geometry.
 let titleSize=portrait?Math.min(138,Math.round(fontSize*1.66)):fontSize;
 if(portrait){
  const norm=s=>String(s).replace(/\s+/g,' ').trim();
  while(titleSize>=60){
   const ctx={measureText:s=>({width:measure(s,titleSize)})};
   const arranged=lines(ctx,title,titleLimit,titleCap);
   if(norm(arranged.join(' '))===norm(title)&&arranged.every(x=>measure(x,titleSize)<=titleLimit))break;
   titleSize-=6;
  }
  if(titleSize<60)throw Error('Título longo para área vertical; divida em dois cartões ou reduza o texto.');
 }
 const portraitTitleLines=portrait?lines({measureText:s=>({width:measure(s,titleSize)})},title,titleLimit,titleCap).length:1;
 const resources=['resource camera camera {"z":15,"fov":45}'];const objects=['object cam camera - {}'];const tracks=[];
 const unique=new Map();const glyphs=[];
 const safeLines=(s,size,max,cap)=>{const m={measureText:v=>({width:measure(v,size)})};return lines(m,s,max,cap);};
 function put(str,size,paint,y,spacing,limit,layer){
  const arranged=safeLines(str,size,limit,portrait?4:3),all=arranged.reduce((n,line)=>n+graphemes(line).length,0);let position=0;
  for(let li=0;li<arranged.length;li++){
   // M1R2_SHAPED_TEXT: measure the *whole shaped prefix*, not each isolated glyph.
   // Word mode keeps ligatures/kerning inside each real SVG <text> node.
   // Letters mode preserves older per-character timelines, with prefix advances.
   const value=arranged[li],segments=textMode==='words'?(value.match(/\s+|\S+/gu)||[]):graphemes(value);
   const length=measure(value,size);let prefix='';
   for(const ch of segments){
    const left=measure(prefix,size);prefix+=ch;const right=measure(prefix,size);
    if(!ch.trim())continue;
    let id=unique.get(paint+'\0'+size+'\0'+ch);if(!id){id='glyph_res_'+unique.size;unique.set(paint+'\0'+size+'\0'+ch,id);resources.push(`resource ${id} text ${JSON.stringify({text:ch,fontSize:size,color:paint,layer})}`);}
    const x=clean((-length/2+(left+right)/2)/pp),yy=clean((stageHeight/2-(y+(li-(arranged.length-1)/2)*spacing))/pp),name='letter_'+glyphs.length;
    objects.push(`object ${name} ${id} - ${JSON.stringify({x,y:yy,opacity:entry==='none'?1:0})}`);
    glyphs.push({id:name,x,y:yy,index:position++,total:Math.max(1,all),layer});
   }
  }
 }
 put(title,titleSize,foreground,titleCenter,Math.round(titleSize*1.12),titleLimit,5);
 if(sub&&style!=='caption'){
  const secondarySize=portrait?Math.min(52,Math.round(titleSize*.52)):Math.min(34,fontSize*.49);
  const subtitleY=portrait?titleCenter+portraitTitleLines*titleSize*.75+75:(style==='lower'?645:yCenter+125);
  if(portrait&&subtitleY>stageHeight*.70)throw Error('Subtítulo invade a zona reservada às legendas.');
  put(sub,secondarySize,secondary,subtitleY,Math.round(secondarySize*1.12),titleLimit,6);
 }
 if(!glyphs.length)throw Error('O título não possui caracteres visíveis.');
 if(resources.length>128||glyphs.length>240)throw Error('Título ultrapassou os recursos do GIL. Divida o texto em dois objetos.');
 for(const g of glyphs){
  const t=Math.min(d*.40,g.index*.055),span=Math.min(.48,Math.max(.1,d*.18)),finish=Math.min(d*.65,t+span);
  const exitStart=Math.max(finish+.01,d-Math.min(1.1,d*.25)),end=Math.max(exitStart+.01,d);
  const values=[ [0,entry==='none'?1:0] ];if(entry!=='none')values.push([Math.max(.0001,t),0],[finish,1]);
  if(exit!=='none')values.push([exitStart,1],[end,0]);
  if(values.length>1)tracks.push(`animate ${g.id} opacity ${JSON.stringify({keys:keys(values),ease:'smooth'})}`);
  const effects=[];
  const startOffset=entry==='rise'?-1.1:entry==='fall'?1.1:entry==='scatter'?(g.index%2?1.7:-1.7):entry==='wave'?-.7:0;
  const sx=entry==='zoom'?.12:1;
  if(startOffset!==0){const v=keys([[0,g.y+startOffset],[Math.max(.0001,t),g.y+startOffset],[finish,g.y],...(exit==='rise'?[[exitStart,g.y],[end,g.y+1.1]]:[])]);effects.push(['y',v]);}
  else if(exit==='rise')effects.push(['y',keys([[0,g.y],[exitStart,g.y],[end,g.y+1.1]])]);
  if(entry==='scatter'||exit==='scatter'){
   const offset=g.index%2?2.2:-2.2;
   effects.push(['x',keys([[0,g.x+(entry==='scatter'?offset:0)],[Math.max(.0001,t),g.x+(entry==='scatter'?offset:0)],[finish,g.x],...(exit==='scatter'?[[exitStart,g.x],[end,g.x+offset]]:[])])]);
  }
  if(sx!==1){for(const prop of ['sx','sy'])effects.push([prop,keys([[0,sx],[Math.max(.0001,t),sx],[finish,1]])]);}
  for(const [prop,frame] of effects)if(frame.length>=2)tracks.push(`animate ${g.id} ${prop} ${JSON.stringify({keys:frame,ease:'smooth'})}`);
 }
 if(tracks.length>1024)throw Error('Excesso de faixas GIL. Reduza o título.');
 return `gil timeline 0.1 {\nstage ${JSON.stringify({width:stageWidth,height:stageHeight,duration:d,background:'#000000',camera:'cam'})}\n${resources.join('\n')}\n${objects.join('\n')}\n${tracks.join('\n')}\n}\n`;
}
