/**
 * Camera timeline adapter for SpatialSeed ThreeRegionRenderer.
 * Uses only the renderer's public readNavigationCamera/applyNavigationCamera
 * interface; no direct Three.js or DOM access.
 *
 * Intentional limitation: this is a reusable timing component, NOT yet
 * connected to RD Studio's viewport and export pipelines.
 */
const finite = (n) => typeof n === 'number' && Number.isFinite(n);
const lerp = (a,b,u) => a+(b-a)*u;
const clamp = (x,a,b) => Math.min(b, Math.max(a,x));
const lerpArray = (a,b,u) => a.map((n,i)=>lerp(n,b[i],u));
const normQuat = q => {
  const len=Math.hypot(...q);
  if(!finite(len)||len<1e-12) throw new TypeError('Quaternion invalid');
  return q.map(n=>n/len);
};
export function slerpQuaternion(qa,qb,u) {
  const a=normQuat(qa);
  let b=normQuat(qb);
  let dot=a.reduce((s,n,i)=>s+n*b[i],0);
  if(dot<0){b=b.map(x=>-x);dot=-dot;}
  dot=clamp(dot,-1,1);
  if(dot>0.9995)return normQuat(lerpArray(a,b,u));
  const theta=Math.acos(dot),s=Math.sin(theta);
  const w0=Math.sin((1-u)*theta)/s,w1=Math.sin(u*theta)/s;
  return a.map((n,i)=>n*w0+b[i]*w1);
}
export function validateKeyframes(keys){
  if(!Array.isArray(keys)||!keys.length)throw new TypeError('Camera keyframes required');
  let previous=-Infinity;
  return keys.map((entry,index)=>{
    if(!entry||!finite(entry.t)||entry.t<0||entry.t<=previous)throw new TypeError(`Invalid key time at ${index}`);
    previous=entry.t;
    const c=entry.camera;
    if(!c||!Array.isArray(c.position)||c.position.length!==3||!c.position.every(finite))throw new TypeError(`Invalid position at ${index}`);
    if(!Array.isArray(c.quaternion)||c.quaternion.length!==4||!c.quaternion.every(finite))throw new TypeError(`Invalid quaternion at ${index}`);
    for(const k of ['focusDistance','fov','near','far'])if(!finite(c[k]))throw new TypeError(`Invalid camera ${k} at ${index}`);
    if(c.focusDistance<=0||c.fov<=0||c.fov>=180||c.near<=0||c.far<=c.near)throw new RangeError('Invalid camera optics');
    if(entry.easing!=null&&!['linear','smoothstep','hold'].includes(entry.easing))throw new TypeError('Unsupported camera easing');
    return {t:entry.t,easing:entry.easing||'linear',camera:{
      position:[...c.position], quaternion:normQuat(c.quaternion),
      focusDistance:c.focusDistance, fov:c.fov, near:c.near, far:c.far
    }};
  });
}
export function sampleCameraTrack(keyframes,localSeconds,aspect){
  const keys=validateKeyframes(keyframes);
  if(!finite(localSeconds)||!finite(aspect)||aspect<=0)throw new TypeError('Invalid timeline or aspect ratio');
  const first=keys[0],last=keys.at(-1);
  if(localSeconds<=first.t || keys.length===1)return {...first.camera,aspect};
  if(localSeconds>=last.t)return {...last.camera,aspect};
  let i=0; while(keys[i+1].t<localSeconds)i++;
  const a=keys[i],b=keys[i+1];
  let u=(localSeconds-a.t)/(b.t-a.t);
  if(a.easing==='hold')u=0;
  else if(a.easing==='smoothstep')u=u*u*(3-2*u);
  const c=a.camera,d=b.camera;
  return {
    position:lerpArray(c.position,d.position,u),
    quaternion:slerpQuaternion(c.quaternion,d.quaternion,u),
    focusDistance:lerp(c.focusDistance,d.focusDistance,u),
    fov:lerp(c.fov,d.fov,u), near:lerp(c.near,d.near,u),far:lerp(c.far,d.far,u),aspect
  };
}
export function captureCameraKeyframe(renderer,t){
  if(!renderer||typeof renderer.readNavigationCamera!=='function')throw new TypeError('SpatialSeed renderer missing camera interface');
  return validateKeyframes([{t,camera:renderer.readNavigationCamera()}])[0];
}
export function applyCameraTrack(renderer,keyframes,localSeconds,aspect){
  if(!renderer||typeof renderer.applyNavigationCamera!=='function')throw new TypeError('SpatialSeed renderer missing camera interface');
  return renderer.applyNavigationCamera(sampleCameraTrack(keyframes,localSeconds,aspect));
}
