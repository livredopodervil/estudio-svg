// M1b: optional direct manipulation of a persisted, ID-addressable SVG element.
// The original SVG document remains authoritative for the editor and exporters.
const NS='http://www.w3.org/2000/svg';
export function svgElementSource(source,id){
 if(!source||!/^[A-Za-z_][\w.:-]{0,80}$/.test(id))return null;
 const full=/^\s*<svg(?:\s|>)/i.test(source);
 const xml=full?source:`<svg xmlns="${NS}" viewBox="0 0 1280 720">${source}</svg>`;
 const doc=new DOMParser().parseFromString(xml,'image/svg+xml');if(doc.querySelector('parsererror'))return null;
 const node=[...doc.querySelectorAll('[id]')].find(n=>n.id===id);
 return node?{doc,node,full}:null;
}
export function serializeSvgElement(source,id,transform){
 const item=svgElementSource(source,id);if(!item)throw Error('Elemento SVG ausente da fonte da cena.');
 if(transform)item.node.setAttribute('transform',transform);else item.node.removeAttribute('transform');
 const write=new XMLSerializer();return item.full?write.serializeToString(item.doc.documentElement):[...item.doc.documentElement.childNodes].map(n=>write.serializeToString(n)).join('');
}
export function installSvgDirect({shell,scene,playing,changed,notify,select}){
 const overlay=document.createElement('div');overlay.className='rdSvgDirectOutline';overlay.hidden=true;
 overlay.innerHTML='<button type="button" data-svg-handle="scale" title="Escalar SVG" aria-label="Escalar SVG">⤢</button><button type="button" data-svg-handle="rotate" title="Girar SVG" aria-label="Girar SVG">↻</button>';
 shell.append(overlay);
 let chosen=null,drag=null;
 const find=()=>{if(!chosen||scene()!==chosen.scene)return null;const root=shell.querySelector('#stage svg');return root?[...root.querySelectorAll('[id]')].find(n=>n.id===chosen.id):null;};
 function paint(){const node=find();if(!node||playing()){overlay.hidden=true;return;}
  const a=node.getBoundingClientRect(),b=shell.getBoundingClientRect();if(a.width<2||a.height<2){overlay.hidden=true;return;}
  overlay.hidden=false;Object.assign(overlay.style,{left:a.left-b.left-shell.clientLeft+'px',top:a.top-b.top-shell.clientTop+'px',width:a.width+'px',height:a.height+'px'});
 }
 function choose(id){const c=scene();if(c?.tipo!=='svg'||!svgElementSource(c.svg,id))return false;chosen={scene:c,id};select?.('svg',id);requestAnimationFrame(paint);return true;}
 function endSelection(){chosen=null;drag=null;overlay.hidden=true;}
 const coords=(e,root)=>{const mat=root.getScreenCTM();if(!mat)throw Error('Coordenadas SVG indisponíveis');const p=new DOMPoint(e.clientX,e.clientY).matrixTransform(mat.inverse());return {x:p.x,y:p.y};};
 const begin=(e,handle='move')=>{
  if(playing()||document.fullscreenElement)return;
  if(e.pointerType==='mouse'&&e.button!==0)return;
  let node,id;
  if(handle!=='move'){node=find();id=chosen?.id;}
  else{const target=e.target.closest?.('#stage svg [id]');id=target?.id;const c=scene();if(c?.tipo!=='svg'||!svgElementSource(c.svg,id))return;node=target;choose(id);}
  if(!node||!id||!scene())return;
  const root=node.ownerSVGElement;if(!root)return;
  const box=node.getBBox();const pivot={x:box.x+box.width/2,y:box.y+box.height/2};
  const from=coords(e,root),base=svgElementSource(scene().svg,id).node.getAttribute('transform')||'';
  drag={id:e.pointerId,kind:handle,node,root,base,pivot,from,current:'',start:scene(),svg:scene().svg};
  shell.setPointerCapture(e.pointerId);e.preventDefault();e.stopPropagation();
 };
 const transform=(e)=>{
  if(!drag||drag.id!==e.pointerId)return;
  const d=drag,to=coords(e,d.root),dx=to.x-d.from.x,dy=to.y-d.from.y;
  let next='';
  if(d.kind==='move')next=`translate(${dx.toFixed(3)} ${dy.toFixed(3)})`;
  else if(d.kind==='scale'){
   const a=Math.hypot(d.from.x-d.pivot.x,d.from.y-d.pivot.y),b=Math.hypot(to.x-d.pivot.x,to.y-d.pivot.y),k=Math.max(.1,Math.min(8,b/Math.max(1,a)));
   next=`translate(${d.pivot.x} ${d.pivot.y}) scale(${k.toFixed(4)}) translate(${-d.pivot.x} ${-d.pivot.y})`;
  }else{
   const a=Math.atan2(d.from.y-d.pivot.y,d.from.x-d.pivot.x),b=Math.atan2(to.y-d.pivot.y,to.x-d.pivot.x),deg=(b-a)*180/Math.PI;
   next=`rotate(${deg.toFixed(3)} ${d.pivot.x} ${d.pivot.y})`;
  }
  d.current=next;d.node.setAttribute('transform',[next,d.base].filter(Boolean).join(' '));paint();e.preventDefault();e.stopPropagation();
 };
 const finish=e=>{
  if(!drag||e.pointerId!==drag.id)return;const d=drag;
  if(e.type==='pointerup')transform(e);
  drag=null;
  if(shell.hasPointerCapture(e.pointerId))shell.releasePointerCapture(e.pointerId);
  if(e.type!=='pointerup'||!d.current||scene()!==d.start){d.node.setAttribute('transform',d.base);paint();return;}
  try{const updated=serializeSvgElement(d.svg,chosen.id,[d.current,d.base].filter(Boolean).join(' '));
   if(updated!==d.svg){d.start.svg=updated;changed();notify('Transformação SVG persistida no documento.');}
  }catch(err){d.node.setAttribute('transform',d.base);notify(err.message,true);}
  requestAnimationFrame(paint);
 };
 shell.addEventListener('pointerdown',e=>{if(e.target.closest?.('[data-scene-object-id],.rdViewportGizmo'))return;begin(e);});
 for(const button of overlay.querySelectorAll('[data-svg-handle]'))button.addEventListener('pointerdown',e=>begin(e,button.dataset.svgHandle));
 shell.addEventListener('pointermove',transform);shell.addEventListener('pointerup',finish);shell.addEventListener('pointercancel',finish);
 window.addEventListener('resize',paint);
 return {choose,paint,clear:endSelection};
}
