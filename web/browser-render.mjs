import {canvasAppearance} from './visual-effects.mjs';
// Estúdio SVG · Rogério Duarte. Exportação local experimental, sem quadros PNG no servidor.
import {objectMotion,localTime,rect} from './scene-objects.mjs';
import {codecCandidates,codecs} from './platform-capabilities.mjs';
import {affine} from './viewport-affine.mjs';
import {prepare,frameTime} from './gil-native.mjs';
const clamp=(v,a,b)=>Math.min(b,Math.max(a,v));
export function plan(project,durations=null){
 const {width,height,fps,draw_fps}=project.video, scenes=project.cenas;
 if(![width,height,fps,draw_fps].every(Number.isFinite)||width<320||height<320||width>1920||height>1920||![24,25,30].includes(fps)||draw_fps<1)throw Error('Configuração de vídeo inválida.');
 let duration=0;const entries=scenes.map((scene,index)=>{
  const nominal=Number(scene.duracao),d=durations?Number(durations[index]):nominal;if(!Number.isFinite(d)||!Number.isFinite(nominal)||d<nominal-.00001||nominal<.5)throw Error('Duração inválida na cena '+(index+1));
  const start=duration;duration+=d;const videos=Number(!!scene.video_clipe?.arquivo)+(scene.objetos_midia||[]).filter(o=>o.kind==='video').length;if(videos>8)throw Error('Até 8 clipes por cena.');
  return {scene,index,start,end:duration,duration:d,nominal};
 });
 if(!entries.length||duration>900||entries.length>150)throw Error('Exportação experimental: até 900 s e 150 cenas.');
 return {entries,duration,width,height,fps,baseFPS:Math.min(draw_fps,12,fps),gilFPS:Math.min(15,fps)};
}
export function atTime(entries,t){return entries.find(e=>t<e.end)||entries[entries.length-1];}
export function boxFit(sw,sh,w,h,fit){
 if(!(sw>0&&sh>0&&w>0&&h>0))return null;
 if(fit==='cover'){const s=Math.max(w/sw,h/sh),cw=w/s,ch=h/s;return [(sw-cw)/2,(sh-ch)/2,cw,ch,-w/2,-h/2,w,h];}
 if(fit==='contain'){const s=Math.min(w/sw,h/sh);return [0,0,sw,sh,-sw*s/2,-sh*s/2,sw*s,sh*s];}
 return [0,0,sw,sh,-w/2,-h/2,w,h];
}
export function sourceTime(t,d,loop){if(!Number.isFinite(d)||d<=0)return null;return loop?((t%d)+d)%d:t<d?Math.max(0,t):null;}
export {codecCandidates};
function abortCheck(signal){if(signal.aborted)throw Error('Exportação cancelada.');}
function timed(p,ms,message,signal){return new Promise((resolve,reject)=>{let done=false;const finish=(fn,x)=>{if(done)return;done=true;clearTimeout(timer);signal.removeEventListener('abort',abort);fn(x);};const abort=()=>finish(reject,Error('Exportação cancelada.'));const timer=setTimeout(()=>finish(reject,Error(message)),ms);signal.addEventListener('abort',abort,{once:true});if(signal.aborted){abort();return;}Promise.resolve(p).then(v=>finish(resolve,v),e=>finish(reject,e));});}
async function response(path,body,signal){const r=await fetch(path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body),signal});if(!r.ok){let msg='HTTP '+r.status;try{msg=(await r.json()).error||msg;}catch{}throw Error(msg);}return r;}
async function svgImage(markup,signal,{transparent=false}={}){
 if(transparent){const doc=new DOMParser().parseFromString(markup,'image/svg+xml');if(doc.documentElement.localName!=='svg'||doc.querySelector('parsererror'))throw Error('SVG GIL inválido.');const root=doc.documentElement;if(root.firstElementChild?.localName==='rect')root.firstElementChild.remove();markup=new XMLSerializer().serializeToString(root);}
 const url=URL.createObjectURL(new Blob([markup],{type:'image/svg+xml'}));const im=new Image();im.src=url;
 try{await timed(im.decode(),12000,'Tempo excedido ao desenhar SVG.',signal);if(!im.naturalWidth||!im.naturalHeight)throw Error('SVG sem dimensões.');return im;}finally{URL.revokeObjectURL(url);}
}
async function openImage(file,signal){const im=new Image();im.src='/api/media/image?file='+encodeURIComponent(file);await timed(im.decode(),15000,'Imagem não carregada: '+file,signal);return im;}
function eventReady(el,event,ready,signal){return timed(new Promise((resolve,reject)=>{const ok=()=>{cleanup();resolve();},bad=()=>{cleanup();reject(Error('Mídia não decodificada: '+el.src));},cleanup=()=>{el.removeEventListener(event,ok);el.removeEventListener('error',bad);signal.removeEventListener('abort',bad);};el.addEventListener(event,ok,{once:true});el.addEventListener('error',bad,{once:true});signal.addEventListener('abort',bad,{once:true});if(ready())ok();}),15000,'Tempo excedido na leitura do clipe.',signal);}
async function openVideo(file,offset,loop,signal,resources){const v=document.createElement('video');resources.add(v);v.muted=true;v.playsInline=true;v.preload='auto';v.loop=loop;v.src='/api/media/clip?file='+encodeURIComponent(file);v.load();await eventReady(v,'loadeddata',()=>v.readyState>=2,signal);if(!Number.isFinite(v.duration)||v.duration<=0)throw Error('Duração de clipe desconhecida: '+file);const target=sourceTime(offset,v.duration,loop);if(target!==null&&Math.abs(v.currentTime-target)>.025){v.currentTime=target;await eventReady(v,'seeked',()=>!v.seeking&&v.readyState>=2,signal);}return v;}
function drawMedia(ctx,canvas,im,p,fit){const w=p.w*canvas.width,h=p.h*canvas.height;const args=boxFit(im.videoWidth||im.naturalWidth,im.videoHeight||im.naturalHeight,w,h,fit);if(!args)return;ctx.save();ctx.translate(p.x*canvas.width,p.y*canvas.height);ctx.transform(...affine(p,w,h));ctx.globalAlpha=clamp(p.opacity,0,1);const stroke=canvasAppearance(ctx,w,h,p);ctx.drawImage(im,...args);stroke();ctx.restore();}
// Rasterizações assíncronas de SVG não interrompem o relógio de áudio. Atraso excessivo aborta.
function frameSlot(first){return {image:first,at:0,requested:0,pending:false,error:null};}
function requestFrame(slot,t,step,make,signal){if(slot.error)throw slot.error;if(t-slot.at>Math.max(.8,3*step))throw Error('Desenho SVG atrasado; reduza resolução/FPS de desenho.');if(slot.pending||t-slot.requested+1e-6<step)return;slot.pending=true;slot.requested=t;Promise.resolve().then(()=>make(t)).then(image=>{if(!signal.aborted){slot.image=image;slot.at=t;}},e=>{if(!signal.aborted)slot.error=e;}).finally(()=>{slot.pending=false;});}
function videoFrame(v,t,loop,state){const dest=sourceTime(t,v.duration,loop);if(dest===null){v.pause();return false;}if(state.error)throw state.error;if(v.error)throw Error('Falha durante a decodificação do vídeo.');if(!v.seeking){const diff=Math.abs(v.currentTime-dest),drift=loop?Math.min(diff,Math.abs(v.duration-diff)):diff;if(drift>.30)v.currentTime=dest;}
 if(v.paused&&!state.pending){state.pending=true;v.play().catch(e=>{if(e.name!=='AbortError')state.error=e;}).finally(()=>{state.pending=false;});}
 if(v.readyState<2||v.seeking){if(state.waitSince===undefined)state.waitSince=performance.now();if(performance.now()-state.waitSince>800)throw Error('Clipe atrasado na exportação.');}else state.waitSince=undefined;return true;}
