import {cssAppearance} from './visual-effects.mjs';
// Rogério Duarte — compositor local de objetos de mídia. Mesmo runtime GIL, sem MP4 derivado.
import {compile} from './gil-runtime/src/model.mjs';
import {Timeline} from './gil-runtime/src/timeline.mjs';
import {affine} from './viewport-affine.mjs';
import {prepare} from './gil-native.mjs';
const clamp=(n,a,b)=>Math.min(b,Math.max(a,n));
export function motionSource(preset,duration){
 const d=Math.max(.5,Math.min(600,Number(duration)||1)),k=Math.min(1.25,d),late=Math.max(0,d-k);
 const smooth=(key,arr)=>`animate media ${key} ${JSON.stringify({keys:arr,ease:'smooth'})}`;
 // All programs target the canonical "media" group. They can be stacked.
 const tracks={
  enter:[['x',[0,-.9],[k,0]],['sx',[0,.25],[k,1]],['sy',[0,.25],[k,1]]],
  exit:[['x',[late,0],[d,1]],['sx',[late,1],[d,.25]],['sy',[late,1],[d,.25]]],
  fade:[['opacity',[0,0],[k,1]]],
  'fade-out':[['opacity',[late,1],[d,0]]],
  'enter-right':[['x',[0,1],[k,0]]],
  'enter-top':[['y',[0,1],[k,0]]],
  'enter-bottom':[['y',[0,-1],[k,0]]],
  'exit-left':[['x',[late,0],[d,-1]]],
  'exit-right':[['x',[late,0],[d,1]]],
  'zoom-in':[['sx',[0,.15],[k,1]],['sy',[0,.15],[k,1]]],
  'zoom-out':[['sx',[late,1],[d,.15]],['sy',[late,1],[d,.15]]],
  'spin':[['rz',[0,0],[d,360]]],
  'float':[['y',[0,0],[d/4,.10],[d/2,0],[3*d/4,-.10],[d,0]]],
  'pulse':[['sx',[0,1],[d/4,1.12],[d/2,1],[3*d/4,1.12],[d,1]],['sy',[0,1],[d/4,1.12],[d/2,1],[3*d/4,1.12],[d,1]]]
 };
 if(!Object.hasOwn(tracks,preset))throw Error('Movimento desconhecido: '+preset);
 return `gil timeline 0.1 {\nstage {"width":640,"height":360,"duration":${d},"background":"#000000","camera":"cam"}\nresource camera camera {"z":15}\nresource g group {}\nobject cam camera - {}\nobject media g - {}\n${tracks[preset].map(([property,...keys])=>smooth(property,keys)).join('\n')}\n}\n`;
}
export function motionProgram(source){
 if(!source?.trim())return ()=>({x:0,y:0,sx:1,sy:1,rz:0,opacity:1});
 const doc=compile(source);const target=doc.nodes.find(n=>n.id==='media'&&n.kind==='group'&&!n.parent);
 if(!target||doc.nodes.length!==2||doc.cues.length||doc.tracks.some(t=>t.target!=='media'||!['x','y','sx','sy','rz','opacity'].includes(t.property)))throw Error('Movimento: use apenas grupo media e câmera; propriedades x,y,sx,sy,rz,opacity.');
 const timeline=new Timeline(doc),sample=t=>timeline.sample(clamp(t,0,doc.spec.stage.duration)).objects.find(o=>o.id==='media').props;
 sample(0);sample(doc.spec.stage.duration/2);sample(doc.spec.stage.duration);return sample;
}
// Program stack evaluated by the same Timeline. Positions and rotations add;
// scales and opacities multiply. Every program uses the object's local clock.
export function objectMotion(obj){
 const programs=[obj.motion,...(obj.motion_programs||[])].filter(x=>x?.trim()).map(motionProgram);
 return t=>{const out={x:0,y:0,sx:1,sy:1,rz:0,opacity:1};for(const f of programs){const p=f(t);out.x+=p.x;out.y+=p.y;out.rz+=p.rz;out.sx*=p.sx;out.sy*=p.sy;out.opacity*=p.opacity;}return out;};
}
export function localTime(obj,t){return t>=obj.start&&t<obj.end?t-obj.start:null;}
export function rect(obj,p){return {x:obj.x+clamp(p.x,-3,3),y:obj.y-clamp(p.y,-3,3),w:obj.w*clamp(p.sx,.01,10),h:obj.h*clamp(p.sy,.01,10),rz:obj.rotation?obj.rotation-p.rz:-p.rz,opacity:obj.opacity*clamp(p.opacity,0,1),...(obj.shear!==undefined?{shear:obj.shear}:{}),...(obj.pivot_x!==undefined?{pivot_x:obj.pivot_x}:{}),...(obj.pivot_y!==undefined?{pivot_y:obj.pivot_y}:{})};}
export function parseFrame(markup,opaque=false){const svg=new DOMParser().parseFromString(markup,'image/svg+xml');if(svg.documentElement.localName!=='svg'||svg.querySelector('parsererror'))throw Error('SVG inválido');const root=svg.documentElement;if(!opaque&&root.firstElementChild?.localName==='rect')root.firstElementChild.remove();root.removeAttribute('width');root.removeAttribute('height');root.setAttribute('preserveAspectRatio','xMidYMid meet');return document.importNode(root,true);}
const states=new WeakMap();
export function syncObjects(shell,objects,time,dimensions,playing=false,rate=1,onError=console.warn,resolveMedia=null){
 if(!shell)return;let state=states.get(shell);
 if(!state){const plane=document.createElement('div');plane.style.cssText='position:absolute;inset:0;z-index:5;pointer-events:none;overflow:hidden';plane.setAttribute('aria-label','Objetos de mídia');shell.append(plane);state={plane,items:new Map()};states.set(shell,state);}
 const stage=shell.querySelector('#stage')||shell,base=shell.getBoundingClientRect(),r=stage.getBoundingClientRect(),ar=dimensions.width/dimensions.height,W=Math.min(r.width,r.height*ar),H=W/ar;
 Object.assign(state.plane.style,{left:r.left-base.left-shell.clientLeft+(r.width-W)/2+'px',top:r.top-base.top-shell.clientTop+(r.height-H)/2+'px',width:W+'px',height:H+'px',right:'auto',bottom:'auto'});
 const wanted=new Set((objects||[]).map(o=>o.id));for(const [id,s] of state.items){if(!wanted.has(id)){s.el.pause?.();s.el.remove();state.items.delete(id);}}
 for(const [z,o] of (objects||[]).entries()){
  const key=JSON.stringify([o.kind,o.file,o.gil?.source,o.motion,o.motion_programs]);let s=state.items.get(o.id);
  if(s?.key!==key){if(s){s.el.pause?.();s.el.remove();}const el=document.createElement(o.kind==='video'?'video':o.kind==='image'?'img':'div');el.style.cssText='position:absolute;display:none;overflow:hidden;pointer-events:none';if(o.kind==='gil'){el.attachShadow({mode:'open'});}el.dataset.sceneObjectId=o.id;s={el,key,last:-1,playPending:false};state.items.set(o.id,s);state.plane.append(el);
   try{s.sample=objectMotion(o);if(o.kind==='gil'){s.gil=prepare(o.gil.source);if(s.gil.cues)throw Error('Áudio GIL ainda não suportado nos objetos.');}else{el.src=resolveMedia?resolveMedia(o.file,o.kind):(o.kind==='video'?'/api/media/clip?file=':'/api/media/image?file=')+encodeURIComponent(o.file);el.onerror=()=>onError(o.label+': mídia indisponível');if(o.kind==='video'){el.muted=true;el.playsInline=true;el.preload='metadata';}}}catch(e){s.failed=true;onError(o.label+': '+e.message);}
  }
  const el=s.el,t=localTime(o,time);if(t===null||s.failed){el.style.display='none';el.pause?.();continue;}
  try{const p=rect(o,s.sample(t));Object.assign(el.style,{display:'block',zIndex:String(z),left:(p.x-p.w/2)*100+'%',top:(p.y-p.h/2)*100+'%',width:p.w*100+'%',height:p.h*100+'%',opacity:String(p.opacity),transform:`matrix(${affine(p,p.w*W,p.h*H).join(',')})`,objectFit:o.fit,pointerEvents:playing?'none':'auto',...cssAppearance(o)});
   if(s.gil){const dur=s.gil.duration,at=o.loop?(t+o.offset)%dur:Math.min(dur,t+o.offset);if(s.last<0||(at!==s.last&&(Math.abs(at-s.last)>=1/30||at===0||!playing))||s.opaque!==o.opaque){const node=parseFrame(s.gil.frame(at),o.opaque);node.style.cssText='display:block;width:100%;height:100%';el.shadowRoot.replaceChildren(node);s.last=at;s.opaque=o.opaque;}}
   else if(o.kind==='video'){el.loop=o.loop;el.playbackRate=rate;if(el.readyState>=1&&Number.isFinite(el.duration)&&el.duration>0){const a=t+o.offset;if(!o.loop&&a>=el.duration){el.pause();el.style.display='none';continue;}const dest=o.loop?a%el.duration:a;if(!el.seeking&&Math.abs(el.currentTime-dest)>(playing?.35:.025))el.currentTime=dest;if(playing&&el.paused&&!s.playPending){s.playPending=true;el.play().catch(e=>{if(e.name!=='AbortError')onError(o.label+': '+e.message);}).finally(()=>{s.playPending=false;});}}if(!playing)el.pause();}
  }catch(e){s.failed=true;el.pause?.();el.style.display='none';onError(o.label+': '+e.message);}
 }
}
export function pauseObjects(shell){for(const s of states.get(shell)?.items.values()||[])s.el.pause?.();}
