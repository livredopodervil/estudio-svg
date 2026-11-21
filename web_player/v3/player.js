(() => {
'use strict';
const $=id=>document.getElementById(id), clamp=(x,a=0,b=1)=>Math.max(a,Math.min(b,x));
let project=null, durations=[], starts=[], total=0, index=-1, svg=null, bases=new Map();
let current=0, playing=false, origin=0, raf=0, voiceEl=null, voiceScene=-1, warning='', speed=1;
let voiceBusy=false, voiceEpoch=0, waitingVoice=false, calibration=false;
const localPlayer=location.pathname==='/player-v3/'||location.pathname==='/player-v3/index.html';
const slug=localPlayer?new URLSearchParams(location.search).get('project'):document.documentElement.dataset.slug;
let revision='',pendingScene=-1;
const pivotStoreKey='estudio-svg-vetorial-pivos:'+slug;
let pivotOverrides={};
try { pivotOverrides=JSON.parse(localStorage.getItem(pivotStoreKey)||'{}')||{}; } catch (_) { pivotOverrides={}; }
/* ESTUDIO_SVG_VETORIAL_AUDIO_PIVO_V2 */
/* ESTUDIO_V3_MEDIA_PATCH_2026_11 */
const out=s=>{$('status').textContent=s};
const sec=t=>`${Math.floor(t/60).toString().padStart(2,'0')}:${Math.floor(t%60).toString().padStart(2,'0')}`;
function pick(t){let i=0; while(i<durations.length-1 && t>=starts[i]+durations[i])i++;return i;}
function source(c){const x=c.audio||{};return (x.voice_file||'').trim();}
function voiceText(c){return String(c.audio?.voice_text || c.fala || '').trim();}
// ESTUDIO_SVG_V34_VOICE_LOCALE

const voiceRuntime=new window.StudioV34.Narrator({
  synth:('speechSynthesis' in window)?window.speechSynthesis:null,
  createAudio:()=>new Audio(), status:out
});
function stopVoice(){
  ++voiceEpoch;voiceRuntime.stop();voiceBusy=false;waitingVoice=false;voiceScene=-1;
}
function nativeVoice(scene){
  if(!$('narrate').checked || voiceScene===scene)return;
  stopVoice();voiceScene=scene;
  const c=project.cenas[scene];
  if(c.audio?.muted||c.audio?.voice_enabled===false)return;
  const originalLang=String(project.idioma||project.language||'pt-BR');
  const lang=$('lang').value;
  const localeText=window.StudioV34.localeText(c,scene,lang,window.__localePacks||{},originalLang);
  if(localeText.lang!==lang)out('Tradução '+lang+' indisponível; usando fala em '+originalLang+'.');
  const basePath=String(c.audio?.voice_file||'').trim();
  const nativeMap=window.__voiceSceneFiles||{},legacy=window.__voiceFiles||{};
  const perLang=window.__voiceSceneLocaleFiles?.[lang]||{};
  const file=perLang[scene]||(lang===originalLang?(nativeMap[scene]||legacy[basePath]||''):'');
  voiceRuntime.setMode($('voiceSource').value);
  voiceRuntime.setRate(Number($('rate').value)*speed);
  voiceRuntime.setVolume(1);
  voiceRuntime.speak({text:localeText.text,lang:localeText.lang,file,
    voices:window.speechSynthesis?.getVoices?.()||[],
    voiceName:$('voiceName').value,
    onDone:()=>{voiceBusy=false;}});
  voiceBusy=voiceRuntime.busy;
}
function sanitize(root){
  root.querySelectorAll('script,foreignObject,iframe,object,embed').forEach(n=>n.remove());
  root.querySelectorAll('*').forEach(el=>{
    for(const a of [...el.attributes]){
      if(/^on/i.test(a.name))el.removeAttribute(a.name);
      if(/^(href|xlink:href)$/i.test(a.name) && /^\s*javascript:/i.test(a.value))el.removeAttribute(a.name);
    }
  });
  return root;
}
async function loadScene(i,token){
  pendingScene=i;
  window.StudioMedia?.pause();objectsModule?.pauseObjects($('stageShell'));
  const url=localPlayer?'/api/player-v3?name='+encodeURIComponent(slug)+'&revision='+encodeURIComponent(revision)+'&scene='+(i+1):'./cenas/cena-'+String(i+1).padStart(3,'0')+'.svg';
  const res=await fetch(url,{cache:'no-store'});
  if(!res.ok)throw Error(url+' → HTTP '+res.status);
  const markup=await res.text();
  if(token!==loadToken)return; // Ignora resposta de fetch anterior a uma busca na timeline.
  const parsed=new DOMParser().parseFromString(markup,'image/svg+xml');
  if(parsed.querySelector('parsererror'))throw Error('SVG inválido: cena '+(i+1));
  const root=sanitize(document.importNode(parsed.documentElement,true));
  if(root.localName!=='svg')throw Error('Documento não é SVG: cena '+(i+1));
  stopVoice();index=i;pendingScene=-1;bases.clear();canonicalAnimator=null;
  $('stage').replaceChildren(root);svg=root;
  svg.setAttribute('preserveAspectRatio','xMidYMid meet');svg.removeAttribute('width');svg.removeAttribute('height');
  $('scene').textContent=(i+1)+' / '+durations.length+' · '+String(project.cenas[i].titulo||'');
  for(const el of svg.querySelectorAll('[id]'))bases.set(el.id,{el,transform:el.getAttribute('transform')||'',opacity:el.getAttribute('opacity')||'1'});
  const targets=[...new Set((project.cenas[i].animacoes||[]).filter(a=>a.tipo==='rotacao').map(a=>String(a.alvo)).filter(t=>bases.has(t)))];
  const picker=$('pivotTarget');
  picker.replaceChildren(...targets.map(t=>new Option(t,t)));
  picker.hidden=!targets.length;
  picker.value=targets.find(t=>/ponteiro|agulha|hand|segund|minut|hora/i.test(t))||targets[0]||'';
  calibration=false;$('calibrate').textContent='⊙ Ajustar eixo';
  window.StudioMedia?.scene(i,project.cenas[i],project.video,current-starts[i],playing,speed);
  if(playing)nativeVoice(i);
}
function val(a,k,defaultValue=0){const n=Number(a[k]);return Number.isFinite(n)?n:defaultValue;}
function ease(t,mode){return window.EstudioV3.ease(t,mode);}
function pivot(el,a){return window.EstudioV3.pivotDOM(el,a,svg,{pivotOverrides,sceneIndex:index});}
let canonicalAnimator=null;
let nativeRuntime=null,nativeLoading=null,nativeFailed=false;
let objectsModule=null,objectsLoading=false;
function updateObjects(t){
 if(!localPlayer||!project||index<0)return;const objects=project.cenas[index].objetos_midia||[];
 if(objectsModule){objectsModule.syncObjects($('stageShell'),objects,Math.max(0,t-starts[index]),project.video,playing&&!waitingVoice,speed,out);return;}
 if(!objects.length||objectsLoading)return;objectsLoading=true;import('/scene-objects.mjs').then(m=>{objectsModule=m;updateObjects(current);}).catch(e=>out('Objetos: '+e.message));
}
function updateNative(){
  if(!localPlayer||!project||index<0)return;
  const layer=project.cenas[index].gil_nativo||null,shell=$('stageShell');
  if(nativeRuntime){nativeRuntime.updateLayer(shell,layer,Math.max(0,current-starts[index]),project.video);return;}
  if(!layer||nativeLoading||nativeFailed)return;
  nativeLoading=import('/gil-native.mjs').then(m=>{nativeRuntime=m;updateNative();}).catch(e=>{nativeFailed=true;out('GIL nativa indisponível: '+e.message);});
}
function apply(t){
  if(!project || !svg)return;
  updateNative();updateObjects(t);
  const p=clamp((t-starts[index])/durations[index]);
  if(!canonicalAnimator)canonicalAnimator=window.EstudioV3.createDOMAnimator(svg,project.cenas[index].animacoes||[],{pivotOverrides,sceneIndex:index});
  canonicalAnimator.apply(p);
  window.EstudioV3.updateProcedural(svg,project.cenas[index],p);
  // Mesma cena permanece no DOM, sem solicitação de frames ao servidor.
  svg.style.opacity=String(clamp(p/.06));
  window.StudioMedia?.tick(index,Math.max(0,t-starts[index]),playing&&!waitingVoice,speed);
  $('seek').value=String(Math.round(1000*t/Math.max(total,.001)));
  $('clock').textContent=sec(t)+' / '+sec(total);
}
let loadToken=0;
async function show(t){
  if(!project)return;
  current=clamp(t,0,total);const i=pick(Math.min(current,Math.max(0,total-1e-6)));
  if(pendingScene===i)return;
  if(i!==index){const token=++loadToken;try{await loadScene(i,token);}catch(e){if(token!==loadToken)return;pendingScene=-1;throw e;}if(token!==loadToken)return;}
  else if(pendingScene!==-1){++loadToken;pendingScene=-1;}
  apply(current);
}
function loop(now){
  if(!playing)return;
  if(voiceEl && voiceEl.error){out('Erro na narração.');stopVoice();}
  if(pendingScene!==-1){origin=now-current*1000/speed;raf=requestAnimationFrame(loop);return;}
  let t=(now-origin)/1000*speed;
  // Nunca troca de cena antes de concluir a voz da cena corrente.
  if(index>=0&&voiceBusy&&index<durations.length){
    const end=starts[index]+durations[index];
    if(t>=end){
      t=end-0.0005;
      origin=now-t*1000/speed; // pausa o relógio das imagens e o clipe
      if(!waitingVoice){waitingVoice=true;out('Aguardando conclusão da narração da cena '+(index+1));}
    }
  }else if(waitingVoice){waitingVoice=false;out('Reprodução sincronizada.');}
  if(t>=total){pause();show(total).catch(e=>out(e.message));return;}
  show(t).catch(e=>{pause();out('Erro: '+e.message);});
  raf=requestAnimationFrame(loop);
}
function pause(){
  playing=false;cancelAnimationFrame(raf);window.StudioMedia?.pause();objectsModule?.pauseObjects($('stageShell'));
  voiceRuntime.pause();
  $('play').textContent='▶ Reproduzir';
}
$('play').onclick=()=>{
  if(!project)return;
  if(playing){pause();return;}
  if(current>=total){current=0;stopVoice();}
  playing=true;window.StudioMedia?.play();origin=performance.now()-current*1000/speed;$('play').textContent='Ⅱ Pausar';
  if(index>=0&&index===pick(current)){
    if(voiceBusy&&voiceScene===index){voiceRuntime.resume();}else nativeVoice(index);
  }
  raf=requestAnimationFrame(loop);
};
$('seek').oninput=()=>{const t=total*Number($('seek').value)/1000;
  if(playing)origin=performance.now()-t*1000/speed;
  stopVoice();window.StudioMedia?.seek(pick(t),t-starts[pick(t)]);
  show(t).then(()=>{if(playing&&index===pick(current)&&pendingScene===-1)nativeVoice(index)}).catch(e=>out(e.message));
};
$('speed').onchange=()=>{speed=Number($('speed').value)||1;origin=performance.now()-current*1000/speed;voiceRuntime.setRate(Number($('rate').value)*speed);if(index>=0)apply(current);};
$('rate').oninput=()=>{$('rateOut').textContent=Number($('rate').value).toFixed(2)+'×';
  voiceRuntime.setRate(Number($('rate').value)*speed);
  // Web Speech API não permite alterar a velocidade durante uma fala em curso.
};
$('narrate').onchange=()=>{if(!$('narrate').checked)stopVoice();else if(playing&&index>=0)nativeVoice(index);};
$('calibrate').onclick=()=>{
  if(!$('pivotTarget').value){out('Cena sem alvos de rotação configurados.');return;}
  calibration=!calibration;
  $('calibrate').textContent=calibration?'Cancelar ajuste':'⊙ Ajustar eixo';
  if(calibration)out('Toque no centro do mostrador para ajustar o eixo de '+$('pivotTarget').value+'.');
};
$('stage').addEventListener('click',e=>{
  if(!calibration||!svg||!svg.contains(e.target))return;
  const target=$('pivotTarget').value,el=bases.get(target)?.el;
  if(!el)return;
  try{
    const parent=el.parentNode?.getScreenCTM?el.parentNode:svg;
    const matrix=parent.getScreenCTM().inverse(),p=svg.createSVGPoint();
    p.x=e.clientX;p.y=e.clientY;
    const at=p.matrixTransform(matrix);
    pivotOverrides[index+':'+target]=[at.x,at.y];
    try{localStorage.setItem(pivotStoreKey,JSON.stringify(pivotOverrides));}
    catch(_){out('Eixo ajustado nesta sessão; armazenamento local bloqueado.');}
    calibration=false;$('calibrate').textContent='⊙ Ajustar eixo';
    apply(current);
    out('Eixo de '+target+' definido em ('+at.x.toFixed(1)+', '+at.y.toFixed(1)+').');
  }catch(err){out('Não foi possível definir o eixo: '+err.message);}
});
$('lang').onchange=async()=>{
  const lang=$('lang').value;
  document.documentElement.lang=lang;
  window.__localePacks=window.__localePacks||{};
  if(!window.__localePacks[lang]){
    try{const p=await window.StudioV34.fetchPack(lang);if(p)window.__localePacks[lang]=p;}
    catch(e){out('Locale '+lang+': '+e.message);}
  }
  stopVoice();if(playing&&index>=0)nativeVoice(index);
};
$('voiceSource').onchange=()=>{stopVoice();if(playing&&index>=0)nativeVoice(index);};
$('voiceName').onchange=()=>{stopVoice();if(playing&&index>=0)nativeVoice(index);};
function refreshVoices(){
  const select=$('voiceName'),keep=select.value;
  const voices=window.speechSynthesis?.getVoices?.()||[];
  select.replaceChildren(new Option('Automática',''),...voices.map(v=>new Option(v.name+' ('+v.lang+')',v.voiceURI)));
  select.value=[...select.options].some(o=>o.value===keep)?keep:'';
}
refreshVoices();window.speechSynthesis?.addEventListener?.('voiceschanged',refreshVoices);

const fullscreenShell=$('stageShell');let fullTimer;
function revealFullControls(){if(document.fullscreenElement!==fullscreenShell)return;fullscreenShell.classList.add('controls-visible');clearTimeout(fullTimer);fullTimer=setTimeout(()=>fullscreenShell.classList.remove('controls-visible'),3500);}
$('full').onclick=async()=>{try{if(document.fullscreenElement)await document.exitFullscreen();else if(fullscreenShell.requestFullscreen)await fullscreenShell.requestFullscreen();else throw Error('Tela cheia não suportada');}catch(e){out(e.message+' — abra o player em uma aba independente do Chrome.');}};
$('fullExit').onclick=()=>document.exitFullscreen?.().catch(e=>out(e.message));$('fullPlay').onclick=()=>$('play').click();
fullscreenShell.addEventListener('click',revealFullControls);document.addEventListener('fullscreenchange',()=>{if(document.fullscreenElement===fullscreenShell)revealFullControls();else{clearTimeout(fullTimer);fullscreenShell.classList.remove('controls-visible');}});
if(window!==parent){$('separate').href=location.href;$('separate').hidden=false;}
window.addEventListener('pagehide',()=>{pause();stopVoice();});
(async()=>{
  try{
    const requested=new URLSearchParams(location.search).get('project');
    if(localPlayer&&!slug)throw Error('Selecione e salve um projeto no editor.');
    if(!localPlayer && requested && requested!==slug)throw Error('Esta apresentação inclui SVGs de '+slug+'. Publique os SVGs e JSON de '+requested+' em um pacote próprio; não é possível trocar apenas o JSON.');
    const r=await fetch(localPlayer?'/api/player-v3?name='+encodeURIComponent(slug):'../apresentacoes/'+encodeURIComponent(slug)+'/projeto.json',{cache:'no-store'});
    if(!r.ok)throw Error('projeto.json HTTP '+r.status);
    const payload=await r.json();
    project=localPlayer?payload.project:payload;
    if(localPlayer){revision=payload.revision;window.__voiceSceneFiles=payload.voices||{};document.querySelector('header a').href='/?project='+encodeURIComponent(slug);}
    if(!Array.isArray(project.cenas)||!project.cenas.length)throw Error('Projeto sem cenas');
    starts=[];let sum=0;durations=project.cenas.map(c=>Math.max(.1,Number(c.duracao)||1));
    for(const d of durations){starts.push(sum);sum+=d;}total=sum;
    const lang=String(project.idioma||project.language||'pt-BR');
    $('lang').value=[...$('lang').options].some(o=>o.value===lang)?lang:'pt-BR';
    document.documentElement.lang=$('lang').value;
    $('loadedProject').textContent='Projeto: '+String(project.titulo||slug)+' · '+slug;
    await show(0);
    out('Player Web vetorial V3 · '+project.cenas.length+' cenas · projeção espacial e timeline no navegador.');
  }catch(e){out('Falha: '+e.message);console.error(e);}
})();
})();
