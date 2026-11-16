/* Estúdio SVG V3.5 experimental — gravação segmentada, teleprompter, qualidade de entrada.
   Módulo independente; não substitui arquivos de mídia e não grava até um gesto explícito.
   Autor do Estúdio SVG: Rogério Duarte. */
(()=>{
'use strict';
const old=window.StudioRecorder;
const d=document.createElement('dialog');d.id='studioRecorderV35';
d.innerHTML=`
<header class="r35head"><strong id="r35title">Gravação da cena</strong><button type="button" id="r35close">Fechar</button></header>
<p class="r35hint">Gravação local no navegador. Nada é capturado até você tocar em Preparar câmera ou Iniciar gravação.</p>
<div class="r35controls">
<label>Microfone <select id="r35profile"><option value="natural">Natural (sem processamento)</option><option value="clear">Voz tratada (eco e ruído)</option></select></label>
<label>Qualidade <select id="r35quality"><option value="96000">96 kbit/s</option><option value="160000">160 kbit/s</option><option value="256000" selected>256 kbit/s</option></select></label>
<label id="r35facingWrap">Câmera <select id="r35facing"><option value="environment">Traseira</option><option value="user">Frontal</option></select></label>
<label id="r35resolutionWrap">Resolução <select id="r35resolution"><option value="720">720p</option><option value="1080">1080p</option></select></label>
</div>
<section id="r35scriptSection"><div class="r35head"><b>Roteiro da cena</b><span id="r35scriptPosition"></span></div>
<textarea id="r35script" spellcheck="false" aria-label="Texto para acompanhar durante a gravação"></textarea>
<div class="r35head"><button type="button" id="r35previous">◀ Trecho anterior</button><button type="button" id="r35next">Próximo trecho ▶</button></div>
<p class="r35hint">Separe o roteiro por parágrafos para navegar entre trechos. A edição aqui não modifica o projeto original.</p></section>
<video id="r35video" playsinline muted hidden></video>
<audio id="r35listen" controls hidden></audio>
<label id="r35videoVoiceWrap"><input id="r35videoVoice" type="checkbox" checked> Usar também o áudio da câmera como narração</label>
<div class="r35head r35buttons"><button id="r35prepare" type="button">Preparar câmera</button><button id="r35start" type="button">● Gravar trecho</button><button id="r35stop" type="button" disabled>■ Encerrar trecho</button><button id="r35accept" type="button" disabled>Usar gravação</button></div>
<div id="r35parts" aria-label="Trechos gravados"></div>
<p id="r35status" role="status">Aguardando início manual.</p>`;
const css=document.createElement('style');css.textContent=`
#studioRecorderV35{border:1px solid #8f755f;color:#f9eadc;background:#221c1a;width:min(96vw,760px);max-height:94dvh;overflow:auto;border-radius:13px;padding:13px}
#studioRecorderV35::backdrop{background:#000c}#studioRecorderV35 .r35head{display:flex;justify-content:space-between;align-items:center;gap:8px;flex-wrap:wrap;margin-bottom:8px}
#studioRecorderV35 button,#studioRecorderV35 select{background:#40352e;color:#fff;border:1px solid #a18a78;border-radius:7px;padding:8px;font:inherit}
#studioRecorderV35 button:disabled{opacity:.45}#studioRecorderV35 .r35controls{display:flex;flex-wrap:wrap;gap:10px;margin:10px 0}#studioRecorderV35 .r35controls label{display:flex;flex-direction:column;gap:5px;font-size:13px}
#studioRecorderV35 #r35script{display:block;width:100%;height:clamp(130px,23dvh,250px);font:clamp(17px,3.6vw,25px)/1.6 system-ui,sans-serif;background:#111719;color:#f5f3e8;border:1px solid #8b9fa7;border-radius:8px;padding:13px;resize:vertical}
#studioRecorderV35 #r35video{width:100%;max-height:40dvh;background:#090909;border-radius:8px}#studioRecorderV35 #r35video[hidden],#studioRecorderV35 #r35listen[hidden]{display:none}
#studioRecorderV35 #r35listen{width:100%;margin:10px 0}#studioRecorderV35 #r35parts{display:flex;flex-direction:column;gap:8px;margin:10px 0}
#studioRecorderV35 .r35part{display:flex;flex-wrap:wrap;gap:7px;align-items:center;border:1px solid #605349;border-radius:7px;padding:7px}
#studioRecorderV35 #r35status{font-size:13px;color:#f3d5aa;white-space:pre-wrap}
#studioRecorderV35 .r35hint{font-size:12px;color:#d4c4b6}#studioRecorderV35 .r35buttons{margin-top:12px}#studioRecorderV35 [hidden]{display:none!important}`;
document.head.appendChild(css);document.body.appendChild(d);
const $=id=>d.querySelector('#'+id);
const stat=msg=>{$('r35status').textContent=msg;};
let kind='audio',commit=null,stream=null,recorder=null,chunks=[],parts=[],videoFile=null,previewUrl=null;
let started=0,clock=null,opening=false,closing=false,skipResult=false,partIndex=0;
function tracksOff(){if(stream){for(const track of stream.getTracks())track.stop();stream=null;} $('r35video').srcObject=null;}
function revokePreview(){if(previewUrl){URL.revokeObjectURL(previewUrl);previewUrl=null;}const a=$('r35listen');a.pause();a.removeAttribute('src');a.hidden=true;}
function cleanup(){clearInterval(clock);clock=null;tracksOff();revokePreview();for(const p of parts)URL.revokeObjectURL(p.url);parts=[];videoFile=null;chunks=[];recorder=null;}
function switchUI(){const busy=recorder&&recorder.state!=='inactive';$('r35start').disabled=!!busy||opening||closing|| (kind==='video'&&!!videoFile);
 $('r35stop').disabled=!busy;$('r35prepare').disabled=kind!=='video'||busy||opening||!!stream;
 $('r35accept').disabled=!!busy||opening||closing||(kind==='audio'?!parts.length:!videoFile);
 $('r35start').textContent=kind==='audio'?'● Gravar trecho':'● Iniciar vídeo';
 $('r35prepare').hidden=kind!=='video';$('r35facingWrap').hidden=kind!=='video';$('r35resolutionWrap').hidden=kind!=='video';
 $('r35video').hidden=kind!=='video';$('r35videoVoiceWrap').hidden=kind!=='video';$('r35parts').hidden=kind==='video';
}
function refuseClose(){if(recorder&&recorder.state!=='inactive'&&!confirm('Descartar a gravação em andamento?'))return;skipResult=true;
 try{if(recorder&&recorder.state!=='inactive')recorder.stop();}catch(_){} cleanup();d.close();}
$('r35close').addEventListener('click',refuseClose);
d.addEventListener('cancel',e=>{e.preventDefault();refuseClose();});
function getParagraphs(){return $('r35script').value.split(/\n\s*\n/).map(s=>s.trim()).filter(Boolean);}
function focusParagraph(){const t=$('r35script'),list=getParagraphs();if(!list.length){$('r35scriptPosition').textContent='Roteiro vazio';return;}
 partIndex=Math.max(0,Math.min(partIndex,list.length-1));$('r35scriptPosition').textContent=`Parágrafo ${partIndex+1}/${list.length}`;
 const text=t.value,fragment=list[partIndex],index=text.indexOf(fragment);if(index>=0){
  const line=text.slice(0,index).split('\n').length,total=Math.max(1,text.split('\n').length);
  t.scrollTop=Math.max(0,t.scrollHeight*line/total-t.clientHeight*.15);}}
$('r35previous').onclick=()=>{partIndex--;focusParagraph();};$('r35next').onclick=()=>{partIndex++;focusParagraph();};
$('r35script').addEventListener('input',()=>{partIndex=0;$('r35scriptPosition').textContent='Roteiro editado para gravação';});
function mimeFor(type){const arr=type==='video'?['video/webm;codecs=vp8,opus','video/webm','video/mp4']:
 ['audio/webm;codecs=opus','audio/webm','audio/mp4','audio/ogg;codecs=opus'];
 return arr.find(s=>window.MediaRecorder?.isTypeSupported(s))||'';}
function constraints(){const processed=$('r35profile').value==='clear';const audio={echoCancellation:processed,noiseSuppression:processed,autoGainControl:processed,
 sampleRate:{ideal:48000},channelCount:{ideal:1}};
 if(kind==='audio')return {audio};const hd=$('r35resolution').value==='1080';return {audio,video:{
 width:{ideal:hd?1920:1280},height:{ideal:hd?1080:720},frameRate:{ideal:30,max:30},facingMode:{ideal:$('r35facing').value}}};}
async function ensureStream(){if(stream)return stream;
 if(!navigator.mediaDevices?.getUserMedia)throw Error('Este navegador não oferece captura de microfone/câmera.');
 try{stream=await navigator.mediaDevices.getUserMedia(constraints());}
 catch(e){if(e.name!=='OverconstrainedError'&&e.name!=='NotFoundError')throw e;
   stream=await navigator.mediaDevices.getUserMedia(kind==='video'?{video:true,audio:true}:{audio:true});}
 if(kind==='video'){$('r35video').muted=true;$('r35video').controls=false;$('r35video').srcObject=stream;
   await $('r35video').play().catch(()=>{});}
 return stream;}
$('r35prepare').onclick=async()=>{if(opening||recorder?.state==='recording')return;opening=true;switchUI();
 try{await ensureStream();stat('Câmera preparada. Nenhum vídeo foi gravado. Toque em Iniciar vídeo.');}
 catch(e){stat('Falha ao preparar câmera: '+e.message);tracksOff();}
 finally{opening=false;switchUI();}};
function showAudioParts(){const area=$('r35parts');area.replaceChildren();for(let i=0;i<parts.length;i++){
 const p=parts[i],row=document.createElement('div');row.className='r35part';
 const title=document.createElement('span');title.textContent=`Trecho ${i+1} · ${(p.blob.size/1024).toFixed(0)} KB`;
 const hear=document.createElement('button');hear.type='button';hear.textContent='▶ Ouvir';hear.onclick=()=>{revokePreview();previewUrl=URL.createObjectURL(p.blob);
   $('r35listen').hidden=false;$('r35listen').src=previewUrl;$('r35listen').play().catch(e=>stat(e.message));};
 const del=document.createElement('button');del.type='button';del.textContent='Excluir';del.onclick=()=>{
   if(recorder?.state==='recording')return;URL.revokeObjectURL(p.url);parts.splice(i,1);showAudioParts();switchUI();};
 row.append(title,hear,del);area.append(row);} }
$('r35start').onclick=async()=>{
 if(!window.MediaRecorder||opening||closing||recorder?.state==='recording'||(kind==='video'&&videoFile))return;
 opening=true;switchUI();skipResult=false;
 try{await ensureStream();const mime=mimeFor(kind),quality=Number($('r35quality').value);
   const opts={audioBitsPerSecond:quality};if(mime)opts.mimeType=mime;
   if(kind==='video')opts.videoBitsPerSecond=$('r35resolution').value==='1080'?6000000:3500000;
   try{recorder=new MediaRecorder(stream,opts);}catch(_){recorder=new MediaRecorder(stream,mime?{mimeType:mime}:{});}
   chunks=[];recorder.ondataavailable=e=>{if(e.data?.size)chunks.push(e.data);};
   recorder.onerror=e=>stat('Erro de gravação: '+(e.error?.message||'erro desconhecido'));
   recorder.onstop=()=>{clearInterval(clock);clock=null;tracksOff();if(skipResult)return;
     const type=recorder.mimeType||mime||'application/octet-stream';const blob=new Blob(chunks,{type});chunks=[];
     if(!blob.size){stat('Não foram registrados dados.');recorder=null;switchUI();return;}
     if(kind==='audio'){
       parts.push({blob,url:URL.createObjectURL(blob)});showAudioParts();stat(`${parts.length} trecho(s) salvo(s) em memória. Pode gravar outro trecho ou usar a gravação.`);
     }else{
       const ext=type.includes('mp4')?'.mp4':'.webm';videoFile=new File([blob],'camera'+ext,{type});
       const v=$('r35video');v.srcObject=null;v.muted=false;v.controls=true;v.src=URL.createObjectURL(blob);
       stat('Vídeo finalizado. Assista e escolha Usar gravação.');
     }
     recorder=null;switchUI();};
   recorder.start(1000);started=performance.now();clock=setInterval(()=>{
     const elapsed=(performance.now()-started)/1000;stat(`Gravando ${elapsed.toFixed(1)} s.\nFonte: ${stream?.getAudioTracks()[0]?.getSettings()?.sampleRate||'padrão do navegador'} Hz · solicitado ${Math.round(quality/1000)} kbit/s.`);
   },500);
   stat('Gravando. O roteiro permanece disponível acima.');
 }catch(e){tracksOff();stat('Não foi possível começar: '+e.message);}
 finally{opening=false;switchUI();}};
$('r35stop').onclick=()=>{if(recorder&&recorder.state==='recording'){
 $('r35stop').disabled=true;recorder.stop();stat('Finalizando trecho…');}};
async function mergeWav(takes){const C=window.AudioContext||window.webkitAudioContext;if(!C)throw Error('Web Audio não disponível; use uma única gravação.');
 const ctx=new C({sampleRate:48000});let decoded=[];
 try{for(const t of takes)decoded.push(await ctx.decodeAudioData(await t.blob.arrayBuffer()));}
 finally{await ctx.close();}
 if(!decoded.length)throw Error('Nenhum trecho.');const rate=decoded[0].sampleRate;
 if(decoded.some(b=>b.sampleRate!==rate))throw Error('Os trechos possuem taxas de amostragem diferentes; exporte-os separadamente.');
 const channels=Math.min(2,Math.max(...decoded.map(b=>b.numberOfChannels)));
 const frames=decoded.reduce((n,b)=>n+b.length,0);
 if(frames*channels*2>160_000_000)throw Error('Gravação longa demais para unir no navegador. Divida o roteiro em cenas.');
 const bytes=new ArrayBuffer(44+frames*channels*2),v=new DataView(bytes);const four=(i,s)=>{for(let k=0;k<s.length;k++)v.setUint8(i+k,s.charCodeAt(k));};
 four(0,'RIFF');v.setUint32(4,36+frames*channels*2,true);four(8,'WAVE');four(12,'fmt ');
 v.setUint32(16,16,true);v.setUint16(20,1,true);v.setUint16(22,channels,true);v.setUint32(24,rate,true);
 v.setUint32(28,rate*channels*2,true);v.setUint16(32,channels*2,true);v.setUint16(34,16,true);
 four(36,'data');v.setUint32(40,frames*channels*2,true);let offset=44;
 for(const b of decoded){for(let j=0;j<b.length;j++)for(let c=0;c<channels;c++){
   const samples=b.getChannelData(Math.min(c,b.numberOfChannels-1));const val=Math.max(-1,Math.min(1,samples[j]));
   v.setInt16(offset,val<0?Math.round(val*32768):Math.round(val*32767),true);offset+=2;}}
 return new File([bytes],'narracao_em_trechos.wav',{type:'audio/wav'});}
$('r35accept').onclick=async()=>{if(closing||opening||recorder?.state==='recording'||!commit)return;
 closing=true;switchUI();stat('Preparando arquivo e importando para o projeto…');
 try{let file;
  if(kind==='video'){if(!videoFile)throw Error('Sem vídeo gravado');file=videoFile;}
  else if(parts.length===1){const b=parts[0].blob;const ext=b.type.includes('mp4')?'.m4a':b.type.includes('ogg')?'.ogg':'.webm';file=new File([b],'narracao'+ext,{type:b.type});}
  else if(parts.length>1){file=await mergeWav(parts);}
  else throw Error('Sem áudio gravado');
  await commit(file,kind==='video'&&$('r35videoVoice').checked);
  cleanup();d.close();
 }catch(e){stat('Erro: '+e.message+' · Gravações preservadas nesta janela.');}
 finally{closing=false;switchUI();}};
window.StudioRecorder={
 open(type,onFile,options={}){
  if(d.open)throw Error('Já existe uma janela de gravação aberta.');
  if(type!=='audio'&&type!=='video')return old?.open(type,onFile);
  cleanup();$('r35parts').replaceChildren();$('r35video').pause();$('r35video').removeAttribute('src');
  kind=type;commit=onFile;partIndex=0;skipResult=false;opening=false;closing=false;
  $('r35title').textContent=type==='video'?'Gravação de vídeo da cena':'Gravação de narração em trechos';
  $('r35script').value=String(options?.script||'');$('r35scriptSection').hidden=!$('r35script').value.trim();
  $('r35video').hidden=type!=='video';$('r35video').muted=true;$('r35video').controls=false;
  $('r35profile').value='natural';$('r35quality').value='256000';
  stat('Pronto. Toque em Gravar trecho. Nenhuma captura foi iniciada.');switchUI();d.showModal();focusParagraph();
 }
};
})();
