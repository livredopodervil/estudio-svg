/* RD_V3_ANIMATION_CANONICAL_15: editor adapter; Player V3 runtime is the only animation engine.
 * No Player iframe, controls, playback loop or second timeline.
 */
const clamp=(x,a=0,b=1)=>Math.min(b,Math.max(a,x));
const runtimeUrl='/player-v3/runtime.js?v=rd-v3-single-engine-15';
let pending;
export function ensureV3Runtime(){
 if(window.EstudioV3?.createDOMAnimator)return Promise.resolve(window.EstudioV3);
 if(pending)return pending;
 pending=new Promise((resolve,reject)=>{
  const script=document.createElement('script');script.async=true;script.src=runtimeUrl;
  script.onload=()=>window.EstudioV3?.createDOMAnimator?resolve(window.EstudioV3):reject(Error('Motor único V3 ausente'));
  script.onerror=()=>reject(Error('Não foi possível carregar o motor V3'));
  document.head.append(script);
 }).catch(e=>{pending=null;throw e;});
 return pending;
}
function sanitize(markup){
 const parsed=new DOMParser().parseFromString(markup,'image/svg+xml');
 if(parsed.querySelector('parsererror')||parsed.documentElement.localName!=='svg')throw Error('SVG inválido');
 const svg=document.importNode(parsed.documentElement,true);
 svg.querySelectorAll('script,foreignObject,iframe,object,embed').forEach(n=>n.remove());
 svg.querySelectorAll('*').forEach(el=>{for(const a of [...el.attributes]){
   if(/^on/i.test(a.name)||(/^(href|xlink:href)$/i.test(a.name)&&/^\s*javascript:/i.test(a.value)))el.removeAttribute(a.name);
 }});
 svg.setAttribute('preserveAspectRatio','xMidYMid meet');svg.removeAttribute('width');svg.removeAttribute('height');
 return svg;
}
function pivotOverridesFor(slug){
 try{return JSON.parse(localStorage.getItem('estudio-svg-vetorial-pivos:'+slug)||'{}')||{};}
 catch(_){return {};}
}
export function applyV3Animation({svg,scene,progress,sceneIndex=0,slug=''}){
 const rt=window.EstudioV3;
 if(!rt?.createDOMAnimator)throw Error('Motor V3 único indisponível');
 if(!svg.__rdV3Animator){svg.__rdV3Animator=rt.createDOMAnimator(svg,scene.animacoes||[],{
   sceneIndex,pivotOverrides:pivotOverridesFor(slug)
 });}
 const p=clamp(Number(progress)||0);
 svg.__rdV3Animator.apply(p);
 rt.updateProcedural(svg,scene,p);
 svg.style.opacity=String(clamp(p/.06));
}
// Shared by browser HD export: same source SVG and evaluator, at the requested exact time.
export async function animateV3Markup(markup,scene,progress,{sceneIndex=0,slug='',renderWidth=null,renderHeight=null}={}){
 await ensureV3Runtime();
 const svg=sanitize(markup);
 const holder=document.createElement('div');
 holder.style.cssText='position:fixed;left:-100000px;top:0;width:1280px;height:720px;visibility:hidden;pointer-events:none;z-index:-1';
 holder.append(svg);document.body.append(holder);
 try{
  applyV3Animation({svg,scene,progress,sceneIndex,slug});
  // Preserve intrinsic pixel aspect ratio when converting the SVG to an Image.
  const view=svg.viewBox?.baseVal;
  if(view?.width>0&&view?.height>0){
   svg.setAttribute('width',String(renderWidth>0?renderWidth:view.width));
   svg.setAttribute('height',String(renderHeight>0?renderHeight:view.height));
  }
  return new XMLSerializer().serializeToString(svg);
 }finally{holder.remove();}
}
export function createV3Preview({post}){
 let currentKey='',svg=null,serial=0;
 return {
  reset(){serial++;currentKey='';svg=null;},
  async render({stage,scene,video,progress,index,total,slug,isCurrent=()=>true}){
   const key=JSON.stringify([index,total,video,{...scene,spatialseed_viewport:{enabled:scene.spatialseed_viewport?.enabled===true}}]);
   if(key!==currentKey||!svg||!svg.isConnected||!stage.contains(svg)){
    const ticket=++serial;
    const markup=await post('/api/preview',{scene,video,index,total,progress:0,animation_engine:'v3'});
    if(ticket!==serial||!isCurrent())return;
    const candidate=sanitize(markup);
    stage.replaceChildren(candidate);svg=candidate;currentKey=key;
   }
   if(isCurrent())applyV3Animation({svg,scene,progress,sceneIndex:index,slug});
  }
 };
}
