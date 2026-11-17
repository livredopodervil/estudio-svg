// Estúdio SVG — camada GIL nativa. Autor do projeto: Rogério Duarte.
// O relógio pertence ao editor/player, nunca ao elemento de composição.
import {compile} from './gil-runtime/src/model.mjs';
import {Timeline} from './gil-runtime/src/timeline.mjs';
import {renderSVG,SUPPORTED} from './gil-runtime/src/render-svg.mjs';
const clamp=(v,min,max,d)=>Number.isFinite(Number(v))?Math.max(min,Math.min(max,Number(v))):d;
export function prepare(source){
 const doc=compile(source),timeline=new Timeline(doc),duration=doc.spec.stage.duration;
 const kinds=new Set(SUPPORTED);
 for(const node of doc.nodes){
  if(!kinds.has(node.kind)||node.kind==='image.svg')throw Error('Recurso não suportado pela camada nativa inicial: '+node.kind);
 }
 const frame=t=>{const result=renderSVG(timeline.sample(t),{assetResolver:()=>null});if(result.missing.length)throw Error(result.missing.join(', '));return result.svg;};
 frame(0);frame(duration/2);frame(duration);
 return {duration,cues:doc.cues.length,frame};
}
const instances=new WeakMap();
function create(shell){
 if(getComputedStyle(shell).position==='static')shell.style.position='relative';
 const host=document.createElement('div');host.setAttribute('aria-label','Camada GIL nativa');host.style.cssText='position:absolute;z-index:4;pointer-events:none;overflow:hidden;display:none;';
 const shadow=host.attachShadow({mode:'open'});const style=document.createElement('style');style.textContent=':host{contain:layout paint}div{width:100%;height:100%;display:grid;place-items:center}svg{display:block;width:100%;height:100%}.error{background:#321d1a;color:#ffdfc8;padding:8px;font:12px system-ui;overflow-wrap:anywhere;box-sizing:border-box}';
 const content=document.createElement('div');shadow.append(style,content);shell.append(host);
 const state={host,content,source:null,compiled:null,last:null,error:null,opaque:null,layer:null,dimensions:null};
 if(typeof ResizeObserver!=='undefined')new ResizeObserver(()=>{if(state.layer)place(shell,state);}).observe(shell);
 return state;
}
function place(shell,s){
 const layer=s.layer,d=s.dimensions||{},v=shell.querySelector('#stage')||shell;
 const sw=shell.getBoundingClientRect(),sv=v.getBoundingClientRect(),ar=(Number(d.width)||1280)/(Number(d.height)||720);
 const W=Math.min(sv.width,sv.height*ar),H=W/ar;
 const w=clamp(layer.w,.08,1,1)*W,h=clamp(layer.h,.08,1,1)*H;
 const x=sv.left-sw.left-shell.clientLeft+(sv.width-W)/2+clamp(layer.x,0,1,.5)*W-w/2;
 const y=sv.top-sw.top-shell.clientTop+(sv.height-H)/2+clamp(layer.y,0,1,.5)*H-h/2;
 Object.assign(s.host.style,{left:x+'px',top:y+'px',width:w+'px',height:h+'px',opacity:String(clamp(layer.opacidade,0,1,1))});
}
export function frameTime(time,duration){return Math.min(duration,Math.max(0,Number(time)||0));}
export function updateLayer(shell,layer,time,dimensions){
 if(!shell)return;
 let s=instances.get(shell);
 if(!layer){if(s){s.layer=null;s.host.style.display='none';s.source=null;s.last=null;s.content.replaceChildren();s.compiled=null;s.error=null;}return;}
 if(!s){s=create(shell);instances.set(shell,s);}
 s.layer=layer;s.dimensions=dimensions;s.host.style.display='block';place(shell,s);
 if(s.source!==layer.source){s.source=layer.source;s.last=null;s.error=null;s.compiled=null;try{s.compiled=prepare(layer.source);}catch(e){s.error=e.message;}}
 if(s.error){s.content.className='error';s.content.textContent='GIL: '+s.error;return;}
 const t=frameTime(time,s.compiled.duration);
 if(s.last!==null&&(t===s.last||(t!==0&&t!==s.compiled.duration&&Math.abs(t-s.last)<1/30))&&s.opaque===!!layer.opaque)return;
 try{
  const parsed=new DOMParser().parseFromString(s.compiled.frame(t),'image/svg+xml'),svg=parsed.documentElement;
  if(svg.localName!=='svg'||parsed.querySelector('parsererror'))throw Error('SVG inválido');
  if(!layer.opaque&&svg.firstElementChild?.localName==='rect')svg.firstElementChild.remove();
  svg.removeAttribute('width');svg.removeAttribute('height');svg.setAttribute('preserveAspectRatio','xMidYMid meet');
  s.content.className='';s.content.replaceChildren(document.importNode(svg,true));s.last=t;s.opaque=!!layer.opaque;
 }catch(e){s.error=e.message;s.content.className='error';s.content.textContent='GIL: '+s.error;}
}
