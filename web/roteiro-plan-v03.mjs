// RD Studio | Roteiro 0.3 — declarative, transactionally validated scene edits.
// Autor: Rogério Duarte. Not a second media clock, player or scripting engine.
// No eval, URL fetch, filesystem access, or arbitrary properties.

const ID='[A-Za-z][A-Za-z0-9_.-]{0,63}';
const NUM='(?:0|[1-9][0-9]*)(?:\\.[0-9]+)?';
const re=x=>new RegExp('^'+x+'$');
const VERSIONS=new Set(['rd-studio-plan-0.3']);
const finite=(x,lo,hi,what)=>{if(typeof x!=='number'||!Number.isFinite(x)||x<lo||x>hi)throw Error(`${what}: valor fora de ${lo}–${hi}`);return x;};
const obj=x=>x!==null&&typeof x==='object'&&!Array.isArray(x);
const exact=(x,keys)=>{if(!obj(x)||Object.keys(x).some(k=>!keys.includes(k)))throw Error('Campos não reconhecidos na operação');};
const clip=(s,id)=>{const c=(s.objetos_midia||[]).find(o=>o.id===id);if(!c||c.kind!=='video')throw Error('Clipe não encontrado como camada: '+id+'. Converta o clipe legado antes.');return c;};
const media=(s,id)=>{const o=(s.objetos_midia||[]).find(o=>o.id===id);if(!o)throw Error('Objeto não encontrado: '+id);return o;};
const validID=v=>{if(typeof v!=='string'||!new RegExp('^'+ID+'$').test(v))throw Error('ID inválido: '+v);return v;};
const safeText=(x,max)=>{if(typeof x!=='string'||x.length>max)throw Error('Texto inválido ou longo demais');return x;};
const trimSeconds=(s,v)=>finite(v,0,s.duracao,'Tempo');
const num=(s)=>Number(s);
const quoted=(s)=>{const v=JSON.parse(s);return safeText(v,400);};

