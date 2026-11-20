// Estúdio SVG · M1O · exportação por quadros com retomada no servidor local.
// Quadro n representa t=n/fps, independentemente da velocidade do aparelho.
import {plan,atTime,prepareEntry,paintOffline,collectGILAudioEvents} from './browser-render.mjs';
import {prepare} from './gil-native.mjs';
import {withDeadline} from './studio-preparation-deadline.mjs';

async function postJSON(path,body,signal){
 const response=await fetch(path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body),signal});
 let payload;try{payload=await response.json();}catch{throw Error('Servidor offline respondeu sem JSON: HTTP '+response.status);}
 if(!response.ok)throw Error(payload.error||'HTTP '+response.status);
 return payload;
}
function stopIfAborted(signal){if(signal?.aborted)throw Error('Renderização interrompida. Os quadros já salvos continuam disponíveis para retomada.');}
async function pngFrame(canvas,signal){
 stopIfAborted(signal);
 const blob=await new Promise((resolve,reject)=>canvas.toBlob(b=>b?resolve(b):reject(Error('Canvas não gerou PNG')), 'image/png'));
 stopIfAborted(signal);
 if(blob.type!=='image/png')throw Error('O navegador não produziu um quadro PNG');
 return blob;
}
function scaledProject(project,quality){
 const p=structuredClone(project);const w=p.video.width,h=p.video.height;
 if(quality==='1080p'){
  const scale=Math.min(1920/w,1920/h);
  p.video.width=Math.max(320,Math.round(w*scale/2)*2);
  p.video.height=Math.max(320,Math.round(h*scale/2)*2);
 }else if(quality!=='native')throw Error('Qualidade de exportação desconhecida');
 return p;
}
export function outputDimensions(video,quality='native'){
 return scaledProject({video},quality).video;
}
export async function exportOffline(project,{canvas,quality='1080p',status=()=>{},signal}={}){
 if(!canvas?.getContext||typeof canvas.toBlob!=='function')throw Error('Canvas PNG indisponível.');
 const p=scaledProject(project,quality);
 // Um mundo ainda presente na sessão WebGL não equivale a uma fonte salva no projeto.
 const emptySource=p.cenas.findIndex(c=>c.spatialseed_viewport?.enabled && !(c.spatialseed_viewport.source||'').trim());
 if(emptySource>=0)throw Error(`Cena ${emptySource+1}: documento SpatialSeed vazio. Salve/importe o .spatialseed no projeto antes de exportar; a sessão WebGL pode mostrar objetos não persistidos.`);
 const preplan=plan(p);
 const metrics={draw_ms:0,png_ms:0,upload_ms:0,server_encode_ms:0,frames_rendered:0};
 const videos=new Set();let entry=null,entryIndex=-1;
 function release(){
  if(entry)for(const layer of entry.layers){
   if(layer.kind==='video'){
    const video=layer.media;video.pause();video.removeAttribute('src');video.load();videos.delete(video);
   }
  }
  entry=null;entryIndex=-1;
 }
 try{
  status('Verificando narrações e timeline…');
  const timing=await postJSON('/api/offline-export/plan',{project:p},signal);
  const settings=plan(p,timing.durations);
  const events=collectGILAudioEvents(settings.entries,prepare);
  stopIfAborted(signal);
  status('Abrindo sessão recuperável no Termux…');
  const job=await postJSON('/api/offline-export/start',{project:p,gil_audio:events},signal);
  if(job.frames!==Math.ceil(settings.duration*settings.fps-1e-9)||job.width!==settings.width||job.height!==settings.height)throw Error('Plano do servidor difere da composição.');
  canvas.width=job.width;canvas.height=job.height;
  const ctx=canvas.getContext('2d',{alpha:false,willReadFrequently:false});
  if(!ctx)throw Error('Não foi possível obter Canvas 2D');
  let next=job.next_frame;
  if(job.resumed)status(`Retomada: ${next}/${job.frames} quadros já persistidos.`);
  let lastReport=0;
  while(next<job.frames){
   stopIfAborted(signal);
   const t=next/job.fps;
   const wanted=atTime(settings.entries,Math.min(t,settings.duration-1e-8));
   if(wanted.index!==entryIndex){
    release();
    status(`Preparando cena ${wanted.index+1}/${settings.entries.length}…`);
    entry=await withDeadline(`Cena ${wanted.index+1}: preparação de camadas`,taskSignal=>prepareEntry(wanted,p,taskSignal,videos,{onPhase:status}),{signal,ms:60000});
    entryIndex=wanted.index;
   }
   const d=performance.now();
   await withDeadline(`Cena ${wanted.index+1}: quadro ${next}`,taskSignal=>paintOffline(ctx,canvas,entry,t-wanted.start,settings,taskSignal),{signal,ms:60000});
   metrics.draw_ms+=performance.now()-d;
   const b=performance.now();const png=await pngFrame(canvas,signal);metrics.png_ms+=performance.now()-b;
   const u=performance.now();
   const r=await fetch(`/api/offline-export/frame?token=${encodeURIComponent(job.token)}&index=${next}`,{
    method:'POST',headers:{'Content-Type':'image/png'},body:png,signal
   });
   let result;try{result=await r.json();}catch{throw Error('Servidor não confirmou o quadro '+next);}
   if(!r.ok)throw Error(result.error||'Erro HTTP '+r.status);
   if(result.next_frame!==next+1)throw Error('Servidor registrou sequência inesperada de quadros.');
   metrics.upload_ms+=performance.now()-u;
   if(result.encoded_chunk)metrics.server_encode_ms+=result.request_seconds*1000;
   metrics.frames_rendered++;
   next=result.next_frame;
   const now=performance.now();
   if(now-lastReport>350||next===job.frames){
    status(`Offline ${next}/${job.frames} quadros · ${Math.round(100*next/job.frames)}% · ${job.width}×${job.height} · ${job.fps} FPS · salvo no Termux`);
    lastReport=now;
   }
  }
  release();stopIfAborted(signal);
  status(`Validando ${job.frames} quadros e multiplexando áudio…`);
  const complete=await postJSON('/api/offline-export/finish',{token:job.token},signal);
  if(complete.stats?.encoded_frames!==job.frames)throw Error('Arquivo final não confirmou todos os quadros codificados.');
  status(`Concluído: ${job.frames}/${job.frames} quadros · ${job.fps} FPS · áudio AAC · ${job.width}×${job.height}`);
  return {url:complete.url,filename:complete.file,bytes:complete.bytes,frames:job.frames,
          fps:job.fps,stats:{...metrics,...complete.stats},resumed:job.resumed};
 }finally{
  release();for(const v of videos){v.pause();v.removeAttribute('src');v.load();}
 }
}
