/* Estúdio SVG 2.7.3: user-initiated local microphone/camera capture and chunked upload.
   Nothing is recorded until the user clicks Start and grants permission. */
(()=>{'use strict';
const dialog=document.createElement('dialog');dialog.id='studioRecorder';
dialog.innerHTML=`<header class="recHead"><strong id="recTitle">Gravação local</strong><button id="recClose" type="button">Fechar</button></header>
<p>Som e vídeo são gravados no próprio navegador e enviados somente ao servidor local do Estúdio.</p>
<div class="recQuality"><label for="recNoise"><input type="checkbox" id="recNoise" checked> Reduzir eco e ruído (desmarque se distorcer a voz)</label>
<label for="recCameraFacing">Câmera <select id="recCameraFacing"><option value="environment">Traseira</option><option value="user">Frontal</option></select></label>
<label for="recVideoQuality">Resolução <select id="recVideoQuality"><option value="720">720p · padrão</option><option value="1080">1080p · qualidade alta</option></select></label></div>
<label id="recAudioOption"><input type="checkbox" id="recUseVoice" checked> Usar o áudio da câmera também como narração</label>
<video id="recPreview" autoplay muted playsinline controls></video>
<audio id="recAudioPreview" controls hidden></audio>
<div class="recBtns"><button id="recStart" type="button">● Iniciar gravação</button><button id="recStop" type="button" disabled>■ Parar</button><button id="recAccept" type="button" disabled>Usar gravação</button></div>
<p id="recStatus" role="status">Aguardando autorização do usuário.</p>`;
document.body.appendChild(dialog);
const css=document.createElement('style');css.textContent=`
#studioRecorder{width:min(94vw,680px);max-height:92dvh;overflow:auto;border:1px solid #a1775a;border-radius:14px;padding:14px;background:#28201c;color:#fff3e0}
#studioRecorder::backdrop{background:#050505bb}#studioRecorder .recHead{display:flex;justify-content:space-between;align-items:center;gap:12px}
#studioRecorder p{font-size:13px;color:#f2d6bb}#studioRecorder video{display:block;width:100%;max-height:55dvh;background:#100c0a;border-radius:10px;margin:12px auto}#studioRecorder audio{width:100%;margin:12px 0}#studioRecorder audio[hidden],#studioRecorder video[hidden]{display:none}
#studioRecorder .recBtns{display:flex;gap:8px;flex-wrap:wrap}#studioRecorder .recBtns button{flex:1}#studioRecorder input{vertical-align:middle}#studioRecorder .recQuality{display:flex;gap:12px;flex-wrap:wrap;padding:8px 0}
#studioRecorder .recQuality label{font-size:12px;color:#f5e0c7}#studioRecorder .recQuality select{background:#271b16;color:#fff;border:1px solid #a1775a;border-radius:6px;padding:5px}
`;document.head.appendChild(css);
const $=id=>document.getElementById(id);
let stream=null,recorder=null,parts=[],recorded=null,previewUrl=null,kind='audio',onFile=null,discard=false;
function status(s){$('recStatus').textContent=s;}
function stopTracks(){if(stream){stream.getTracks().forEach(t=>t.stop());stream=null;}}
function clearPreview(){if(previewUrl){URL.revokeObjectURL(previewUrl);previewUrl=null;}for(const id of ['recPreview','recAudioPreview']){$(id).pause();$(id).removeAttribute('src');$(id).load();} $('recAudioPreview').hidden=true;$('recPreview').srcObject=null;}
function reset(){stopTracks();clearPreview();parts=[];recorded=null;discard=false;$('recStart').disabled=false;$('recStop').disabled=true;$('recAccept').disabled=true;}
function close(){discard=true;if(recorder&&recorder.state!=='inactive')recorder.stop();reset();discard=true;dialog.close();}
$('recClose').onclick=close;dialog.addEventListener('cancel',e=>{e.preventDefault();close();});
function mimeType(){
 const list=kind==='video'?['video/webm;codecs=vp8,opus','video/webm','video/mp4']:
  ['audio/webm;codecs=opus','audio/webm','audio/mp4'];
 return list.find(s=>MediaRecorder.isTypeSupported(s))||'';
}
$('recStart').onclick=async()=>{
 if(!navigator.mediaDevices?.getUserMedia||typeof MediaRecorder==='undefined')return status('Este navegador não oferece gravação por MediaRecorder.');
 reset();try{
  const processed=$('recNoise').checked;
  const audio={echoCancellation:processed,noiseSuppression:processed,autoGainControl:processed,
     channelCount:{ideal:1},sampleRate:{ideal:48000}};
  const hd=kind==='video'&&$('recVideoQuality').value==='1080';
  const resolution=hd?{width:1920,height:1080}:{width:1280,height:720};
  const constraints=kind==='video'?{video:{width:{ideal:resolution.width},height:{ideal:resolution.height},
      frameRate:{ideal:30,max:30},facingMode:{ideal:$('recCameraFacing').value}},audio}:{audio};
  try{stream=await navigator.mediaDevices.getUserMedia(constraints);}
  catch(e){if(e.name==='OverconstrainedError'||e.name==='NotFoundError'){
      stream=await navigator.mediaDevices.getUserMedia(kind==='video'?{video:true,audio:true}:{audio:true});
    }else throw e;}
  const mime=mimeType(),options=mime?{mimeType:mime}:{};
  options.audioBitsPerSecond=160000;
  if(kind==='video')options.videoBitsPerSecond=hd?6000000:3500000;
  try{recorder=new MediaRecorder(stream,options);}
  catch(e){recorder=new MediaRecorder(stream,mime?{mimeType:mime}:{});}
  parts=[];discard=false;
  recorder.ondataavailable=e=>{if(e.data?.size>0)parts.push(e.data);};
  recorder.onerror=e=>status('Falha de gravação: '+(e.error?.message||'erro desconhecido'));
  recorder.onstop=()=>{
   stopTracks();if(discard)return;
   const type=recorder.mimeType||mime||'application/octet-stream';
   const blob=new Blob(parts,{type});parts=[];
   if(!blob.size){status('Nenhum dado foi gravado.');$('recStart').disabled=false;return;}
   const ext=type.includes('mp4')?(kind==='video'?'.mp4':'.m4a'):'.webm';
   recorded=new File([blob],kind==='video'?'camera'+ext:'narracao'+ext,{type});
   previewUrl=URL.createObjectURL(recorded);$('recPreview').srcObject=null;
   if(kind==='video'){$('recPreview').src=previewUrl;$('recPreview').muted=false;$('recPreview').controls=true;}
   else{$('recAudioPreview').hidden=false;$('recAudioPreview').src=previewUrl;}
   $('recAccept').disabled=false;$('recStart').disabled=false;status('Gravação pronta. Ouça ou assista antes de usar.');
  };
  $('recPreview').controls=false;$('recPreview').muted=true;
  if(kind==='video'){$('recPreview').srcObject=stream;}
  recorder.start(1000);$('recStart').disabled=true;$('recStop').disabled=false;
  status('Gravando. Toque em Parar para encerrar.');
 }catch(e){stopTracks();status('Não foi possível acessar o dispositivo: '+e.message);}
};
$('recStop').onclick=()=>{if(recorder?.state==='recording'){recorder.stop();$('recStop').disabled=true;status('Finalizando gravação…');}};
$('recAccept').onclick=async()=>{
 if(!recorded||!onFile)return;
 $('recAccept').disabled=true;status('Transferindo para o servidor local…');
 try{await onFile(recorded,kind==='video'&&$('recUseVoice').checked);close();}
 catch(e){status('Falha ao importar: '+e.message);$('recAccept').disabled=false;}
};
window.StudioRecorder={open(type,callback){if(dialog.open)throw Error('Já existe gravação aberta');reset();kind=type;onFile=callback;$('recTitle').textContent=type==='video'?'Gravar vídeo da câmera':'Gravar narração';$('recAudioOption').hidden=type!=='video';$('recCameraFacing').parentElement.hidden=type!=='video';$('recVideoQuality').parentElement.hidden=type!=='video';$('recPreview').hidden=type!=='video';status('Toque em Iniciar gravação e permita o acesso solicitado pelo Android.');dialog.showModal();}};
})();
