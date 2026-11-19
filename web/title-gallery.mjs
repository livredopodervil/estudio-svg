// M1c — new titles are native per-character GIL; older PNG titles remain editable.
// Preview, player, offline HTML and browser export use the existing image-object path.
// No additional frame compositor, clock, or media player is introduced.
import {createTitleGIL,TITLE_ENTRIES,TITLE_EXITS} from './title-gil.mjs';
import {prepare} from './gil-native.mjs';
import {parseFrame} from './scene-objects.mjs';
export const TITLE_STYLES = Object.freeze([
 {id:'editorial',label:'Editorial',motion:'enter-bottom',note:'Título amplo com linha editorial'},
 {id:'lower',label:'Tarja inferior',motion:'enter-right',note:'Identificação / entrevista'},
 {id:'cinema',label:'Cinemático',motion:'fade',note:'Tipografia central espaçada'},
 {id:'neon',label:'Luz e neon',motion:'zoom-in',note:'Letreiro luminoso'},
 {id:'minimal',label:'Minimalista',motion:'fade',note:'Texto branco com linha fina'},
 {id:'signal',label:'Sinal digital',motion:'enter-right',note:'Painel de dados'},
 {id:'poster',label:'Cartaz',motion:'zoom-in',note:'Título forte em bloco'},
 {id:'caption',label:'Legenda',motion:'enter-bottom',note:'Texto de leitura com contraste'}
]);
export const titleStyle=id=>TITLE_STYLES.find(x=>x.id===id)||TITLE_STYLES[0];
export function wrapTitle(ctx,text,maxWidth,maxLines=3){
 const out=[];let line='';for(const word of String(text||'').trim().split(/\s+/).filter(Boolean)){
  const test=line?line+' '+word:word;
  if(line && ctx.measureText(test).width>maxWidth){out.push(line);line=word;}else line=test;
  if(out.length>=maxLines)break;
 }
 if(line && out.length<maxLines)out.push(line);
 if(out.length===maxLines && ctx.measureText(out[maxLines-1]).width>maxWidth){let x=out[maxLines-1];while(x.length>1&&ctx.measureText(x+'…').width>maxWidth)x=x.slice(0,-1);out[maxLines-1]=x+'…';}
 return out;
}
export function renderTitle(canvas,{text='EXEMPLO DE TÍTULO',subtitle='ESTÚDIO SVG',style='editorial'}={}){
 const ctx=canvas.getContext('2d');if(!ctx)throw Error('Canvas 2D indisponível.');const W=canvas.width,H=canvas.height;
 const p=titleStyle(style),s=Math.min(W/1280,H/720),cx=W/2;
 ctx.clearRect(0,0,W,H);ctx.save();ctx.scale(s,s);
 const width=W/s,height=H/s;const center=width/2;
 const primary='#f7efe1',accent='#e7bd76';
 const font=(px,weight=700,family='system-ui, sans-serif')=>`${weight} ${Math.round(px)}px ${family}`;
 const fillLines=(str,x,y,{size=66,color=primary,spacing=82,align='center',maxWidth=1050,weight=750,shadow=0}={})=>{
  ctx.font=font(size,weight);ctx.textAlign=align;ctx.textBaseline='middle';ctx.fillStyle=color;
  if(shadow){ctx.shadowColor='#000e';ctx.shadowBlur=shadow;ctx.shadowOffsetY=2;}
  const lines=wrapTitle(ctx,str,maxWidth,3);lines.forEach((line,i)=>ctx.fillText(line,x,y+(i-(lines.length-1)/2)*spacing,maxWidth));
  ctx.shadowBlur=0;ctx.shadowOffsetY=0;
 };
 const sub=(x,y,color=accent,align='center')=>{if(!subtitle)return;ctx.font=font(29,550);ctx.textAlign=align;ctx.textBaseline='middle';ctx.fillStyle=color;ctx.fillText(subtitle.slice(0,100),x,y,900);};
 if(p.id==='lower'){
  ctx.fillStyle='rgba(15,28,38,.91)';ctx.fillRect(0,height-238,width*.88,188);ctx.fillStyle='#edbb77';ctx.fillRect(0,height-238,12,188);
  fillLines(text,65,height-153,{size:56,align:'left',maxWidth:width*.78,spacing:59});sub(66,height-77,'#9ae2da','left');
 } else if(p.id==='cinema'){
  ctx.fillStyle='#fff7ea';ctx.fillRect(center-280,height*.33,560,2);
  fillLines(text,center,height*.51,{size:70,spacing:93,shadow:10,maxWidth:width*.85});sub(center,height*.72,'#f0cc9e');
  ctx.fillStyle='#fff7ea';ctx.fillRect(center-180,height*.78,360,2);
 } else if(p.id==='neon'){
  ctx.save();ctx.shadowColor='#11e3eb';ctx.shadowBlur=32;fillLines(text,center,height*.48,{size:76,color:'#bffcff',spacing:86,shadow:20});ctx.restore();sub(center,height*.68,'#ffb5d9');
 } else if(p.id==='minimal'){
  fillLines(text,center,height*.47,{size:72,spacing:88,shadow:8});ctx.fillStyle=accent;ctx.fillRect(center-86,height*.67,172,4);sub(center,height*.74);
 } else if(p.id==='signal'){
  ctx.fillStyle='rgba(15,34,46,.88)';ctx.fillRect(75,height*.33,width-150,255);ctx.strokeStyle='#6bd4cf';ctx.lineWidth=3;ctx.strokeRect(75,height*.33,width-150,255);
  ctx.fillStyle='#6bd4cf';ctx.fillRect(80,height*.33,120,8);ctx.fillRect(width-200,height*.33+247,120,8);
  fillLines(text,center,height*.47,{size:66,color:'#c9fff0',spacing:76,maxWidth:width-260});sub(center,height*.64,'#8ae2cf');
 } else if(p.id==='poster'){
  ctx.fillStyle='rgba(25,29,35,.90)';ctx.fillRect(85,height*.25,width-170,height*.56);
  ctx.fillStyle='#e9ad61';ctx.fillRect(85,height*.25,11,height*.56);
  fillLines(text,center,height*.45,{size:81,spacing:92,maxWidth:width-240,shadow:8});sub(center,height*.70);
 } else if(p.id==='caption'){
  ctx.fillStyle='rgba(5,5,8,.86)';ctx.fillRect(48,height*.73,width-96,height*.21);
  fillLines(text,center,height*.82,{size:49,spacing:57,maxWidth:width-140});
 } else {
  ctx.fillStyle='rgba(18,33,43,.82)';ctx.fillRect(65,height*.36,width-130,height*.35);
  ctx.fillStyle=accent;ctx.fillRect(65,height*.36,8,height*.35);
  fillLines(text,center,height*.49,{size:74,spacing:85,maxWidth:width-220});sub(center,height*.65);
 }
 ctx.restore();return p;
}
export function installTitleGallery({scene,dimensions,local,upload,changed,select,notify,motionSource,refresh,selected}){
 const library=document.getElementById('workspaceLibrary');if(!library)return null;
 const section=document.createElement('section');section.className='rdTitleGallery';
 section.innerHTML='<h4>Títulos GIL · caracteres independentes</h4><p class="smallNote">Cada letra tem posição e movimento na fonte GIL Timeline. Não é PNG nem vídeo intermediário. Títulos antigos continuam editáveis.</p><div class="rdTitleTiles"></div>';
 const original=library.querySelector('#objectCatalog');original.parentNode.insertBefore(section,original);
 const dialog=document.createElement('dialog');dialog.className='rdTitleDialog';dialog.setAttribute('aria-label','Criar título e texto');
 dialog.innerHTML='<div class="rdTitleHead"><b>Inserir título</b><button type="button" data-close>× Fechar</button></div><label>Texto do título<input maxlength="110" data-title value="TÍTULO DE EXEMPLO" required></label><label>Linha secundária<input maxlength="100" data-subtitle value="RD STUDIO"></label><label>Estilo<select data-style></select></label><label>Unidades de animação<select data-text-mode><option value="words">Palavras · kerning natural (recomendado)</option><option value="letters">Letras · composição experimental</option></select></label><label>Entrada GIL<select data-motion></select></label><label>Saída GIL<select data-exit></select></label><canvas data-preview width="1280" height="720" aria-label="Miniatura do título"></canvas><div class="rdTitleLive" data-live aria-label="Prévia animada GIL"></div><p class="smallNote" data-status role="status"></p><div class="rdTitleActions"><button type="button" data-close>Cancelar</button><button type="button" data-apply class="primary">Inserir na cena</button></div>';
 document.body.append(dialog);
 const text=dialog.querySelector('[data-title]'),subtitle=dialog.querySelector('[data-subtitle]'),style=dialog.querySelector('[data-style]'),motion=dialog.querySelector('[data-motion]'),exit=dialog.querySelector('[data-exit]'),textMode=dialog.querySelector('[data-text-mode]'),canvas=dialog.querySelector('[data-preview]'),live=dialog.querySelector('[data-live]'),status=dialog.querySelector('[data-status]'),apply=dialog.querySelector('[data-apply]');
 motion.replaceChildren(...TITLE_ENTRIES.map(v=>new Option(v[1],v[0])));exit.replaceChildren(...TITLE_EXITS.map(v=>new Option(v[1],v[0])));
 style.replaceChildren(...TITLE_STYLES.map(p=>new Option(p.label,p.id)));
 let busy=false,owner=null,editing=null,liveRaf=0,animation=null,stamp=0;
 const measure=(value,size)=>{const ctx=canvas.getContext('2d');ctx.font=`600 ${size}px sans-serif`;return ctx.measureText(value).width;};
 // M1R1_PORTRAIT: use actual Studio video dimensions in the GIL title generator.
 const sourceFor=d=>{const video=dimensions?.()||{};return createTitleGIL({text:text.value,subtitle:subtitle.value,style:style.value,entry:motion.value,exit:exit.value,duration:d,width:video.width||1280,height:video.height||720,measureText:measure,textMode:textMode.value});};
 const paint=()=>{
  renderTitle(canvas,{text:text.value,subtitle:subtitle.value,style:style.value});
  try{animation=prepare(sourceFor(Math.min(60,Math.max(.5,owner?.duracao||7))));stamp=performance.now();status.textContent='Prévia GIL por letra · fonte válida';}
  catch(e){animation=null;live.replaceChildren();status.textContent=e.message;}
 };
 const animate=now=>{if(!dialog.open){liveRaf=0;return;}if(animation){try{const frame=parseFrame(animation.frame((now-stamp)/1000%animation.duration),false);frame.style.cssText='width:100%;height:100%;display:block';live.replaceChildren(frame);}catch(e){status.textContent='GIL: '+e.message;animation=null;}}liveRaf=requestAnimationFrame(animate);};
 dialog.addEventListener('close',()=>{if(liveRaf)cancelAnimationFrame(liveRaf);liveRaf=0;animation=null;live.replaceChildren();});

 const open=(preset='editorial',obj=null)=>{
  if(busy)return;owner=scene();if(!owner)return notify('Abra primeiro um projeto e uma cena.',true);
  editing=obj||null;text.value=obj?.title_spec?.text??(obj?String(obj.label||'').replace(/^TÍTULO\s*\[[^\]]+\]\s*/,''):'TÍTULO DE EXEMPLO');subtitle.value=obj?.title_spec?.subtitle??(obj?'':'RD STUDIO');
  style.value=titleStyle(obj?.title_spec?.style||preset).id;motion.value=obj?.title_spec?.entry||'cascade';exit.value=obj?.title_spec?.exit||'fade';textMode.value=obj?.title_spec?.textMode||'words';
  apply.textContent=obj?'Atualizar título':'Inserir na cena';status.textContent='';paint();dialog.showModal();if(!liveRaf)liveRaf=requestAnimationFrame(animate);
 };
 for(const p of TITLE_STYLES){const b=document.createElement('button');b.type='button';b.className='rdTitleTile';b.title=p.note;b.innerHTML=`<canvas width="320" height="180"></canvas><span>${p.label}</span>`;renderTitle(b.querySelector('canvas'),{text:'TÍTULO',subtitle:'DEMONSTRAÇÃO',style:p.id});b.onclick=()=>open(p.id);section.querySelector('.rdTitleTiles').append(b);}
 for(const b of dialog.querySelectorAll('[data-close]'))b.onclick=()=>{if(!busy)dialog.close();};
 for(const el of [text,subtitle,style,motion,exit,textMode])el.addEventListener('input',paint);
 apply.onclick=async()=>{
  if(busy)return;const content=text.value.trim(),c=owner;if(!c||c!==scene())return status.textContent='A cena mudou. Reabra a janela.';
  if(!content||content.length>110)return status.textContent='Digite um título com até 110 caracteres.';
  if(!editing&&(c.objetos_midia||[]).length>=16)return status.textContent='Limite de 16 objetos por cena.';
  busy=true;apply.disabled=true;
  try{
   const t=editing?editing.start:Math.min(local(),Math.max(0,c.duracao-.1)),d=Math.min(60,Math.max(.5,c.duracao-t));
   const src=sourceFor(d),info=prepare(src);if(info.cues)throw Error('Título não deve gerar áudio GIL.');
   const hash=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(src)))).map(x=>x.toString(16).padStart(2,'0')).join('');
   if(c!==scene())throw Error('A cena mudou durante a edição.');
   if(editing?.kind==='image'&&!confirm('Converter este título PNG antigo em GIL nativa? A imagem antiga não será apagada.')){status.textContent='Conversão cancelada.';return;}
   const label='TÍTULO ['+style.value+'] '+content.slice(0,95),gil={format:'gil-timeline-0.1',origin:'gil',origin_sha256:hash,source_sha256:hash,source:src,duration:info.duration};
   const title_spec={text:content,subtitle:subtitle.value,style:style.value,entry:motion.value,exit:exit.value,textMode:textMode.value};
   if(editing){editing.kind='gil';delete editing.file;editing.gil=gil;editing.title_spec=title_spec;editing.label=label;editing.opaque=false;editing.loop=false;}
   else{const o={id:'obj_'+crypto.randomUUID().replace(/-/g,''),label,kind:'gil',gil,title_spec,x:.5,y:.5,w:1,h:1,opacity:1,start:t,end:c.duracao,offset:0,fit:'contain',loop:false,opaque:false,rotation:0,motion:'',motion_programs:[]};
    (c.objetos_midia??=[]).push(o);select(o.id);
   }
   changed();refresh();dialog.close();notify('Título GIL com letras animadas inserido. Salve o projeto.');
  }catch(e){status.textContent=e.message;}finally{busy=false;apply.disabled=false;}
 };
 return {open};
}
