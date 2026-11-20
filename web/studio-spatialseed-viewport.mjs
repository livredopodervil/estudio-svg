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
export function mountStudioSpatialSeed({getScene,getAspect,getTime,onEdit,onError}){
 const host=$('ssViewportHost'),frame=$('ssViewportFrame'),shell=$('stageShell');
 let lastDocument=null,readyPromise=null,active=false,loadingSerial=0,cameraSeq=0,previousTime=null,loadedKey='';
 let cameraFlight=null,cameraRequested=null,hudHidden=true;
 let exportActive=false,exportStream=null,exportVideo=null,exportCanvas=null,exportQueue=Promise.resolve(),exportPrevious=null;
 const cameraNumbers=['ssCamX','ssCamY','ssCamZ','ssCamFov'];
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
  frame.src='/spatialseed-main/apps/web/?project=new&rd-studio-viewport=1';
  readyPromise=(async()=>{
   const deadline=Date.now()+20000;
   while(Date.now()<deadline){
    try{const result=api();embedCSS();return result;}catch{}
    await pause(250);
   }
   throw Error('SpatialSeed não inicializou. Verifique RD_SPATIALSEED_ROOT e os módulos do main.');
  })().catch(e=>{readyPromise=null;status(e.message);throw e;});
  return readyPromise;
 }
 async function openSource(source,token){
  const {w,app}=await boot();
  if(token!==loadingSerial)return;
  if(!editableSource(source))return;
  const nativeInput=w.document.getElementById('project-file-input');
  if(!nativeInput)throw Error('Importador .spatialseed do main indisponível.');
  const dt=new w.DataTransfer();dt.items.add(new w.File([source],'studio-scene.spatialseed',{type:'application/json'}));
  nativeInput.files=dt.files;
  nativeInput.dispatchEvent(new w.Event('change',{bubbles:true}));
  // Native importer has its own asynchronous transaction. The camera will
  // be re-applied after it has completed its scene projection.
  await pause(600);
  if(token!==loadingSerial)return;
  await Promise.resolve(app.query('world.snapshot'));
 }
 async function cameraAt(scene,time,aspect,token){
  const keys=scene?.spatialseed_viewport?.camera_keys||[];
  if(!keys.length)return;
  const {app}=await boot();if(token!==loadingSerial)return;
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
   lastDocument=source;
   await openSource(source,serial);
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
  if(!enabled){active=false;previousTime=null;return;}
  active=true;
  const source=scene.spatialseed_viewport.source||'';
  const key=(scene.id||'')+'\0'+source;
  if(key!==loadedKey){const resetWorld=loadedKey!=='';loadedKey=key;
   pending=loadDocument(scene,resetWorld).catch(e=>{status('Erro: '+e.message);onError(e.message);}).finally(()=>{pending=null;});return;
  }
  if(pending)return;
  if(scene.spatialseed_viewport.camera_keys?.length && (previousTime===null||Math.abs(time-previousTime)>1/60)){
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
 async function prepareCapture(scene,time,aspect){
   if(!isEnabled(scene))throw Error('Cena sem viewport SpatialSeed.');
   const key=(scene.id||'')+'\0'+(scene.spatialseed_viewport.source||'');
   if(key!==loadedKey){const had=loadedKey!=='';loadedKey=key;await loadDocument(scene,had);}
   if(readyPromise)await readyPromise;
   const token=loadingSerial;
   if(scene.spatialseed_viewport.camera_keys?.length)await cameraAt(scene,time,aspect,token);
   const {canvas,w}=api();
   if(!canvas.width||!canvas.height)throw Error('SpatialSeed não produziu quadros WebGL.');
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
   exportPrevious={hidden:host.hidden,active:shell.classList.contains('ss-webgl-active')};
   exportActive=true;host.hidden=false;shell.classList.add('ss-webgl-active');return true;
 }
 function endExport(){
   exportActive=false;exportVideo?.pause();if(exportVideo)exportVideo.srcObject=null;
   exportStream?.getTracks().forEach(t=>t.stop());exportVideo=null;exportCanvas=null;exportStream=null;
   if(exportPrevious){host.hidden=exportPrevious.hidden;shell.classList.toggle('ss-webgl-active',exportPrevious.active);exportPrevious=null;}
 }
 function frameAt(scene,time,aspect){
   const promise=exportQueue.then(()=>prepareCapture(scene,time,aspect));
   exportQueue=promise.catch(()=>{});
   return promise;
 }
 async function frameAtOffline(scene,time,aspect,signal){
   if(signal?.aborted)throw Error('Exportação offline cancelada.');
   if(!exportActive)beginExport();
   const video=await frameAt(scene,time,aspect);
   // The frame may have been presented before requestVideoFrameCallback is
   // installed. Static WebGL scenes need not emit additional video frames.
   // prepareCapture already awaited the camera command and two RAF cycles
   // in the SpatialSeed iframe. Check that the captured frame is decodable.
   if(video.readyState<2||!video.videoWidth||!video.videoHeight)
    throw Error('Quadro WebGL indisponível para exportação offline.');
   return video;
 }

 // Browser export may use this bridge, not a second application or renderer.
 const exportAPI=Object.freeze({beginExport,endExport,frameAt,frameAtOffline,isEnabled});
 window.StudioSpatialSeedViewport=exportAPI;
 // The original source remains editable in SpatialSeed; use its native Save
 // then reimport the file to persist object edits inside the Studio project.
 return {sync,readCamera:async()=>currentCamera((await boot()).app),isActive:()=>active,exportAPI};
}
