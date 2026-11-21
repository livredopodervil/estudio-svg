// M1X SpatialSeed main — embedded WebGL world in the actual video viewport.
// Original ThreeRegionRenderer is owned by the SpatialSeed application; no Three.js copy.
import {sampleCameraTrack,validateKeyframes} from './spatialseed-camera-track.mjs';
import {mountSpatialSeedPanel} from './studio-spatialseed-panel.mjs';
const $=id=>document.getElementById(id);
const status=t=>{$('ssCameraStatus').textContent=t;};
const pause=ms=>new Promise(r=>setTimeout(r,ms));
const editableSource=s=>typeof s==='string'&&s.length>0;
function currentCamera(app){return app.query('viewer.camera.snapshot');}
function isEnabled(scene){return scene?.spatialseed_viewport?.enabled===true;}
export function mountStudioSpatialSeed({getScene,getAspect,getTime,getProjectId=()=>'',onEdit,onError}){
 const host=$('ssViewportHost'),frame=$('ssViewportFrame'),shell=$('stageShell');
 let lastDocument=null,readyPromise=null,active=false,loadingSerial=0,cameraSeq=0,previousTime=null,loadedKey='';
 let cameraFlight=null,cameraRequested=null,hudHidden=true;
 let exportActive=false,exportStream=null,exportVideo=null,exportCanvas=null,exportQueue=Promise.resolve(),exportPrevious=null;
 const cameraNumbers=['ssCamX','ssCamY','ssCamZ','ssCamFov'];
 const sceneKey=(scene,source)=>[getProjectId(),scene.id||'',source].join('\0');
 let bootGeneration=0;
 const nativeCapture=new WeakMap();
 function api(){
  const w=frame.contentWindow;
  if(!w||w.location.origin!==location.origin)throw Error('SpatialSeed não está na origem local.');
  const app=w.__SPATIAL_SEED__,canvas=w.document.getElementById('world');
  if(!app||typeof app.execute!=='function'||typeof app.query!=='function'||!canvas)throw Error('SpatialSeed ainda não inicializado.');
  return {w,app,canvas};
 }
 async function refreshCameraInputs(){
  try{const {app,canvas}=api(),c=await Promise.resolve(currentCamera(app));
   [c.position[0],c.position[1],c.position[2],c.fov].forEach((v,i)=>{$(cameraNumbers[i]).value=Number(v).toFixed(2);});
   if(!canvas.dataset.rdStudioCameraBound){canvas.dataset.rdStudioCameraBound='1';
    canvas.addEventListener('pointerup',()=>{void refreshCameraInputs();});}
  }catch{}
 }
 const panel=mountSpatialSeedPanel({getNative:()=>({document:api().w.document}),showError:onError});
 function embedCSS(){
  const {w}=api(),d=w.document;
  let s=d.getElementById('rdStudioEmbedStyle');if(!s){
   s=d.createElement('style');s.id='rdStudioEmbedStyle';
   s.textContent='html,body{margin:0!important;width:100%!important;height:100%!important;overflow:hidden!important}body > :not(#world){display:none!important}#world{display:block!important;position:fixed!important;inset:0!important;width:100vw!important;height:100vh!important;max-width:none!important;max-height:none!important;touch-action:none!important}';
   d.head.append(s);
  }
  s.disabled=!hudHidden; // 'Show HUD' restores original controls when needed
 }
 async function boot(){
  if(readyPromise)return readyPromise;
  const generation=++bootGeneration;
  const url=new URL('/spatialseed-main/apps/web/?project=new&rd-studio-viewport=1',location.href);
  url.searchParams.set('mount',String(generation));
  url.searchParams.set('sandbox','sandbox-'+crypto.randomUUID());
  frame.src=url.href;
  readyPromise=(async()=>{
   const deadline=Date.now()+20000;
   while(Date.now()<deadline){
    if(generation!==bootGeneration)throw Error('Carregamento anterior substituído.');
    try{
     const result=api();
     if(new URL(result.w.location.href).searchParams.get('mount')===String(generation)){embedCSS();return result;}
    }catch{}
    await pause(250);
   }
   throw Error('SpatialSeed não inicializou. Verifique RD_SPATIALSEED_ROOT e os módulos do main.');
  })().catch(e=>{if(generation===bootGeneration){readyPromise=null;status(e.message);}throw e;});
  return readyPromise;
 }
 async function openSource(source,token){
  const {app}=await boot();
  if(token!==loadingSerial||!editableSource(source))return;
  const opened=await app.execute('project.open',{text:source});
  if(!opened?.loaded)throw Error('SpatialSeed recusou o documento.');
 }
 async function cameraAt(scene,time,aspect,token){
  const {app}=await boot();if(token!==loadingSerial)return;
  time=Math.max(0,Math.min(time,scene.duracao));
  const domain=app.query('time.domain',{id:'world'});
  if(!domain.paused)await app.execute('time.domain.pause',{id:'world'});
  const result=await app.execute('time.domain.seek',{id:'world',localTime:time});
  if(!result?.domain?.paused||!Number.isFinite(result.domain.localTime)||Math.abs(result.domain.localTime-time)>1e-7)
   throw Error('SpatialSeed não confirmou o instante solicitado.');
  if(token!==loadingSerial)return;
  const keys=scene?.spatialseed_viewport?.camera_keys||[];
  if(!keys.length){previousTime=time;return;}
  const pose=sampleCameraTrack(keys,Math.max(0,time),aspect);
  const serial=++cameraSeq;
  await Promise.resolve(app.execute('viewer.camera.restore',{camera:pose}));
  if(serial!==cameraSeq)return;
  [pose.position[0],pose.position[1],pose.position[2],pose.fov].forEach((v,i)=>{const el=$(cameraNumbers[i]);if(document.activeElement!==el)el.value=Number(v).toFixed(2);});
  previousTime=time;
 }
 // At most one camera command in flight. Late playhead positions supersede
 // intermediate positions; no unbounded promises or out-of-order camera poses.
 function scheduleCamera(scene,time,aspect,token){
  cameraRequested={scene,time,aspect,token};
  if(cameraFlight)return;
  async function drain(){
   while(cameraRequested){
    const request=cameraRequested;cameraRequested=null;
    if(request.token!==loadingSerial)continue;
    try{await cameraAt(request.scene,request.time,request.aspect,request.token);}
    catch(e){status('Câmera: '+e.message);}
   }
  }
  cameraFlight=drain().finally(()=>{cameraFlight=null;if(cameraRequested){const q=cameraRequested;scheduleCamera(q.scene,q.time,q.aspect,q.token);}});
 }
 async function loadDocument(scene,resetWorld=false){
  const serial=++loadingSerial;
  const source=scene?.spatialseed_viewport?.source||'';
  if(readyPromise && resetWorld){
   // Switching scenes must not retain the previous SpatialSeed world.
   frame.src='about:blank';readyPromise=null;previousTime=null;lastDocument=null;
   cameraRequested=null;
  }
  if(!readyPromise)await boot();
  if(serial!==loadingSerial)return;
  if(source!==lastDocument){
   await openSource(source,serial);
   if(serial!==loadingSerial)return;
   lastDocument=source;
  }
  if(serial!==loadingSerial)return;
  await cameraAt(scene,getTime(),getAspect(),serial);
  await refreshCameraInputs();
  status('SpatialSeed main · WebGL ativo · câmera da timeline.');
 }
 let pending=null;
 function sync(scene,time,aspect){
  if(exportActive)return;
  const enabled=isEnabled(scene);
  host.hidden=!enabled;shell.classList.toggle('ss-webgl-active',enabled);
  $('ssViewportToggle').setAttribute('aria-pressed',String(enabled));
  $('ssViewportToggle').textContent=enabled?'◈ WebGL ativo':'◈ Ativar WebGL nesta cena';
  if(!enabled){if(!readyPromise||lastDocument===null)loadedKey='';active=false;previousTime=null;return;}
  active=true;
  const source=scene.spatialseed_viewport.source||'';
  const key=sceneKey(scene,source);
  if(key!==loadedKey){const resetWorld=loadedKey!=='';loadedKey=key;
   const request=loadDocument(scene,resetWorld);
   pending=request;
   request.catch(e=>{if(pending===request){status('Erro: '+e.message);onError(e.message);}})
    .finally(()=>{if(pending===request)pending=null;});return;
  }
  if(pending || lastDocument!==source)return;
  if(previousTime!==Math.min(time,scene.duracao)){
   const token=loadingSerial;
   scheduleCamera(scene,time,aspect,token);
  }
 }
 // State comes from the Studio project and always survives normalization.
 function update(mutator){
  const scene=getScene();if(!scene)throw Error('Nenhuma cena selecionada.');
  if(!scene.spatialseed_viewport)scene.spatialseed_viewport={enabled:false,source:'',camera_keys:[]};
  mutator(scene.spatialseed_viewport);onEdit();
 }
 $('ssViewportToggle').onclick=()=>{try{update(v=>{v.enabled=!v.enabled;});sync(getScene(),getTime(),getAspect());}catch(e){onError(e.message);}};
 const hudButton=$('ssViewportHud');
 function refreshHUD(){
  hudButton.setAttribute('aria-pressed',String(!hudHidden));
  hudButton.textContent=hudHidden?'Mostrar HUD original':'Ocultar HUD original';
  try{embedCSS();}catch{} // SpatialSeed may not have booted yet.
 }
 hudButton.onclick=()=>{hudHidden=!hudHidden;refreshHUD();};
 refreshHUD();
 $('ssViewportStore').onclick=async()=>{
  try{
   const scene=getScene(),token=loadingSerial;
   const source=scene?.spatialseed_viewport?.source||'';
   if(!isEnabled(scene)||pending||exportActive||lastDocument!==source||
      loadedKey!==sceneKey(scene,source))throw Error('Aguarde a cena WebGL selecionada.');
   const saved=await api().app.execute('project.save');
   if(!saved?.prepared||!saved.text||new TextEncoder().encode(saved.text).length>900000)
    throw Error('Fonte nativa indisponível ou acima de 900 kB.');
   if(getScene()!==scene||token!==loadingSerial)throw Error('A cena mudou durante a captura.');
   lastDocument=saved.text;
   loadedKey=sceneKey(scene,saved.text);
   update(v=>{v.source=saved.text;});
   status('Edição 3D capturada. Use Salvar para gravar o arquivo .spatialseed.');
  }catch(e){onError(e.message);}
 };
 $('ssViewportImport').onclick=()=>$('ssViewportFile').click();
 $('ssViewportFile').onchange=async e=>{
  const file=e.target.files?.[0];e.target.value='';if(!file)return;
  try{if(file.size>900000||!file.size)throw Error('Documento deve ter até 900 kB.');
   const source=await file.text(),decoded=JSON.parse(source);
   if(!decoded||typeof decoded!=='object'||Array.isArray(decoded))throw Error('Documento JSON inválido.');
   update(v=>{v.enabled=true;v.source=source;v.camera_keys=[];});
   sync(getScene(),getTime(),getAspect());status('Importando documento .spatialseed original…');
  }catch(error){onError(error.message);}
 };
 // Menu actions are proxied into the floating sibling panel, never unhide iframe chrome.
 $('ssCameraCapture').onclick=async()=>{
  try{const scene=getScene();if(!isEnabled(scene))throw Error('Ative WebGL nesta cena.');
   const {app}=await boot(),c=await Promise.resolve(currentCamera(app));
   const t=Math.round(Math.min(scene.duracao,Math.max(0,getTime()))*1000)/1000;
   const key={t,easing:'smoothstep',camera:{position:[...c.position],quaternion:[...c.quaternion],focusDistance:c.focusDistance,fov:c.fov,near:c.near,far:c.far}};
   update(v=>{const keys=[...(v.camera_keys||[])].filter(k=>Math.abs(k.t-t)>.0005);keys.push(key);keys.sort((a,b)=>a.t-b.t);v.camera_keys=validateKeyframes(keys);});
   status(`Keyframe da câmera em ${t.toFixed(2)} s.`);
  }catch(e){onError(e.message);}
 };
 $('ssCameraDelete').onclick=()=>{try{const t=getTime();update(v=>{const keys=v.camera_keys||[];if(!keys.length)throw Error('Câmera sem keyframes.');const nearest=keys.reduce((a,b)=>Math.abs(b.t-t)<Math.abs(a.t-t)?b:a);v.camera_keys=keys.filter(k=>k!==nearest);});status('Keyframe mais próximo removido.');}catch(e){onError(e.message);}};
 $('ssCamApply').onclick=async()=>{
  try{if(!isEnabled(getScene()))throw Error('Ative WebGL.');const {app}=await boot();const before=await Promise.resolve(currentCamera(app));
   const [x,y,z,fov]=cameraNumbers.map(id=>Number($(id).value));
   if(![x,y,z,fov].every(Number.isFinite)||fov<1||fov>179)throw Error('Pose/FOV inválidos.');
   const next={...before,position:[x,y,z],fov,aspect:getAspect()};
   await Promise.resolve(app.execute('viewer.camera.restore',{camera:next}));
   status('Pose aplicada. Use ◆ Keyframe para vinculá-la à timeline.');
  }catch(e){onError(e.message);}
 };
 // Only user action updates numeric inputs, never an animation frame.
 frame.addEventListener('pointerup',async()=>{
  try{const {app}=api(),c=await Promise.resolve(currentCamera(app));
   [c.position[0],c.position[1],c.position[2],c.fov].forEach((v,i)=>{$(cameraNumbers[i]).value=Number(v).toFixed(2);});
  }catch{}
 });
 // Export uses the same SpatialSeed canvas, camera and source as preview.
 // Browser video track captures *presented WebGL frames*, avoiding an empty
 // default drawing buffer when preserveDrawingBuffer=false.
 async function prepareCapture(scene,time,aspect,exact=false,signal){
   if(!isEnabled(scene))throw Error('Cena sem viewport SpatialSeed.');
   const key=sceneKey(scene,scene.spatialseed_viewport.source||'');
   if(cameraFlight)await cameraFlight;
   if(pending)await pending;
   if(key!==loadedKey||lastDocument!==(scene.spatialseed_viewport.source||'')){const had=loadedKey!=='';loadedKey=key;await loadDocument(scene,had);}
   if(readyPromise)await readyPromise;
   const token=loadingSerial;
   await cameraAt(scene,time,aspect,token);
   const {canvas,w}=api();
   if(!canvas.width||!canvas.height)throw Error('SpatialSeed não produziu quadros WebGL.');
   const {app}=api();
   if(!exact&&!nativeCapture.has(app)){
     nativeCapture.set(app,app.capabilities().queries.some(q=>q.id==='viewer.frame.capture'));
   }
   if(exact||nativeCapture.get(app)){
     const deadline=performance.now()+2000;
     for(;;){
       if(signal?.aborted)throw Error('Exportação offline cancelada.');
       const state=app.query('time.execution');
       if(state?.fault)throw Error(state.fault.message);
       if(state&&!state.running&&state.readiness.readyCount===0)break;
       if(performance.now()>=deadline)throw Error('SpatialSeed não concluiu a avaliação temporal.');
       await pause(8);
     }
     try{return await app.query('viewer.frame.capture');}
     catch(e){throw Error('Captura exata WebGL indisponível. Confira o patch SpatialSeed. '+e.message);}
   }
   if(canvas!==exportCanvas){
     exportStream?.getTracks().forEach(t=>t.stop());
     exportVideo?.pause();
     exportCanvas=canvas;
     if(!canvas.captureStream)throw Error('Canvas WebGL sem captureStream.');
     exportStream=canvas.captureStream(30);
     exportVideo=document.createElement('video');exportVideo.muted=true;exportVideo.playsInline=true;exportVideo.autoplay=true;
     exportVideo.srcObject=exportStream;
     await exportVideo.play();
   }
   // One presentation opportunity after applying the timeline camera.
   await new Promise(resolve=>w.requestAnimationFrame(()=>w.requestAnimationFrame(resolve)));
   if(exportVideo.readyState<2||!exportVideo.videoWidth)throw Error('WebGL não apresentou quadro ao codificador.');
   return exportVideo;
 }
 function beginExport(){
   if(exportActive)throw Error('Exportação WebGL já em andamento.');
   cameraRequested=null;
   exportPrevious={hidden:host.hidden,active:shell.classList.contains('ss-webgl-active')};
   exportActive=true;host.hidden=false;shell.classList.add('ss-webgl-active');return true;
 }
 function endExport(){
   exportActive=false;exportVideo?.pause();if(exportVideo)exportVideo.srcObject=null;
   exportStream?.getTracks().forEach(t=>t.stop());exportVideo=null;exportCanvas=null;exportStream=null;
   if(exportPrevious){host.hidden=exportPrevious.hidden;shell.classList.toggle('ss-webgl-active',exportPrevious.active);exportPrevious=null;}
   if(getScene())sync(getScene(),getTime(),getAspect());
 }
 function frameAt(scene,time,aspect){
   const promise=exportQueue.then(()=>prepareCapture(scene,time,aspect));
   exportQueue=promise.catch(()=>{});
   return promise;
 }
 async function frameAtOffline(scene,time,aspect,signal){
   if(signal?.aborted)throw Error('Exportação offline cancelada.');
   if(!exportActive)beginExport();
   const result=exportQueue.then(()=>prepareCapture(scene,time,aspect,true,signal));
   exportQueue=result.catch(()=>{});
   return result;
 }

 // Browser export may use this bridge, not a second application or renderer.
 const exportAPI=Object.freeze({beginExport,endExport,frameAt,frameAtOffline,isEnabled});
 window.StudioSpatialSeedViewport=exportAPI;
 // Explicit capture adopts native edits into the normal Studio save/undo path.
 return {sync,readCamera:async()=>currentCamera((await boot()).app),isActive:()=>active,exportAPI};
}