async function prepareEntry(e,p,signal,videos){const c=e.scene,{objetos_midia,gil_nativo,componente_gil,...baseScene}=c,baseAt=async t=>svgImage(await (await response('/api/preview',{scene:baseScene,video:p.video,progress:Math.min(1,t/e.nominal),index:e.index,total:p.cenas.length},signal)).text(),signal);
 const target={...e,baseAt,base:frameSlot(await baseAt(0)),layers:[]};
 const old=c.video_clipe||{};if(old.arquivo)target.layers.push({kind:'video',obj:{x:old.x,y:old.y,w:old.w,h:old.h,opacity:old.opacidade,fit:old.fit,offset:old.inicio||0,loop:old.repetir},media:await openVideo(old.arquivo,old.inicio||0,old.repetir,signal,videos),state:{}});
 async function gil(o,native=false){const compiled=prepare(native?o.source:o.gil.source);if(compiled.cues)throw Error('A camada GIL possui som ainda não suportado.');const imageAt=async t=>{const offset=native?0:o.offset||0,at=native?frameTime(t,compiled.duration):o.loop?(t+offset)%compiled.duration:frameTime(t+offset,compiled.duration);return svgImage(compiled.frame(at),signal,{transparent:!o.opaque});};return {kind:'gil',obj:o,native,slot:frameSlot(await imageAt(0)),imageAt,sample:native?null:objectMotion(o)};}
 if(c.gil_nativo)target.layers.push(await gil(c.gil_nativo,true));
 for(const o of c.objetos_midia||[]){abortCheck(signal);if(o.kind==='gil')target.layers.push(await gil(o));else if(o.kind==='image'||o.kind==='video')target.layers.push({kind:o.kind,obj:o,sample:objectMotion(o),media:o.kind==='image'?await openImage(o.file,signal):await openVideo(o.file,o.offset||0,o.loop,signal,videos),state:{}});else throw Error('Objeto não suportado: '+o.kind);}
 return target;
}
function paint(ctx,canvas,e,t,settings,signal,initial=false){const held=initial||t>=e.nominal;t=Math.min(t,Math.max(0,e.nominal-1e-8));ctx.globalAlpha=1;ctx.fillStyle='#000';ctx.fillRect(0,0,canvas.width,canvas.height);requestFrame(e.base,t,1/settings.baseFPS,e.baseAt,signal);ctx.drawImage(e.base.image,0,0,canvas.width,canvas.height);
 for(const l of e.layers){const o=l.obj,local=l.native||!l.sample?t:localTime(o,t);if(local===null){l.media?.pause?.();continue;}
 const p=l.native?{...o,x:o.x,y:o.y,w:o.w,h:o.h,opacity:o.opacidade,rz:0}:l.sample?{...o,...rect(o,l.sample(local))}:o;
 if(l.kind==='gil'){requestFrame(l.slot,local,1/settings.gilFPS,l.imageAt,signal);drawMedia(ctx,canvas,l.slot.image,p,'contain');}else if(l.kind==='image'){drawMedia(ctx,canvas,l.media,p,o.fit);}else if(held){l.media.pause();if(sourceTime(local+(o.offset||0),l.media.duration,o.loop)!==null)drawMedia(ctx,canvas,l.media,p,o.fit);}else if(videoFrame(l.media,local+(o.offset||0),o.loop,l.state)){drawMedia(ctx,canvas,l.media,p,o.fit);}}
}
// Keep the final container bytes on local storage for long recordings. No re-encoding.
export async function outputSink(duration,type,storage=globalThis.navigator?.storage){
 const ext=type.includes('mp4')?'mp4':'webm';let dir=null,name=null,writer=null,chain=Promise.resolve(),queued=0,error=null,closed=false,bytes=0;const chunks=[];
 if(duration>120){
  if(!storage?.getDirectory)throw Error('Vídeo longo exige armazenamento local OPFS (Chrome/localhost).');
  const estimate=await storage.estimate?.();if(estimate&&Number.isFinite(estimate.quota)&&Number.isFinite(estimate.usage)&&estimate.quota-estimate.usage<duration*800000)throw Error('Espaço insuficiente para a gravação longa.');
  const root=await storage.getDirectory();dir=await root.getDirectoryHandle('estudio-exports',{create:true});name=crypto.randomUUID()+'.'+ext;
  try{writer=await (await dir.getFileHandle(name,{create:true})).createWritable();}catch(e){await dir.removeEntry(name).catch(()=>{});throw e;}
 }
 const cleanup=async()=>{if(dir&&name)await dir.removeEntry(name).catch(()=>{});};
 return {get error(){return error;},push(blob){if(closed||error||!blob.size)return;bytes+=blob.size;if(!writer){chunks.push(blob);return;}queued+=blob.size;if(queued>64*1024*1024){error=Error('Armazenamento não acompanha o codificador.');return;}chain=chain.then(async()=>{if(!error)await writer.write(blob);}).catch(e=>{error=e;}).finally(()=>{queued-=blob.size;});},
 async finish(){closed=true;await chain;if(error)throw error;if(!bytes)throw Error('Codificador não produziu arquivo.');if(writer){await writer.close();writer=null;const file=await (await dir.getFileHandle(name)).getFile();if(file.size!==bytes)throw Error('Arquivo local incompleto.');return {blob:file.slice(0,file.size,type),cleanup};}return {blob:new Blob(chunks,{type}),cleanup};},
 async abort(){closed=true;await chain;if(writer){try{await writer.abort();}catch{}writer=null;}chunks.length=0;await cleanup();}};
}
export async function exportBrowser(project,{canvas,status=()=>{},signal}={}){
 let settings=plan(project);if(!canvas?.captureStream||typeof MediaRecorder==='undefined')throw Error('Canvas.captureStream/MediaRecorder indisponíveis.');
 const AC=window.AudioContext||window.webkitAudioContext;if(!AC)throw Error('Web Audio indisponível.');
 const context=new AC(),videos=new Set(),prepared=new Map();const mediaController=new AbortController();const abortMedia=()=>mediaController.abort();signal.addEventListener('abort',abortMedia,{once:true});let rec=null,stream=null,audio=null,audioEl=null,mixToken=null,sink=null,success=false,raf=0,recError=null,stopped=null,hidden=false,abortRecording=null,wake=null;
 const visibility=()=>{if(document.hidden){hidden=true;abortRecording?.(Error('Página perdeu visibilidade. Repita mantendo a tela aberta.'));}};document.addEventListener('visibilitychange',visibility);
 try{
  // resume é disparado diretamente pelo gesto de exportar, antes de operações assíncronas.
  await timed(context.resume(),5000,'Não foi possível ativar Web Audio. Toque novamente em Exportar.',signal);abortCheck(signal);if(document.hidden)throw Error('Mantenha a página visível.');
  const {width,height,fps}=settings;canvas.width=width;canvas.height=height;const ctx=canvas.getContext('2d',{alpha:false});if(!ctx)throw Error('Canvas 2D indisponível.');
  status('Preparando mix de áudio, sem renderizar vídeo…');const r=await response('/api/browser-render/audio',{project,stream:true},signal);const manifest=await r.json();mixToken=manifest.token;
  if(!Array.isArray(manifest.durations)||manifest.durations.length!==project.cenas.length||!/^[0-9a-f]{32}$/.test(mixToken)||manifest.url!=='/api/browser-render/mix?token='+mixToken)throw Error('Servidor não informou a timeline/mix. Reinicie a versão correta.');
  settings=plan(project,manifest.durations);const {duration}=settings;const dest=context.createMediaStreamDestination();
  if(duration>120){audioEl=new Audio();audioEl.preload='auto';audioEl.src=manifest.url;audioEl.load();await eventReady(audioEl,'canplay',()=>audioEl.readyState>=3,signal);if(Math.abs(audioEl.duration-duration)>.025)throw Error('O mix não corresponde à duração efetiva.');context.createMediaElementSource(audioEl).connect(dest);}
  else{const mix=await fetch(manifest.url,{signal});if(!mix.ok)throw Error('Mix indisponível.');const buf=await context.decodeAudioData(await mix.arrayBuffer());if(Math.abs(buf.duration-duration)>.025)throw Error('O mix não corresponde à duração efetiva.');audio=context.createBufferSource();audio.buffer=buf;audio.connect(dest);}
  function preload(i){if(i>=settings.entries.length||prepared.has(i))return;const slot={entry:null,error:null,promise:null};prepared.set(i,slot);slot.promise=prepareEntry(settings.entries[i],project,mediaController.signal,videos).then(e=>{slot.entry=e;},e=>{slot.error=e;});}
  function release(i){const slot=prepared.get(i);for(const l of slot?.entry?.layers||[]){const v=l.media;if(l.kind==='video'&&v){v.pause();v.removeAttribute('src');v.load();videos.delete(v);}}prepared.delete(i);}
  function ready(i){const s=prepared.get(i);if(s?.error)throw s.error;if(!s?.entry)throw Error('Cena '+(i+1)+' ainda não carregada; reduza a complexidade ou aumente sua duração.');return s.entry;}
  status('Preparando primeiras cenas…');preload(0);preload(1);await Promise.all([...prepared.values()].map(x=>x.promise));ready(0);if(settings.entries.length>1)ready(1);
  abortCheck(signal);if(hidden)throw Error('A página perdeu visibilidade.');
  const captured=canvas.captureStream(fps);stream=new MediaStream([...captured.getVideoTracks(),...dest.stream.getAudioTracks()]);
  for(const mimeType of codecs()){try{rec=new MediaRecorder(stream,{mimeType,videoBitsPerSecond:6000000,audioBitsPerSecond:160000});break;}catch{}}
  if(!rec)throw Error('Nenhum codec de vídeo com áudio aceito pelo navegador.');
  const type=rec.mimeType;if(!type)throw Error('Codec não identificado.');sink=await outputSink(duration,type);rec.ondataavailable=e=>sink.push(e.data);rec.onerror=e=>{recError=e.error||Error('Erro do codificador.');};stopped=new Promise(resolve=>{rec.onstop=resolve;});
  let previous=null,frames=0,missed=0,last=-1;const totalFrames=Math.ceil(duration*fps);
  // Desenho inicial antes de iniciar a captura, inclusive no caso de clipe carregado.
  paint(ctx,canvas,ready(0),0,settings,mediaController.signal,true);
  try{wake=await navigator.wakeLock?.request('screen');}catch{}abortCheck(signal);if(hidden||document.hidden)throw Error('Mantenha a página visível.');
  rec.start(1000);const start=context.currentTime;if(audioEl){await timed(audioEl.play(),5000,'Navegador bloqueou o áudio longo. Verifique permissões e tente novamente.',signal);if(context.currentTime-start>.35)throw Error('Início do áudio longo atrasado.');}else audio.start(start);status('Gravando diretamente no navegador…');
  await new Promise((resolve,reject)=>{const onAbort=()=>finish(reject,Error('Exportação cancelada.'));function finish(fn,value){abortRecording=null;signal.removeEventListener('abort',onAbort);cancelAnimationFrame(raf);fn(value);}abortRecording=e=>finish(reject,e);signal.addEventListener('abort',onAbort,{once:true});
   function step(){try{abortCheck(signal);if(hidden||document.hidden)throw Error('Página perdeu visibilidade. Repita mantendo a tela aberta.');if(recError)throw recError;if(rec.state!=='recording')throw Error('Codificador interrompeu a gravação.');if(sink.error)throw sink.error;if(context.state!=='running')throw Error('Relógio de áudio suspenso.');const elapsed=context.currentTime-start;if(audioEl&&(audioEl.error||Math.abs(audioEl.currentTime-Math.min(duration,elapsed))>.35))throw Error('Áudio longo perdeu sincronização; exportação interrompida.');const t=Math.min(duration,Math.max(0,audioEl?(audioEl.ended?duration:audioEl.currentTime):elapsed));if(t>=duration){finish(resolve);return;}
    const n=Math.min(totalFrames-1,Math.floor(t*fps));if(n>last){missed+=Math.max(0,n-last-1);const wanted=atTime(settings.entries,t),e=ready(wanted.index);if(previous&&previous!==e){release(previous.index);preload(e.index+1);}previous=e;paint(ctx,canvas,e,t-e.start,settings,mediaController.signal);frames++;last=n;}
    if(n%Math.max(1,Math.round(fps/5))===0)status(`Exportando ${t.toFixed(1)} / ${duration.toFixed(1)} s · ${frames} quadros desenhados`);raf=requestAnimationFrame(step);
   }catch(e){finish(reject,e);}}raf=requestAnimationFrame(step);
  });
  missed+=Math.max(0,totalFrames-last-1);rec.stop();await timed(stopped,15000,'Codificador não finalizou.',signal);if(recError)throw recError;const output=await sink.finish();if(!output.blob.size)throw Error('Arquivo vazio.');success=true;return {...output,ext:type.includes('mp4')?'mp4':'webm',frames,missed,totalFrames};
 }finally{mediaController.abort();signal.removeEventListener('abort',abortMedia);cancelAnimationFrame(raf);document.removeEventListener('visibilitychange',visibility);if(rec&&rec.state!=='inactive')try{rec.stop();}catch{}if(!success&&sink)await sink.abort();try{audio?.stop();}catch{}if(audioEl){audioEl.pause();audioEl.removeAttribute('src');audioEl.load();}stream?.getTracks().forEach(t=>t.stop());for(const v of videos){v.pause();v.removeAttribute('src');v.load();}await context.close().catch(()=>{});await wake?.release().catch(()=>{});if(mixToken)void fetch('/api/browser-render/release',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({token:mixToken}),keepalive:true}).catch(()=>{});}
}
