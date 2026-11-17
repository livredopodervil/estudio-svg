// Optional desktop/system capture: browser permissions vary by device.
// On Android without getDisplayMedia, prefer the already supported canvas export.
(()=>{'use strict';
 const $=id=>document.getElementById(id);
 const record=$('recordScreen'),stop=$('stopScreen'),save=$('saveScreen');
 const name=new URL(location.href).searchParams.get('name')||'';
 $('browserExport').href='/?project='+encodeURIComponent(name);
 let stream=null,recorder=null,chunks=[],url=null;
 const say=message=>{$('msg').textContent=message;};
 if(!navigator.mediaDevices?.getDisplayMedia||!window.MediaRecorder){
   record.disabled=true;record.title='Seu navegador não permite capturar a tela. Use a exportação de vídeo no editor.';
   record.textContent='Captura de tela indisponível';
 }
 record.addEventListener('click',async()=>{
   if(recorder&&recorder.state!=='inactive')return;
   if(url){URL.revokeObjectURL(url);url=null;save.hidden=true;}
   try{
     stream=await navigator.mediaDevices.getDisplayMedia({video:{frameRate:30},audio:true});
     const type=['video/webm;codecs=vp9,opus','video/webm;codecs=vp8,opus','video/webm','video/mp4'].find(x=>MediaRecorder.isTypeSupported(x));
     recorder=new MediaRecorder(stream,type?{mimeType:type}:{ });
     chunks=[];recorder.ondataavailable=e=>{if(e.data.size)chunks.push(e.data);};
     recorder.onstop=()=>{
       stream?.getTracks().forEach(x=>x.stop());stream=null;
       const blob=new Blob(chunks,{type:recorder.mimeType||'video/webm'});chunks=[];
       if(!blob.size){say('A captura terminou sem dados.');return;}
       url=URL.createObjectURL(blob);save.href=url;save.download='captura-'+new Date().toISOString().slice(0,19).replace(/:/g,'-')+(blob.type.includes('mp4')?'.mp4':'.webm');save.hidden=false;
       say('Captura pronta para download. O áudio do dispositivo depende da permissão do navegador.');
       stop.hidden=true;record.disabled=false;
     };
     stream.getVideoTracks()[0]?.addEventListener('ended',()=>{if(recorder?.state==='recording')recorder.stop();},{once:true});
     recorder.start(1000);record.disabled=true;stop.disabled=false;stop.hidden=false;say('Gravando a superfície autorizada. Inicie a apresentação.');
   }catch(e){stream?.getTracks().forEach(x=>x.stop());stream=null;record.disabled=false;stop.hidden=true;say('Captura de tela não iniciada: '+e.message+'. No Android, use Exportar vídeo no editor.');}
 });
 stop.addEventListener('click',()=>{if(recorder?.state==='recording')recorder.stop();stop.disabled=true;});
 window.addEventListener('pagehide',()=>{if(recorder?.state==='recording')recorder.stop();stream?.getTracks().forEach(x=>x.stop());if(url)URL.revokeObjectURL(url);});
})();