// Studio commands can only be placed at root level. The remaining script is
// compiled by Roteiro 0.2 unchanged (the same GIL compiler as the editor).
export function splitRoteiro03(source){
 if(typeof source!=='string'||source.length>100000)throw Error('Roteiro acima do limite de 100 kB');
 const lines=source.split(/\r?\n/),first=lines.findIndex(l=>l.trim()&&!l.trim().startsWith('//'));
 if(first<0||lines[first].trim()!=='roteiro 0.3 {')throw Error('Cabeçalho esperado: roteiro 0.3 {');
 const script=lines.slice();script[first]=script[first].replace('roteiro 0.3','roteiro 0.2');
 const operations=[];let depth=0;
 for(let i=first;i<lines.length;i++){
  const raw=lines[i].trim();if(!raw||raw.startsWith('//'))continue;
  if(raw==='}') {depth--;if(depth<0)throw Error(`Linha ${i+1}: fechamento excessivo`);continue;}
  if(raw.endsWith('{')) {depth++;continue;}
  if(depth!==1){
   if(/^(clipe |transicao |audio (?:cena|voz|faixa) |texto cena )/.test(raw))throw Error(`Linha ${i+1}: diretiva de documento permitida apenas na raiz`);
   continue;
  }
  let m,op=null;
  try{
   if((m=re('clipe ('+ID+') entre ('+NUM+')s e ('+NUM+')s').exec(raw)))op={type:'clip.time',id:m[1],start:num(m[2]),end:num(m[3])};
   else if((m=re('clipe ('+ID+') quadro \\[('+NUM+'),('+NUM+'),('+NUM+'),('+NUM+')\\]').exec(raw)))op={type:'clip.frame',id:m[1],x:num(m[2]),y:num(m[3]),w:num(m[4]),h:num(m[5])};
   else if((m=re('clipe ('+ID+') audio volume ('+NUM+') entrada ('+NUM+')s saida ('+NUM+')s').exec(raw)))op={type:'clip.audio',id:m[1],volume:num(m[2]),fade_in:num(m[3]),fade_out:num(m[4])};
   else if((m=re('transicao ('+ID+') (entrada|saida) (dissolver|esquerda|direita|zoom) durante ('+NUM+')s').exec(raw)))op={type:'object.transition',id:m[1],phase:m[2],style:m[3],duration:num(m[4])};
   else if((m=re('audio cena entrada ('+NUM+')s saida ('+NUM+')s').exec(raw)))op={type:'audio.scene',fade_in:num(m[1]),fade_out:num(m[2])};
   else if((m=re('audio voz volume ('+NUM+') atraso ('+NUM+')s').exec(raw)))op={type:'audio.voice',volume:num(m[1]),delay:num(m[2])};
   else if((m=re('audio faixa ([0-9]+) inicio ('+NUM+')s volume ('+NUM+') entrada ('+NUM+')s saida ('+NUM+')s').exec(raw)))op={type:'audio.track',index:num(m[1]),start:num(m[2]),volume:num(m[3]),fade_in:num(m[4]),fade_out:num(m[5])};
   else if((m=/^texto cena (titulo|subtitulo) ("(?:[^"\\]|\\.)*")$/.exec(raw)))op={type:'scene.text',field:m[1],text:quoted(m[2])};
  }catch(e){throw Error(`Linha ${i+1}: ${e.message}`);}
  if(op){operations.push(op);script[i]='// '+raw;}
  else if(/^(clipe |transicao |audio (?:cena|voz|faixa) |texto cena )/.test(raw))throw Error(`Linha ${i+1}: diretiva de documento inválida`);
 }
 if(depth!==0)throw Error('Bloco não fechado no Roteiro 0.3');
 return {gilScript:script.join('\n'),plan:{format:'rd-studio-plan-0.3',operations}};
}

export function parseAgentPlan(raw){
 const plan=typeof raw==='string'?JSON.parse(raw):raw;
 exact(plan,['format','operations']);
 if(!VERSIONS.has(plan.format)||!Array.isArray(plan.operations)||plan.operations.length>100)throw Error('Plano 0.3 inválido ou com mais de 100 operações');
 return plan;
}

// Transition keyframes are expressed in the EXISTING motion GIL syntax and
// consumed by objectMotion() in the existing DOM/browser canvas paths.
export function transitionSource({phase,style,duration,objectDuration}){
 finite(duration,.05,5,'Duração da transição');finite(objectDuration,.5,600,'Duração do objeto');
 if(duration>objectDuration)throw Error('Transição maior que o intervalo do objeto');
 if(!['entrada','saida'].includes(phase)||!['dissolver','esquerda','direita','zoom'].includes(style))throw Error('Transição desconhecida');
 const isEnter=phase==='entrada',begin=isEnter?0:objectDuration-duration,end=begin+duration;
 const tracks=[];
 const anim=(prop,from,to)=>tracks.push(`animate media ${prop} ${JSON.stringify({keys:[[begin,from],[end,to]],ease:'smooth'})}`);
 anim('opacity',isEnter?0:1,isEnter?1:0);
 if(style==='esquerda'||style==='direita')anim('x',isEnter?(style==='esquerda'?-1:1):0,isEnter?0:(style==='esquerda'?-1:1));
 if(style==='zoom'){anim('sx',isEnter?.35:1,isEnter?1:.35);anim('sy',isEnter?.35:1,isEnter?1:.35);}
 const src=`gil timeline 0.1 {\nstage ${JSON.stringify({width:640,height:360,duration:objectDuration,background:'#000000',camera:'cam'})}\nresource camera camera {"z":15}\nresource g group {}\nobject cam camera - {}\nobject media g - {}\n${tracks.join('\n')}\n}\n`;
 return src;
}

// Creates an isolated proposal; caller explicitly confirms and copies it back.
// Does not modify the input, refer to unknown media or extend project fields.
export function previewScenePlan(scene,rawPlan,{validateMotion=()=>{}}={}){
 const plan=parseAgentPlan(rawPlan);
 if(!obj(scene)||!Array.isArray(scene.objetos_midia)&&scene.objetos_midia!==undefined)throw Error('Cena inválida');
 if(typeof scene.duracao!=='number'||!Number.isFinite(scene.duracao)||scene.duracao<.5)throw Error('Duração da cena inválida');
 const out=structuredClone(scene),changes=[];
 for(const [index,p] of plan.operations.entries()){
  try{
   if(!obj(p)||typeof p.type!=='string')throw Error('Operação inválida');
   if(p.type==='clip.time'){
    exact(p,['type','id','start','end']);const o=clip(out,validID(p.id));trimSeconds(out,p.start);trimSeconds(out,p.end);
    if(p.end-p.start<.05)throw Error('Intervalo de clipe demasiado curto');Object.assign(o,{start:p.start,end:p.end});
   }else if(p.type==='clip.frame'){
    exact(p,['type','id','x','y','w','h']);const o=clip(out,validID(p.id));
    Object.assign(o,{x:finite(p.x,-2,3,'X'),y:finite(p.y,-2,3,'Y'),w:finite(p.w,.02,2,'Largura'),h:finite(p.h,.02,2,'Altura')});
   }else if(p.type==='clip.audio'){
    exact(p,['type','id','volume','fade_in','fade_out']);const o=clip(out,validID(p.id));
    const v=finite(p.volume,0,3,'Volume'),a=finite(p.fade_in,0,5,'Fade entrada'),b=finite(p.fade_out,0,5,'Fade saída');
    if(a+b>o.end-o.start)throw Error('Fades excedem o intervalo do clipe');Object.assign(o,{audio_enabled:true,audio_volume:v,audio_fade_in:a,audio_fade_out:b});
   }else if(p.type==='object.transition'){
    exact(p,['type','id','phase','style','duration']);const o=media(out,validID(p.id));
    const src=transitionSource({...p,objectDuration:o.end-o.start});validateMotion(src);const stack=o.motion_programs||[];
    if(stack.length>=8)throw Error('Limite de oito programas GIL por objeto');o.motion_programs=[...stack,src];
   }else if(p.type==='audio.scene'){
    exact(p,['type','fade_in','fade_out']);const a=finite(p.fade_in,0,5,'Fade entrada'),b=finite(p.fade_out,0,5,'Fade saída');
    if(a+b>out.duracao)throw Error('Fades excedem a cena');out.audio??={};Object.assign(out.audio,{scene_fade_in:a,scene_fade_out:b});
   }else if(p.type==='audio.voice'){
    exact(p,['type','volume','delay']);out.audio??={};Object.assign(out.audio,{voice_volume:finite(p.volume,0,3,'Voz'),voice_delay:finite(p.delay,0,30,'Atraso')});
   }else if(p.type==='audio.track'){
    exact(p,['type','index','start','volume','fade_in','fade_out']);const idx=finite(p.index,0,19,'Faixa');
    if(!Number.isInteger(idx)||!out.audio?.tracks?.[idx]?.file)throw Error('Faixa inexistente: '+idx);
    Object.assign(out.audio.tracks[idx],{start:trimSeconds(out,p.start),volume:finite(p.volume,0,3,'Volume'),fade_in:finite(p.fade_in,0,60,'Fade entrada'),fade_out:finite(p.fade_out,0,60,'Fade saída')});
   }else if(p.type==='scene.text'){
    exact(p,['type','field','text']);if(!['titulo','subtitulo'].includes(p.field))throw Error('Campo de texto inválido');
    out[p.field]=safeText(p.text,p.field==='titulo'?250:400);
   }else throw Error('Operação não autorizada: '+p.type);
   changes.push({index,type:p.type,id:p.id??null});
  }catch(e){throw Error(`Operação ${index+1}: ${e.message}`);}
 }
 return {scene:out,changes};
}
