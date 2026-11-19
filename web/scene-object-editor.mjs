// Editor de objetos do Estúdio, acoplado ao documento e ao transporte existentes.
import {motionSource,motionProgram,objectMotion,rect,localTime,parseFrame} from './scene-objects.mjs';
import {installGizmo} from './viewport-gizmo.mjs';
import {installInstanceManager} from './instance-manager-v1.mjs';
import {prepare} from './gil-native.mjs';
import {installTitleGallery} from './title-gallery.mjs';
import {installSvgDirect} from './svg-direct-edit.mjs';
import {installRoteiroEditor} from './roteiro-editor.mjs';
import {cropImageURL,normalizeCrop} from './object-crop.mjs';
const $=id=>document.getElementById(id),clamp=(n,a,b)=>Math.max(a,Math.min(b,n));
export function installEditor(ctx){
 const dialog=$('objectInsert'),view=$('objectInsertPreview'),status=$('objectInsertStatus'),files=$('objectFile'),tracks=$('objectTracks'),ins=$('objectInspector');
 const motionCache={source:null,eval:null};let draft=null,raf=0,url='',serial=0,owner=null,selectedId='',selectedScene=null,drag=null,loading=false,stackDraft=[];
 const scene=()=>ctx.scene(),objects=()=>scene()?.objetos_midia||[],current=()=>objects().find(o=>o.id===selectedId);
 const m1tManager=installInstanceManager(ins,{project:ctx.project,scene,selectedObject:current,changed:ctx.changed,preview:ctx.preview,notify:ctx.notify,upload:ctx.upload});

// M1S_PICKING: selection by scene order, with alpha-aware image probing.
// Screen-space probing happens only on tap, not for every animation frame.
let m1sTap=null;
const m1sProbe=document.createElement('canvas');m1sProbe.width=m1sProbe.height=1;
function m1sPaintHit(el,x,y){
 const box=el.getBoundingClientRect();
 if(!(box.width>0&&box.height>0&&x>=box.left&&x<=box.right&&y>=box.top&&y<=box.bottom))return false;
 if(el.tagName==='IMG'&&el.complete&&el.naturalWidth&&el.naturalHeight){
  try{
   const style=getComputedStyle(el),fit=style.objectFit||'fill';
   const ratio=fit==='cover'?Math.max(box.width/el.naturalWidth,box.height/el.naturalHeight):fit==='contain'?Math.min(box.width/el.naturalWidth,box.height/el.naturalHeight):null;
   let u=(x-box.left)/box.width,v=(y-box.top)/box.height;
   if(ratio!==null){const dw=el.naturalWidth*ratio,dh=el.naturalHeight*ratio;u=(x-box.left-(box.width-dw)/2)/dw;v=(y-box.top-(box.height-dh)/2)/dh;}
   if(u<0||u>1||v<0||v>1)return false;
   const pixel=m1sProbe.getContext('2d',{willReadFrequently:true});
   pixel.clearRect(0,0,1,1);
   pixel.drawImage(el,Math.max(0,Math.min(el.naturalWidth-1,Math.floor(u*el.naturalWidth))),Math.max(0,Math.min(el.naturalHeight-1,Math.floor(v*el.naturalHeight))),1,1,0,0,1,1);
   return pixel.getImageData(0,0,1,1).data[3]>=24;
  }catch{return true;} // CORS/rotation fallback: allow explicit layer cycling.
 }
 if(el.shadowRoot){
  const root=el.shadowRoot.querySelector('svg');
  const hit=el.shadowRoot.elementFromPoint?.(x,y);
  if(root&&hit===root)return false;
 }
 return true;
}
function m1sCandidates(e){
 const available=new Set(objects().filter(o=>localTime(o,ctx.local())!==null).map(o=>o.id));
 const nodes=[...$('stageShell').querySelectorAll('[data-scene-object-id]')];
 return nodes.filter(el=>available.has(el.dataset.sceneObjectId)
   &&getComputedStyle(el).display!=='none'
   &&Number(getComputedStyle(el).opacity)>.02
   &&m1sPaintHit(el,e.clientX,e.clientY))
   .sort((a,b)=>objects().findIndex(o=>o.id===b.dataset.sceneObjectId)-objects().findIndex(o=>o.id===a.dataset.sceneObjectId))
   .map(el=>el.dataset.sceneObjectId);
}
function m1sSelectBehind(){
 const ids=objects().filter(o=>localTime(o,ctx.local())!==null).map(o=>o.id);
 if(!ids.length)return ctx.notify('Sem objetos independentes nesta cena; selecione SVG na camada base.');
 const i=ids.indexOf(selectedId),next=ids[(i<=0?ids.length:i)-1];
 select(next);inspectorOpen=true;ins.hidden=false;refresh();ctx.notify('Selecionado: '+current()?.label+' · escolha por ordem de camada.');
}

 const say=s=>status.textContent=s;
 let legacyTarget=null,svgDirect=null;
 const legacyBox=$('legacyObjectSelection');
 function hideLegacy(){legacyTarget=null;legacyBox.hidden=true;svgDirect?.clear();}
 function selectLegacy(kind,id=''){
  if(!scene()||ctx.playing())return;
  if(kind==='clip'||kind==='image'||kind==='gil')ctx.activate();
  selectedId='';inspectorOpen=false;ins.hidden=true;
  const clip=scene()?.video_clipe;
  if(kind==='clip'&&!clip?.arquivo)return;
  if(kind==='image'&&!scene()?.imagem?.arquivo)return;
  if(kind!=='svg')svgDirect?.clear();
  legacyTarget={kind,id,scene:scene()};
  const label=kind==='clip'?'Clipe original':kind==='image'?'Imagem original':kind==='gil'?'GIL anterior':kind==='svg'?'Elemento SVG':'Arte base da cena';
  $('legacySelectionLabel').textContent=id?label+' · '+id:label;
  $('legacySelectionHint').textContent=kind==='image'?'Converter a imagem original em objeto independente, preservando inclusive o recorte. Depois, use Editar recorte no inspetor. A imagem original permanece salva.':kind==='clip'?'Converter permite usar gizmo, moldura e programas GIL; o clipe anterior é substituído no mesmo projeto, com desfazer disponível.':kind==='svg'?'Mantém os IDs e as animações existentes.':kind==='gil'?'Use as alças para mover/escalar; Editar fonte GIL para alterar o conteúdo.':'A arte base é uma composição da cena, não uma camada independente. Use o editor da cena.';
  for(const [button,show] of [['legacyPromoteImage',kind==='image'],['legacyPromoteClip',kind==='clip'],['legacyEditSVG',kind==='svg'&&scene().tipo==='svg'],['legacyAnimateSVG',kind==='svg'&&!!id],['legacyEditScene',kind==='scene'||(kind==='svg'&&scene().tipo!=='svg')]])$(button).hidden=!show;
  legacyBox.hidden=false;gizmo.paint();
 }
 $('legacySelectionClose').onclick=()=>{hideLegacy();svgDirect?.clear();};
 $('legacyPromoteImage').onclick=async()=>{
  if(legacyTarget?.kind!=='image'||legacyTarget.scene!==scene())return;
  const c=scene(),im=c.imagem;if(!im?.arquivo)return;
  if(objects().length>=16)return ctx.notify('Limite de 16 objetos por cena.',true);
  const crop=im.crop?.length===4?normalizeCrop(im.crop):[0,0,1,1];
  const mode=im.modo==='fundo';
  if(!confirm('Converter a imagem '+(mode?'de fundo':'da cena')+' em camada animável? Ela ficará acima da arte base; o arquivo original será preservado e a ação poderá ser desfeita.'))return;
  try{
   const original=im.arquivo;let filename=original;
   if(crop.some((v,i)=>v!==[0,0,1,1][i])){
    const blob=await cropImageURL('/api/media/image?file='+encodeURIComponent(original),crop);
    filename=await ctx.upload(new File([blob],'recorte-'+Date.now()+'.png',{type:'image/png'}),'image');
   }
   if(scene()!==c||c.imagem!==im)throw Error('Cena ou recorte alterados durante a conversão.');
   const o={id:'obj_'+crypto.randomUUID().replace(/-/g,''),label:original,kind:'image',file:filename,source_file:original,source_crop:crop,x:mode?.5:im.x,y:mode?.5:im.y,w:mode?1:im.w,h:mode?1:im.h,opacity:1,start:0,end:c.duracao,offset:0,fit:im.fit==='contain'?'contain':'cover',loop:true,rotation:0,motion:'',motion_programs:[]};
   (c.objetos_midia??=[]).push(o);c.imagem={...im,arquivo:''};hideLegacy();selectedId=o.id;inspectorOpen=true;ctx.changed();refresh();ctx.preview();ctx.notify('Recorte preservado e imagem convertida. Use alças ou Editar recorte.');
  }catch(e){ctx.notify(e.message,true);}

 };
 $('legacyPromoteClip').onclick=()=>{
  if(legacyTarget?.kind!=='clip'||legacyTarget.scene!==scene())return;
  const c=scene(),clip=c.video_clipe;
  if(!clip?.arquivo)return;
  if(objects().length>=16)return ctx.notify('Limite de 16 objetos por cena.',true);
  const o={id:'obj_'+crypto.randomUUID().replaceAll('-',''),label:clip.arquivo,kind:'video',file:clip.arquivo,x:clip.x,y:clip.y,w:clip.w,h:clip.h,opacity:clip.opacidade,start:0,end:c.duracao,offset:clip.inicio||0,fit:clip.fit,loop:clip.repetir,audio_enabled:clip.audio_enabled,audio_volume:clip.audio_volume,audio_fade_in:clip.audio_fade_in??.12,audio_fade_out:clip.audio_fade_out??.12,motion:'',motion_programs:[],rotation:0,shear:0,pivot_x:0,pivot_y:0};
  if(!confirm('Converter o clipe original em camada independente, preservando sua mídia e faixa sonora? Esta edição pode ser desfeita.'))return;
  (c.objetos_midia??=[]).push(o);c.video_clipe={...clip,arquivo:'',audio_enabled:false};
  hideLegacy();selectedId=o.id;inspectorOpen=true;ctx.changed();refresh();ctx.preview();ctx.notify('Clipe convertido em objeto animável. Salve para persistir.');
 };
 $('legacyEditSVG').onclick=()=>{if(legacyTarget?.scene===scene())ctx.editSVG?.();};
 $('legacyAnimateSVG').onclick=()=>{if(legacyTarget?.scene===scene())ctx.animateSVG?.(legacyTarget.id);};
 $('legacyEditScene').onclick=()=>{if(legacyTarget?.scene===scene())ctx.sceneProperties?.();};

 function resetDraft(){++serial;cancelAnimationFrame(raf);view.querySelector('video')?.pause();view.replaceChildren();if(url)URL.revokeObjectURL(url);url='';draft=null;$('objectConfirm').disabled=true;}
 function clear(){resetDraft();files.value='';}
 function previewGIL(source,label){clear();const info=prepare(source);if(info.duration<.5||info.duration>60)throw Error('Duração GIL: 0,5–60 s.');if(info.cues)throw Error('Composição usa áudio GIL, ainda não suportado. Escolha uma fonte silenciosa.');draft={kind:'gil',source,label,info};const start=performance.now();let last=-Infinity;const frame=now=>{if(!dialog.open||!draft)return;if(now-last<42){raf=requestAnimationFrame(frame);return;}last=now;try{const el=parseFrame(info.frame(((now-start)/1000)%info.duration),true);el.style.cssText='width:100%;height:100%;display:block';view.replaceChildren(el);raf=requestAnimationFrame(frame);}catch(e){clear();say(e.message);}};raf=requestAnimationFrame(frame);say(`${label} · ${info.duration.toFixed(2)} s · GIL nativa`);$('objectConfirm').disabled=false;}
 async function example(){clear();const token=serial;say('Carregando exemplo…');try{const r=await ctx.example($('objectExamples').value);if(token===serial&&dialog.open)previewGIL(r.source,r.name);}catch(e){if(token===serial)say(e.message);}}
 async function filePreview(file){clear();const token=serial;if(!file)return;try{if(/\.gil3$/i.test(file.name))throw Error('GIL3 ainda exige adaptador; fonte preservada.');if(/\.(gil|txt)$/i.test(file.name)){if(file.size>250000)throw Error('Fonte acima de 250 kB');const source=(await file.text()).replace(/^\uFEFF/,'');if(token===serial&&dialog.open)previewGIL(source,file.name);return;}
 const kind=file.type.startsWith('image/')||/\.(jpe?g|png|webp)$/i.test(file.name)?'image':file.type.startsWith('video/')||/\.(mp4|webm|mov|m4v|mkv|ogv)$/i.test(file.name)?'video':null;if(!kind)throw Error('Selecione imagem, vídeo ou .gil.');if(file.size<=0||file.size>(kind==='image'?12e6:250e6))throw Error('Arquivo vazio ou acima do limite de importação.');url=URL.createObjectURL(file);const el=document.createElement(kind==='video'?'video':'img');el.style.cssText='display:block;width:100%;height:100%;object-fit:contain';el.onerror=()=>{if(token===serial){draft=null;$('objectConfirm').disabled=true;say('Formato não decodificado pelo navegador.');}};const ready=()=>{if(token!==serial||!dialog.open)return;draft={kind,file,label:file.name,duration:kind==='video'?el.duration:null};say(file.name+(kind==='video'?' · '+el.duration.toFixed(2)+' s · clipe de vídeo':' · imagem'));$('objectConfirm').disabled=false;};if(kind==='video'){el.controls=true;el.playsInline=true;el.muted=false;el.preload='metadata';el.onloadedmetadata=ready;}else el.onload=ready;el.src=url;view.append(el);
 }catch(e){if(token===serial)say(e.message);}}
 function open(preferred=''){if(!scene()||loading||dialog.open)return;ctx.stop();owner=scene();clear();dialog.showModal();availableFamilies();queueMicrotask(()=>{m1sPopulate();m1sDialogState();});if(typeof preferred==='string'&&Array.from($('objectExamples').options).some(o=>o.value===preferred)){$('objectExamples').value=preferred;example();}else say('Escolha um tipo, uma mídia ou uma composição; nenhuma demonstração foi selecionada automaticamente.');}
 function openSource(source,label){if(!scene()||loading||dialog.open)return;ctx.stop();owner=scene();clear();dialog.showModal();if(new TextEncoder().encode(source).length>250000){say('Fonte acima de 250 kB');return;}try{previewGIL(source,label);}catch(e){say(e.message);}}
 // M1R2_INSERT_HUB: one insertion entrypoint, delegating to existing canonical editors.
 const insertionHub=document.createElement('section');insertionHub.className='rdInsertHub';insertionHub.setAttribute('aria-label','Todos os tipos de inserção disponíveis');
 const actions=[
  ['image','▧','Imagem / fotografia'],['video','▶','Vídeo / clipe'],
  ['svg','◇','SVG / ícones / geometria'],['title','T','Texto e título animado'],
  ['gil','◈','Composição GIL'],['gil-source','{}','Fonte GIL existente'],
  ['audio','♫','Voz / áudio da cena'],['scene3d','▣','Criar nova cena espacial 3D']
 ];
 const headline=document.createElement('p');headline.className='smallNote';headline.textContent='Selecione o conteúdo. Geometrias e estilos são parâmetros, não novos tipos de objeto.';
 const grid=document.createElement('div');grid.className='rdInsertTypes';
 for(const [id,ico,label] of actions){const b=document.createElement('button');b.type='button';b.dataset.insertKind=id;b.textContent=ico+' '+label;grid.append(b);}
 insertionHub.append(headline,grid);
 const family=document.createElement('div');family.className='rdInsertFamilies';
 const familyTitle=document.createElement('strong');familyTitle.textContent='Catálogo SVG — famílias de objetos';family.append(familyTitle);
 const familyList=document.createElement('div');familyList.className='rdInsertFamilyGrid';family.append(familyList);
 insertionHub.append(family);
 // M1S_UNIVERSAL: use the actual GIL library options rather than four fixed demos.
 const m1sSearch=document.createElement('input');m1sSearch.type='search';m1sSearch.placeholder='Buscar objeto, SVG, GIL ou efeito…';m1sSearch.setAttribute('aria-label','Buscar no seletor universal');m1sSearch.className='rdUniversalSearch';
 insertionHub.insertBefore(m1sSearch,grid);
 const m1sGil=document.createElement('details');m1sGil.className='rdUniversalGil';
 const gilSummary=document.createElement('summary');gilSummary.textContent='Composições GIL · prévia animada';m1sGil.append(gilSummary);
 const m1sGilGrid=document.createElement('div');m1sGilGrid.className='rdInsertFamilyGrid';m1sGil.append(m1sGilGrid);
 insertionHub.append(m1sGil);
 function m1sPopulate(){
  const select=$('objectExamples'),library=$('gilLibrarySelect');
  const existing=new Set([...select.options].map(o=>o.value));
  for(const original of library?.options||[]){if(existing.has(original.value))continue;const opt=document.createElement('option');opt.value=original.value;opt.textContent=original.textContent;select.append(opt);existing.add(opt.value);}
  m1sGilGrid.replaceChildren();
  for(const option of select.options){const b=document.createElement('button');b.type='button';b.dataset.m1sTitle=option.textContent;b.dataset.m1sGil=option.value;b.textContent='◈ '+option.textContent;
   b.onclick=()=>{select.value=option.value;example();};m1sGilGrid.append(b);}
  m1sFilter();
 }
 function m1sFilter(){
  const q=m1sSearch.value.toLocaleLowerCase('pt-BR').trim();
  for(const b of [...familyList.children,...m1sGilGrid.children])b.hidden=!!q&&!b.textContent.toLocaleLowerCase('pt-BR').includes(q);
  for(const b of grid.querySelectorAll('button'))b.hidden=!!q&&!b.textContent.toLocaleLowerCase('pt-BR').includes(q);
  if(q){m1sGil.open=true;family.closest('details')?.setAttribute('open','');}
 }
 m1sSearch.addEventListener('input',m1sFilter);
 const familyDetails=document.createElement('details');familyDetails.className='rdUniversalSvg';
 const familySummary=document.createElement('summary');familySummary.textContent='SVG / ícones / geometrias · prévia';familyDetails.append(familySummary);
 family.parentElement.insertBefore(familyDetails,family);familyDetails.append(family);

 const latex=document.createElement('p');latex.className='smallNote';latex.textContent='LaTeX: adaptador MathJax TeX→SVG ainda não instalado; não há conversão implícita.';insertionHub.append(latex);
 const controls=$('objectExamples').closest('.objectTools');dialog.insertBefore(insertionHub,controls);
 const closeAnd=fn=>{dialog.close();fn();};
 function availableFamilies(){familyList.replaceChildren();const cat=$('objectCatalog');for(const source of cat?.querySelectorAll('[data-library-object]')||[]){const b=document.createElement('button');b.type='button';b.textContent=source.textContent.trim();b.dataset.family=source.dataset.libraryObject;b.onclick=()=>closeAnd(()=>{$('openLibrary')?.click();source.click();});familyList.append(b);}family.hidden=!familyList.children.length;}
 grid.addEventListener('click',e=>{const id=e.target.closest('[data-insert-kind]')?.dataset.insertKind;if(!id)return;
  if(id==='image'||id==='video'){files.accept=id==='image'?'image/*,.png,.jpg,.jpeg,.webp':'video/*,.mp4,.webm,.mov,.m4v,.mkv,.ogv';files.click();return;}
  if(id==='gil'){$('objectExamples').value='native-demo';example();return;}
  if(id==='svg')return closeAnd(()=>$('openLibrary')?.click());
  if(id==='title')return closeAnd(()=>titles.open('editorial'));
  if(id==='gil-source')return closeAnd(editGil);
  if(id==='audio')return closeAnd(()=>ctx.audio?.());
  if(id==='scene3d')return closeAnd(()=>{const control=$('addSpatialScene');if(control)control.click();else ctx.notify('Cena espacial não disponível nesta configuração.',true);});
 });
 const originalOpen=open; // catalog families refresh on demand, never on every animation frame.

 // M1S_SCROLL: keep touch/wheel scroll inside the modal; never scroll the page behind it.
 const m1sDialogState=()=>document.documentElement.classList.toggle('rdObjectModalOpen',dialog.open);
 dialog.addEventListener('close',m1sDialogState);
 dialog.addEventListener('wheel',e=>e.stopPropagation(),{passive:true});
 dialog.addEventListener('touchmove',e=>e.stopPropagation(),{passive:true});

 dialog.addEventListener('close',()=>{familyList.replaceChildren();});
 $('addSceneObject').onclick=()=>{originalOpen();if(dialog.open){availableFamilies();m1sPopulate();m1sDialogState();}};$('objectExampleLoad').onclick=example;$('objectExamples').onchange=example;files.onchange=e=>filePreview(e.target.files[0]);$('objectCancel').onclick=()=>{if(!loading)dialog.close();};dialog.addEventListener('cancel',e=>{if(loading)e.preventDefault();});dialog.addEventListener('close',()=>{clear();owner=null;});
 $('objectConfirm').onclick=async()=>{if(!draft||!owner||loading)return;if(scene()!==owner)return say('Cena mudou; reabra a janela.');if((owner.objetos_midia||[]).length>=16)return say('Limite de 16 objetos por cena.');const d=draft,target=owner;loading=true;$('objectConfirm').disabled=true;$('objectCancel').disabled=true;$('objectExamples').disabled=true;$('objectExampleLoad').disabled=true;files.disabled=true;
 try{const t=clamp(ctx.local(),0,Math.max(0,target.duracao-.1));const o={id:'obj_'+crypto.randomUUID().replace(/-/g,''),label:d.label.slice(0,120),kind:d.kind,x:.5,y:.5,w:d.kind==='gil'?1:.7,h:d.kind==='gil'?1:.7,opacity:1,start:t,end:target.duracao,offset:0,fit:'contain',loop:true,opaque:false,motion:'',rotation:0,motion_programs:[],...(d.kind==='video'?{audio_enabled:true,audio_volume:1,audio_fade_in:.12,audio_fade_out:.12}:{})};if(d.kind==='gil'){const hash=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(d.source)))).map(v=>v.toString(16).padStart(2,'0')).join('');o.gil={format:'gil-timeline-0.1',origin:'gil',origin_sha256:hash,source_sha256:hash,source:d.source,duration:d.info.duration};}else{say('Importando arquivo local…');o.file=await ctx.upload(d.file,d.kind);}
 if(scene()!==target)throw Error('Cena mudou durante a importação. Objeto não inserido.');(target.objetos_midia??=[]).push(o);selectedId=o.id;ctx.activate();ctx.changed();dialog.close();refresh();ctx.notify('Objeto inserido na cena atual. Salve para persistir.');
 }catch(e){say(e.message);$('objectConfirm').disabled=false;}finally{loading=false;$('objectCancel').disabled=false;$('objectExamples').disabled=false;$('objectExampleLoad').disabled=false;files.disabled=false;}};
 let inspectorOpen=false,lastUndo=null;const toggle=$('viewportInspector');
 toggle.onclick=()=>{inspectorOpen=!inspectorOpen;ins.hidden=!current()||!inspectorOpen;toggle.setAttribute('aria-expanded',String(inspectorOpen));requestAnimationFrame(ctx.visualPreview);};
 $('viewportUndo').onclick=()=>{if(!lastUndo||!(objects().includes(lastUndo.object)||(legacyTarget?.scene===scene()&&[scene().imagem,scene().video_clipe,scene().gil_nativo].includes(lastUndo.object))))return;for(const k of ['x','y','w','h','rotation','shear','pivot_x','pivot_y']){if(Object.hasOwn(lastUndo.original,k))lastUndo.object[k]=lastUndo.original[k];else delete lastUndo.object[k];}lastUndo=null;$('viewportUndo').disabled=true;ctx.changed();ctx.preview();refresh();};
 const gizmo=installGizmo($('stageShell'),{read:()=>{
  if(ctx.playing()||document.fullscreenElement||$('stageShell').classList.contains('clip-editing')||!$('browserRenderCanvas').hidden)return null;
  const o=current();if(o){if(localTime(o,ctx.local())===null)return null;const key=JSON.stringify([o.motion,o.motion_programs]);try{if(motionCache.source!==key){motionCache.source=key;motionCache.eval=objectMotion(o);}return {object:o,pose:rect(o,motionCache.eval(ctx.local()-o.start)),stage:stageBounds()};}catch(e){return null;}}
  if(legacyTarget?.scene!==scene())return null;
  const kind=legacyTarget?.kind,old=kind==='image'&&scene().imagem?.modo==='quadro'?scene().imagem:kind==='clip'?scene().video_clipe:kind==='gil'?scene().gil_nativo:null;
  if(!old||!(kind==='gil'||old.arquivo))return null;
  return {object:old,pose:{x:Number(old.x??.5),y:Number(old.y??.5),w:Number(old.w??1),h:Number(old.h??1),rz:0,opacity:1},stage:stageBounds(),handles:'basic'};
 },hitTest:e=>legacyTarget?.scene===scene()&&(legacyTarget.kind==='clip'&&e.target.closest?.('#stageClip')||legacyTarget.kind==='image'&&e.target.closest?.('#stage svg image')),select:id=>{if(id!==selectedId)select(id);inspectorOpen=true;ins.hidden=false;toggle.setAttribute('aria-expanded','true');refresh();},preview:()=>{if(current())ctx.visualPreview();else ctx.preview();},commit:(original,object)=>{if(['x','y','w','h','rotation','shear','pivot_x','pivot_y'].some(k=>(original[k]??0)!==(object[k]??0))){lastUndo={original,object};$('viewportUndo').disabled=false;ctx.changed();}refresh();},cancel:()=>{ctx.preview();refresh();},metric:ctx.metric});
 const dock=document.createElement('div');dock.className='rdViewportToolDock';dock.setAttribute('role','toolbar');dock.setAttribute('aria-label','Ferramentas de edição visual');
 const defs=[['add','＋','Inserir imagem, vídeo ou GIL'],['behind','⇄','Selecionar próximo objeto atrás'],['select','⤧','Transformar: arraste corpo para mover e use alças para escala, rotação, cisalhamento e pivô'],['raise','↑','Subir camada (trazer à frente)'],['lower','↓','Descer camada (enviar para trás)'],['inspect','⚙','Propriedades do objeto'],['remove','×','Remover objeto selecionado']];
 const grip=document.createElement('button');grip.type='button';grip.className='rdDockHandle';grip.title='Arraste para mover a barra';grip.setAttribute('aria-label','Mover barra de ferramentas');grip.textContent='⠿ Arrastar';dock.append(grip);
 // Ferramentas pertencem à interface, não ao vídeo. Permaneçam fora do frame.
 let dockDrag=null;
 function constrainDock(x,y){const vv=window.visualViewport,w=vv?.width||window.innerWidth,h=vv?.height||window.innerHeight;return [clamp(x,0,Math.max(0,w-dock.offsetWidth)),clamp(y,0,Math.max(0,h-dock.offsetHeight))];}
 function placeDock(x,y){const [a,b]=constrainDock(x,y);Object.assign(dock.style,{left:a+'px',top:b+'px',right:'auto',bottom:'auto'});}
 grip.addEventListener('pointerdown',e=>{if(e.pointerType==='mouse'&&e.button!==0)return;const r=dock.getBoundingClientRect();dockDrag={id:e.pointerId,dx:e.clientX-r.left,dy:e.clientY-r.top};grip.setPointerCapture(e.pointerId);e.preventDefault();e.stopPropagation();});
 grip.addEventListener('pointermove',e=>{if(!dockDrag||e.pointerId!==dockDrag.id)return;placeDock(e.clientX-dockDrag.dx,e.clientY-dockDrag.dy);e.preventDefault();e.stopPropagation();});
 function endDock(e){if(!dockDrag||e.pointerId!==dockDrag.id)return;dockDrag=null;try{const [x,y]=[parseFloat(dock.style.left)||0,parseFloat(dock.style.top)||0];localStorage.setItem('rdStudioViewportDock-v2',JSON.stringify([x,y]));}catch{}if(grip.hasPointerCapture(e.pointerId))grip.releasePointerCapture(e.pointerId);e.stopPropagation();}
 grip.addEventListener('pointerup',endDock);grip.addEventListener('pointercancel',endDock);
 const restoreDock=()=>{try{const p=JSON.parse(localStorage.getItem('rdStudioViewportDock-v2')||'[7,65]');if(Array.isArray(p)&&p.length===2&&p.every(Number.isFinite))placeDock(p[0],p[1]);else placeDock(7,65);}catch{placeDock(7,65);}};
 const moveDockToHost=()=>{const host=document.fullscreenElement&&$('previewFullHost').contains(document.fullscreenElement)?$('previewFullHost'):document.body;
  if(dock.parentElement!==host)host.append(dock);restoreDock();};
 document.body.append(dock);requestAnimationFrame(restoreDock);window.addEventListener('resize',restoreDock);window.visualViewport?.addEventListener('resize',restoreDock);document.addEventListener('fullscreenchange',moveDockToHost);
 const toolButtons=new Map();for(const [key,glyph,label] of defs){const b=document.createElement('button');b.type='button';b.textContent=glyph;b.title=label;b.setAttribute('aria-label',label);b.dataset.tool=key;
  if(key==='select')b.setAttribute('aria-pressed','true');
  b.onclick=()=>{if(key==='add'){open();return;}if(key==='behind'){m1sSelectBehind();return;}if(key==='inspect'){if(!current()){ctx.notify('Selecione um objeto no viewport ou na timeline.');return;}inspectorOpen=true;ins.hidden=false;toggle.setAttribute('aria-expanded','true');return;}
   if(key==='raise'||key==='lower'||key==='remove'){if(!current())return ctx.notify('Selecione um objeto antes.');$('object'+(key==='raise'?'Raise':key==='lower'?'Lower':'Remove')).click();return;}
   gizmo.setTool('select');};toolButtons.set(key,b);dock.append(b);}

 // M1S_PICKING: single tap selects visual objects; repeated tap cycles overlapping layers.
 // Legacy SVG selection remains handled by the existing stage listener.
 let m1sDown=null;
 $('stageShell').addEventListener('pointerdown',e=>{m1sDown={x:e.clientX,y:e.clientY,id:e.pointerId};},true);
 $('stageShell').addEventListener('click',e=>{
  if(ctx.playing()||document.fullscreenElement||$('stageShell').classList.contains('clip-editing'))return;
  if(m1sDown&&Math.hypot(e.clientX-m1sDown.x,e.clientY-m1sDown.y)>8)return;
  const path=e.composedPath?.()||[];
  if(path.some(el=>el?.classList?.contains('rdGizmoHandle')||el?.classList?.contains('rdGizmoFace')||el?.classList?.contains('rdGizmoHit')))return;
  const ids=m1sCandidates(e);
  if(!ids.length)return;
  let index=0;
  const now=performance.now();
  if(m1sTap&&now-m1sTap.time<1100&&Math.hypot(e.clientX-m1sTap.x,e.clientY-m1sTap.y)<18&&ids.join('|')===m1sTap.ids){index=(m1sTap.index+1)%ids.length;}
  m1sTap={x:e.clientX,y:e.clientY,time:now,ids:ids.join('|'),index};
  const id=ids[index];
  e.preventDefault();e.stopImmediatePropagation();
  if(selectedId!==id)select(id);
  inspectorOpen=true;ins.hidden=false;toggle.setAttribute('aria-expanded','true');refresh();paint();
 },true);
 $('stageShell').addEventListener('dblclick',e=>{const media=e.composedPath?.().find?.(n=>n?.dataset?.sceneObjectId)||e.target.closest?.('[data-scene-object-id]');if(!media)return;e.stopImmediatePropagation();select(media.dataset.sceneObjectId);inspectorOpen=true;refresh();});
 function select(id){hideLegacy();svgDirect?.clear();ctx.stop();ctx.activate();selectedId=id;refresh();const o=current();if(o&&localTime(o,ctx.local())===null)ctx.seek(o.start);paint();}
 function stageBounds(){const r=$('stage').getBoundingClientRect(),a=ctx.dimensions().width/ctx.dimensions().height,w=Math.min(r.width,r.height*a),h=w/a;return {left:r.left+(r.width-w)/2,top:r.top+(r.height-h)/2,width:w,height:h};}
 function paint(){svgDirect?.paint();const o=current();if(o){const media=[...$('stageShell').querySelectorAll('[data-scene-object-id]')].find(n=>n.dataset.sceneObjectId===o.id);const info=$('objectMediaInfo');const size=media?.videoWidth?`${media.videoWidth} × ${media.videoHeight} px · ${media.duration.toFixed(2)} s`:media?.naturalWidth?`${media.naturalWidth} × ${media.naturalHeight} px`:o.kind==='gil'?`${o.gil?.duration||0} s · GIL`:'';info.textContent=[o.file||o.kind,size].filter(Boolean).join(' · ');}$('objectTime').textContent=scene()?`${ctx.local().toFixed(2)} / ${Number(scene().duracao).toFixed(2)} s`:'';const cursor=$('objectCursor');cursor.style.left=scene()?clamp(ctx.local()/scene().duracao,0,1)*100+'%':'0';gizmo.paint();}
 function refresh(){m1tManager.refresh();if(legacyTarget&&legacyTarget.scene!==scene())hideLegacy();if(scene()!==selectedScene){lastUndo=null;$('viewportUndo').disabled=true;selectedScene=scene();if(!current())selectedId='';}const c=scene(),all=objects();tracks.replaceChildren();if(!c)return;
 const legacy=[['Arte base',true,'scene'],['Imagem original',!!c.imagem?.arquivo,'image'],['Clipe original',!!c.video_clipe?.arquivo,'clip'],['GIL anterior',!!c.gil_nativo,'gil'],['Narração',!!c.audio?.voice_enabled,true],['Música da cena',!!c.audio?.music_file,true],...(c.audio?.tracks||[]).filter(t=>t.file).map((t,i)=>[t.file,true,true,t.start])];for(const [label,show,audio,start=0] of legacy){if(!show)continue;const row=document.createElement('div');row.className='objectTrack legacy';const name=document.createElement('button');name.type='button';name.textContent=label;name.title=label;name.onclick=audio==='clip'?()=>selectLegacy('clip'):audio==='image'?()=>selectLegacy('image'):audio==='scene'?()=>selectLegacy('scene'):audio==='gil'?()=>selectLegacy('gil'):ctx.audio;if(audio===true)row.classList.add('audioTrack');const lane=document.createElement('div');lane.className='objectLane';const b=document.createElement('span');b.className='objectBar';b.style.cssText=`left:${clamp(start/c.duracao,0,1)*100}%;width:${(1-clamp(start/c.duracao,0,1))*100}%`;lane.append(b);row.append(name,lane);tracks.append(row);}
 for(const o of all){const row=document.createElement('div');row.className='objectTrack';const name=document.createElement('button');name.type='button';name.textContent=o.label;name.title=o.label;name.onclick=()=>select(o.id);const lane=document.createElement('div');lane.className='objectLane';const b=document.createElement('button');b.type='button';b.textContent=o.kind==='video'?(o.audio_enabled===false?'VÍDEO · mudo':'VÍDEO + ÁUDIO'):o.kind.toUpperCase();b.className='objectBar '+(o.id===selectedId?'chosen':'');b.style.left=clamp(o.start/c.duracao,0,1)*100+'%';b.style.width=clamp((Math.min(o.end,c.duracao)-o.start)/c.duracao,0,1)*100+'%';b.onclick=()=>select(o.id);lane.onclick=e=>{if(e.target!==lane)return;ctx.seek(clamp((e.clientX-lane.getBoundingClientRect().left)/lane.clientWidth,0,.9999)*c.duracao);};lane.append(b);row.append(name,lane);tracks.append(row);}
 const o=current();$('objectCrop').hidden=o?.kind!=='image';$('objectEditTitle').hidden=!o?.label?.startsWith('TÍTULO [');ins.hidden=!o||!inspectorOpen;toggle.disabled=!o;toggle.setAttribute('aria-expanded',String(!!o&&inspectorOpen));if(o){$('objectLabel').textContent=o.label;for(const k of ['x','y','w','h','rotation','shear','pivot_x','pivot_y','opacity','start','end','offset','corner_radius','border_width','shadow_blur'])$('object_'+k).value=o[k]??0;for(const k of ['border_color','shadow_color'])$('object_'+k).value=o[k]??(k==='border_color'?'#ffffff':'#000000');$('object_motion').value=o.motion||'';$('object_fit').value=o.fit;$('object_loop').checked=o.loop;$('object_opaque').checked=o.opaque;$('object_opaque').disabled=o.kind!=='gil';$('objectAudioFields').hidden=o.kind!=='video';$('object_audio_enabled').checked=o.audio_enabled!==false;$('object_audio_volume').value=o.audio_volume??1;for(const k of ['audio_fade_in','audio_fade_out'])$('object_'+k).value=o[k]??.12;stackDraft=[...(o.motion_programs||[])];drawStack();}paint();}
 $('objectCrop').onclick=async()=>{
  const o=current(),target=scene();if(o?.kind!=='image'||!target)return;
  const source=o.source_file||o.file;
  try{await window.StudioImageComposer.open({
   url:'/api/media/image?file='+encodeURIComponent(source),video:ctx.dimensions(),
   config:{arquivo:source,crop:o.source_crop||[0,0,1,1],fit:o.fit,align_x:.5,align_y:.5,bg:'#241b1a',modo:'quadro',x:o.x,y:o.y,w:o.w,h:o.h},
   onChange:async res=>{
    if(scene()!==target||!objects().includes(o))throw Error('Seleção ou cena mudou; nenhuma alteração aplicada.');
    const original=res.arquivo||source,crop=normalizeCrop(res.crop);
    const blob=await cropImageURL('/api/media/image?file='+encodeURIComponent(original),crop);
    const filename=await ctx.upload(new File([blob],'recorte-'+Date.now()+'.png',{type:'image/png'}),'image');
    if(scene()!==target||!objects().includes(o))throw Error('Seleção mudou durante a importação.');
    Object.assign(o,{file:filename,source_file:original,source_crop:crop,x:res.x,y:res.y,w:res.w,h:res.h,fit:res.fit==='contain'?'contain':'cover'});
    ctx.changed();refresh();ctx.preview();ctx.notify('Recorte atualizado; mídia original preservada. Salve o projeto.');
   }});
  }catch(e){ctx.notify(e.message,true);}
 };
 $('objectRuler').onclick=e=>{if(!scene())return;const r=e.currentTarget.getBoundingClientRect();ctx.seek(clamp((e.clientX-r.left)/r.width,0,.9999)*scene().duracao);};
 $('objectApply').onclick=()=>{const o=current();if(!o)return;try{const change={};for(const [k,lo,hi] of [['x',-2,3],['y',-2,3],['w',.02,2],['h',.02,2],['rotation',-360,360],['shear',-2,2],['pivot_x',-.5,.5],['pivot_y',-.5,.5],['opacity',0,1],['start',0,600],['end',0,600],['offset',0,3600],['corner_radius',0,.5],['border_width',0,20],['shadow_blur',0,60]]){const el=$('object_'+k),n=Number(el.value);if(el.value===''||!Number.isFinite(n)||n<lo||n>hi)throw Error('Valor inválido: '+k);change[k]=n;}if(change.end<=change.start)throw Error('Fim precisa ser maior que início.');for(const k of ['border_color','shadow_color'])change[k]=$('object_'+k).value;change.fit=$('object_fit').value;change.loop=$('object_loop').checked;change.opaque=$('object_opaque').checked;change.motion=$('object_motion').value;if(new TextEncoder().encode(change.motion).length>16000)throw Error('Fonte excessiva.');change.motion_programs=[...stackDraft];if(o.kind==='video'){const v=Number($('object_audio_volume').value);if(!Number.isFinite(v)||v<0||v>3)throw Error('Volume inválido');change.audio_enabled=$('object_audio_enabled').checked;change.audio_volume=v;for(const k of ['audio_fade_in','audio_fade_out']){const f=Number($('object_'+k).value);if(!Number.isFinite(f)||f<0||f>5)throw Error('Fade inválido: '+k);change[k]=f;}}objectMotion(change);Object.assign(o,change);ctx.changed();refresh();}catch(e){ctx.notify(e.message,true);}};
 function drawStack(){const host=$('objectMotionStack');host.replaceChildren();stackDraft.forEach((source,i)=>{const row=document.createElement('div');row.className='motionProgramRow';const details=document.createElement('details'),title=document.createElement('summary'),text=document.createElement('textarea'),remove=document.createElement('button');title.textContent='Programa '+(i+2);text.value=source;text.rows=5;text.spellcheck=false;text.oninput=()=>stackDraft[i]=text.value;details.append(title,text);remove.type='button';remove.textContent='×';remove.setAttribute('aria-label','Remover programa '+(i+2));remove.onclick=()=>{stackDraft.splice(i,1);drawStack();};row.append(details,remove);host.append(row);});}
 $('objectAddProgram').onclick=()=>{if(stackDraft.length>=8)return ctx.notify('Limite de 8 programas adicionais.',true);stackDraft.push(motionSource('fade',current().end-current().start));drawStack();};
 // M1R1_MOTION: enrich the existing inspector; no new editor or clock.
 const advancedMotions=[['ken-burns','Foto: Ken Burns'],['pan-left','Pan esquerda'],['pan-right','Pan direita'],['parallax','Parallax 2,5D'],['push-in','Aproximar'],['pull-out','Afastar'],['pop','Pop'],['bounce','Salto'],['tilt-in','Giro de entrada'],['swing','Oscilar'],['wipe-in','Revelar'],['shrink-away','Encolher e sair'],['drift-up','Flutuar ↑'],['drift-down','Flutuar ↓'],['orbit-soft','Órbita suave'],['stagger-in','Entrada escalonada'],['stagger-out','Saída escalonada']];
 const motionButtons=ins.querySelector('[data-motion]')?.parentElement;
 const quickChoices=[['ken-burns','Ken Burns'],['pan-left','Pan'],['parallax','Parallax'],['push-in','Zoom'],['stagger-in','Entrada'],['stagger-out','Saída']];
 if(motionButtons&&!ins.querySelector('.rdQuickMotion')){
  const quick=document.createElement('div');quick.className='rdQuickMotion';
  const label=document.createElement('strong');label.textContent='Movimentos rápidos (selecione e clique Aplicar)';quick.append(label);
  for(const [key,name] of quickChoices){const b=document.createElement('button');b.type='button';b.textContent=name;b.dataset.quickMotion=key;b.onclick=()=>ins.querySelector('[data-motion="'+key+'"]')?.click();quick.append(b);}
  motionButtons.before(quick);
 }
 if(motionButtons&&!motionButtons.querySelector('[data-m1r-advanced]')){
  const details=document.createElement('details');details.dataset.m1rAdvanced='';
  const summary=document.createElement('summary');summary.textContent='Mais movimentos (GIL)';details.append(summary);
  const group=document.createElement('div');group.className='motionProgramRow';
  for(const [name,label] of advancedMotions){const b=document.createElement('button');b.type='button';b.dataset.motion=name;b.textContent=label;group.append(b);}
  details.append(group);motionButtons.append(details);
 }
 for(const b of ins.querySelectorAll('[data-motion]'))b.onclick=()=>{const o=current();if(!o)return;const field=$('object_motion');if(b.dataset.motion==='none'){if(confirm('Limpar todos os programas de movimento deste objeto?')){field.value='';stackDraft=[];drawStack();}return;}const source=motionSource(b.dataset.motion,o.end-o.start);if(!field.value.trim())field.value=source;else{if(stackDraft.length>=8)return ctx.notify('Limite de 8 programas adicionais.',true);stackDraft.push(source);drawStack();}};
 $('objectRemove').onclick=()=>{const o=current();if(o&&confirm('Remover apenas '+o.label+'?')){scene().objetos_midia=objects().filter(x=>x!==o);selectedId='';ctx.changed();refresh();}};
 $('objectRaise').onclick=()=>{const a=objects(),i=a.indexOf(current());if(i>=0&&i<a.length-1){[a[i],a[i+1]]=[a[i+1],a[i]];ctx.changed();ctx.preview();refresh();ctx.notify('Camada '+(i+2)+' de '+a.length+' · trazida à frente.');}else ctx.notify('O objeto já está na frente.');};
 $('objectLower').onclick=()=>{const a=objects(),i=a.indexOf(current());if(i>0){[a[i],a[i-1]]=[a[i-1],a[i]];ctx.changed();ctx.preview();refresh();ctx.notify('Camada '+i+' de '+a.length+' · enviada para trás.');}else ctx.notify('O objeto já está atrás.');};
 // Preserve the source as an editable GIL text document. This uses the existing
 // compiler/timeline (prepare) and does not navigate to an assumed port.
 const gilDialog=document.createElement('dialog');gilDialog.className='rdGilSourceDialog';gilDialog.setAttribute('aria-label','Editor de fonte GIL');
 gilDialog.innerHTML='<div class="rdTitleHead"><b>Editor GIL nativo</b><button data-gil-close type="button">× Fechar</button></div><p class="smallNote">Editor de fonte da composição. O mesmo runtime GIL valida e mostra os quadros. Não suporta GIL3 nem áudio interno.</p><textarea data-gil-code spellcheck="false" aria-label="Código GIL"></textarea><div class="inline"><label>Tempo <input data-gil-time type="range" min="0" max="8" step="0.02" value="0"></label><output data-gil-read>0.00 s</output><button data-gil-validate type="button">Validar e visualizar</button></div><div data-gil-preview></div><p data-gil-status class="smallNote" role="status"></p><div class="rdTitleActions"><button data-gil-close type="button">Cancelar</button><button data-gil-save type="button" class="primary">Aplicar fonte</button></div>';
 document.body.append(gilDialog);
 const code=gilDialog.querySelector('[data-gil-code]'),range=gilDialog.querySelector('[data-gil-time]'),readout=gilDialog.querySelector('[data-gil-read]'),image=gilDialog.querySelector('[data-gil-preview]'),error=gilDialog.querySelector('[data-gil-status]'),saveGIL=gilDialog.querySelector('[data-gil-save]');
 let sourceOwner=null,sourceTarget=null,compiled=null;
 const validate=()=>{try{compiled=prepare(code.value);if(compiled.cues)throw Error('Fontes com áudio GIL não suportadas.');range.max=compiled.duration;range.value=Math.min(Number(range.value),compiled.duration);renderGil();error.textContent=compiled.duration.toFixed(2)+' segundos · fonte válida';return true;}catch(e){compiled=null;image.replaceChildren();error.textContent=e.message;return false;}};
 const renderGil=()=>{if(!compiled)return;try{const t=Math.max(0,Math.min(Number(range.value),compiled.duration));const frame=parseFrame(compiled.frame(t),true);frame.style.cssText='width:100%;height:100%';image.replaceChildren(frame);readout.textContent=t.toFixed(2)+' s';}catch(e){error.textContent=e.message;}};
 gilDialog.querySelector('[data-gil-validate]').onclick=validate;range.oninput=renderGil;
 code.oninput=()=>{compiled=null;saveGIL.disabled=!code.value.trim();error.textContent='Fonte alterada; valide antes de aplicar.';};
 for(const b of gilDialog.querySelectorAll('[data-gil-close]'))b.onclick=()=>gilDialog.close();
 function editGil(){if(!scene())return ctx.notify('Abra uma cena primeiro.',true);
  sourceOwner=scene();sourceTarget=current()?.kind==='gil'?current():scene()?.gil_nativo||null;
  code.value=sourceTarget?(sourceTarget.kind==='gil'?sourceTarget.gil.source:sourceTarget.source):'';
  error.textContent='';compiled=null;image.replaceChildren();gilDialog.showModal();
  if(code.value)validate();else {error.textContent='Sem GIL selecionada. Cole código GIL Timeline 0.1 e valide; para inserir, use Inserir GIL.';saveGIL.disabled=true;}
  saveGIL.disabled=!code.value.trim();saveGIL.textContent=sourceTarget?'Aplicar fonte':'Inserir fonte como objeto';
 }
 saveGIL.onclick=async()=>{if(sourceOwner!==scene()||!code.value.trim()||!validate())return;
  const source=code.value.trim();if(new TextEncoder().encode(source).length>250000)return error.textContent='Fonte excessiva.';
  const bytes=new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(source)));
  const sha=[...bytes].map(v=>v.toString(16).padStart(2,'0')).join('');
  if(!sourceTarget){gilDialog.close();openSource(source,'editor.gil');return;}
  if(sourceOwner!==scene()||(sourceTarget.kind==='gil'&&!objects().includes(sourceTarget)))return error.textContent='Seleção mudou durante a validação.';
  const g=sourceTarget.kind==='gil'?sourceTarget.gil:sourceTarget;
  Object.assign(g,{format:'gil-timeline-0.1',origin:'gil',source,source_sha256:sha,origin_sha256:sha,duration:compiled.duration});
  ctx.changed();refresh();gilDialog.close();ctx.notify('Fonte GIL validada e atualizada. Salve o projeto.');
 };
 svgDirect=installSvgDirect({shell:$('stageShell'),scene,playing:ctx.playing,changed:()=>ctx.changed(),notify:ctx.notify,select:selectLegacy});
 const titles=installTitleGallery({scene,dimensions:ctx.dimensions,local:ctx.local,upload:ctx.upload,changed:ctx.changed,select,notify:ctx.notify,motionSource,refresh,selected:current});
 installRoteiroEditor({scene,selected:current,openSource,stop:ctx.stop,seek:ctx.seek,local:ctx.local,notify:ctx.notify,changed:ctx.changed,refresh});
 $('objectEditTitle').onclick=()=>{const o=current();if(o?.label?.startsWith('TÍTULO ['))titles?.open((o.label.match(/^TÍTULO \[([^\]]+)/)||[])[1]||'editorial',o);};
 $('legacyEditSVG').title='Abre o editor vetorial para edições detalhadas';
 window.addEventListener('resize',paint);document.addEventListener('fullscreenchange',paint);
 return {open,openSource,refresh,paint,selectLegacy,editGil,editTitle:()=>{const o=current();if(o?.label?.startsWith('TÍTULO ['))titles?.open((o.label.match(/^TÍTULO \[([^\]]+)/)||[])[1]||'editorial',o);}};
}
