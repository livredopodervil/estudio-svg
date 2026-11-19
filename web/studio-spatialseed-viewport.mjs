// M1X SpatialSeed main — embedded WebGL world in the actual video viewport.
// Original ThreeRegionRenderer is owned by the SpatialSeed application; no Three.js copy.
import {sampleCameraTrack,validateKeyframes} from './spatialseed-camera-track.mjs';
const $=id=>document.getElementById(id);
const status=t=>{$('ssCameraStatus').textContent=t;};
const pause=ms=>new Promise(r=>setTimeout(r,ms));
const editableSource=s=>typeof s==='string'&&s.length>0;
function currentCamera(app){return app.query('viewer.camera.snapshot');}
function isEnabled(scene){return scene?.spatialseed_viewport?.enabled===true;}
export function mountStudioSpatialSeed({getScene,getAspect,getTime,onEdit,onError}){
 const host=$('ssViewportHost'),frame=$('ssViewportFrame'),shell=$('stageShell');
 let lastDocument=null,readyPromise=null,active=false,tools=false,loadingSerial=0,cameraSeq=0,previousTime=null,loadedKey='';
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
 function showTools(next){
  tools=next;$('ssViewportTools').setAttribute('aria-pressed',String(tools));
  if(!readyPromise)return;
  try{const d=api().w.document;const s=d.getElementById('rdStudioEmbedStyle');if(s)s.disabled=tools;}catch{}
 }
 function embedCSS(){
  const {w}=api(),d=w.document;
  let s=d.getElementById('rdStudioEmbedStyle');if(!s){
   s=d.createElement('style');s.id='rdStudioEmbedStyle';
   s.textContent='html,body{margin:0!important;width:100%!important;height:100%!important;overflow:hidden!important}body > :not(#world){display:none!important}#world{display:block!important;position:fixed!important;inset:0!important;width:100vw!important;height:100vh!important;max-width:none!important;max-height:none!important;touch-action:none!important}';
   d.head.append(s);
  }
  s.disabled=tools;
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
 async function loadDocument(scene,resetWorld=false){
  const serial=++loadingSerial;
  const source=scene?.spatialseed_viewport?.source||'';
  if(readyPromise && resetWorld){
   // Changing scenes must not leak the former scene's SpatialSeed world.
   frame.src='about:blank';readyPromise=null;previousTime=null;lastDocument=null;
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
   cameraAt(scene,time,aspect,token).catch(e=>status('Câmera: '+e.message));
  }
 }
 // State comes from the Studio project and always survives normalization.
 function update(mutator){
  const scene=getScene();if(!scene)throw Error('Nenhuma cena selecionada.');
  if(!scene.spatialseed_viewport)scene.spatialseed_viewport={enabled:false,source:'',camera_keys:[]};
  mutator(scene.spatialseed_viewport);onEdit();
 }
 $('ssViewportToggle').onclick=()=>{try{update(v=>{v.enabled=!v.enabled;});sync(getScene(),getTime(),getAspect());}catch(e){onError(e.message);}};
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
 $('ssViewportTools').onclick=()=>showTools(!tools);
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
 // The original source remains editable in SpatialSeed; use its native Save
 // then reimport the file to persist object edits inside the Studio project.
 return {sync,readCamera:async()=>currentCamera((await boot()).app),isActive:()=>active};
}
