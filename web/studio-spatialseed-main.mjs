// M1W: usa o motor e a linguagem ORIGINAL do SpatialSeed main.
// As operações de captura são do navegador e passam pelo upload existente.
const $=id=>document.getElementById(id);
const dialog=$('ssStudioOverlay'),frame=$('ssStudioFrame'),output=$('ssStudioStatus');
const open=$('openSpatialSeedMain'),file=$('ssStudioFile'),record=$('ssStudioRecord'),stop=$('ssStudioStop');
let started=false,activeRecorder=null,stopping=false;
function report(message){output.textContent=String(message);}
function inner(){
 const w=frame.contentWindow;
 if(!w||w.location.origin!==location.origin)throw Error('Renderer não está na origem local do Estúdio.');
 return w;
}
function ready(){
 const w=inner(),app=w.__SPATIAL_SEED__,canvas=w.document.getElementById('world');
 if(!app||!canvas)throw Error('SpatialSeed ainda não inicializado. Verifique mensagens do servidor.');
 return {w,app,canvas};
}
open.addEventListener('click',async()=>{
 dialog.hidden=false;
 if(!started){
  started=true;
  frame.src='/spatialseed-main/apps/web/?project=new';
  report('Carregando WebGL, editor, linguagens e módulos do SpatialSeed main...');
 }
});
$('ssStudioClose').addEventListener('click',()=>{
 if(activeRecorder){report('Finalize a gravação antes de fechar.');return;}
 dialog.hidden=true;
});
frame.addEventListener('load',()=>{
 let tries=0;
 const poll=()=>{
  if(!started)return;
  try{
   const {app}=ready();
   report('SpatialSeed '+app.build+' · WebGL e console nativos carregados. Abra um projeto, edite ou capture a cena.');
  }catch(error){
   if(++tries<30)setTimeout(poll,350);
   else report('Falha de inicialização: '+error.message);
  }
 };
 poll();
});
$('ssStudioOpenProject').addEventListener('click',()=>file.click());
file.addEventListener('change',async()=>{
 const f=file.files?.[0];file.value='';if(!f)return;
 try{
  const {w}=ready();
  if(f.size>20_000_000||!f.size)throw Error('Arquivo .spatialseed inválido ou acima de 20 MB.');
  const target=w.document.getElementById('project-file-input');
  if(!target)throw Error('Seletor de projeto ausente no SpatialSeed main.');
  // Usamos o mesmo manipulador público de abertura do SpatialSeed.
  const dt=new w.DataTransfer();
  dt.items.add(new w.File([await f.arrayBuffer()],f.name,{type:'application/json'}));
  target.files=dt.files;
  target.dispatchEvent(new w.Event('change',{bubbles:true}));
  report('Arquivo entregue ao importador nativo. Verifique o resultado no viewport.');
 }catch(error){report('Falha ao abrir: '+error.message);}
});
$('ssStudioSaveProject').addEventListener('click',()=>{
 try{const {w}=ready();w.document.getElementById('project-save')?.click();}
 catch(error){report(error.message);}
});
$('ssStudioConsole').addEventListener('click',()=>{
 try{const {w}=ready();w.document.getElementById('console')?.click();}
 catch(error){report(error.message);}
});
function capNumber(id,min,max){
 const v=Number($(id).value);
 if(!Number.isFinite(v)||v<min||v>max)throw Error(`Valor inválido em ${id}: ${v}`);
 return v;
}
function mime(){
 for(const m of ['video/webm;codecs=vp9','video/webm;codecs=vp8','video/webm'])
  if(MediaRecorder.isTypeSupported(m))return m;
 throw Error('O navegador não oferece gravação WebM por MediaRecorder.');
}
record.addEventListener('click',async()=>{
 if(activeRecorder)return;
 let stream=null;
 try{
  const {canvas}=ready();
  if(!canvas.captureStream||typeof MediaRecorder==='undefined')throw Error('Captura de canvas não suportada pelo navegador.');
  const seconds=capNumber('ssStudioSeconds',1,60),fps=capNumber('ssStudioFps',12,30);
  if(!canvas.width||!canvas.height)throw Error('Canvas WebGL sem dimensões.');
  if(typeof window.StudioSpatialSeedAttachClip!=='function')throw Error('Ponte de mídia do Estúdio indisponível; recarregue a página.');
  stream=canvas.captureStream(fps);
  const chunks=[],recorder=new MediaRecorder(stream,{mimeType:mime(),videoBitsPerSecond:6_000_000});
  activeRecorder=recorder;stopping=false;
  record.disabled=true;stop.hidden=false;
  recorder.ondataavailable=e=>{if(e.data?.size)chunks.push(e.data);};
  recorder.onerror=e=>{report('Falha MediaRecorder: '+(e.error?.message||'desconhecida'));};
  recorder.onstop=async()=>{
   activeRecorder=null;record.disabled=false;stop.hidden=true;
   stream.getTracks().forEach(t=>t.stop());
   const blob=new Blob(chunks,{type:'video/webm'});
   if(!blob.size){report('Gravação sem quadros; nada inserido.');return;}
   const f=new File([blob],`spatialseed-main-${Date.now()}.webm`,{type:'video/webm'});
   report(`Gravação concluída (${(f.size/1048576).toFixed(1)} MB). Enviando para a cena selecionada...`);
   try{
    const result=await window.StudioSpatialSeedAttachClip(f);
    report(`Clipe 3D inserido na cena ${result.scene+1}: ${result.filename}. Salve o projeto.`);
   }catch(error){
    report('O vídeo foi produzido, mas não anexado: '+error.message+'. Baixe-o para não perder o resultado.');
    const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download=f.name;a.click();setTimeout(()=>URL.revokeObjectURL(a.href),20000);
   }
  };
  recorder.start(1000);
  report(`Capturando ${seconds}s do renderer WebGL original, ${fps} FPS. Use as animações nativas do SpatialSeed.`);
  setTimeout(()=>{if(activeRecorder===recorder&&!stopping){stopping=true;recorder.stop();}},seconds*1000);
 }catch(error){
  stream?.getTracks().forEach(t=>t.stop());
  activeRecorder=null;record.disabled=false;stop.hidden=true;
  report('Não foi possível gravar: '+error.message);
 }
});
stop.addEventListener('click',()=>{
 if(!activeRecorder||stopping)return;
 stopping=true;activeRecorder.stop();
});
window.addEventListener('keydown',e=>{
 if(e.key==='Escape'&&!dialog.hidden&&!activeRecorder){dialog.hidden=true;}
});
