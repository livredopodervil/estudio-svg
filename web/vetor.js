/* Ateliê SVG V2.6. Editor nativo no navegador: não depende da API do SVG-Edit.
   Os documentos são salvos pela API /api/svg/document do Estúdio. */
const $=id=>document.getElementById(id),ns='http://www.w3.org/2000/svg';
const query=new URLSearchParams(location.search),name=query.get('name'),scene=Number(query.get('scene'));
const SHAPES=new Set(['rect','circle','ellipse','path','line','polyline','polygon','text','image','use']);
const S={svg:null,selected:null,layer:null,revision:null,dirty:false,loaded:false,working:false,tool:'select',zoom:1,panX:0,panY:0,touches:new Map(),pinch:null,gestureUsed:false,drag:null,history:[],index:-1,locked:new Set(),style:{fill:'#d77b53',stroke:'#354f5e',width:8,pattern:'solid',cap:'round'}};
const el=(t,a={})=>{const e=document.createElementNS(ns,t);for(const [k,v] of Object.entries(a))e.setAttribute(k,String(v));return e;};
const uid=(p='obj')=>p+'_'+Math.random().toString(36).slice(2,10);
function notice(msg,bad=false){$('notice').textContent=msg;$('notice').classList.toggle('error',bad);}
function state(){const e=$('saveState');e.textContent=S.dirty?'● Não salvo':'✓ Salvo';e.classList.toggle('unsaved',S.dirty);$('save').disabled=!S.loaded||S.working;}
async function api(url,method='GET',data){let options=method==='GET'?{}:{method,headers:{'Content-Type':'application/json'},body:JSON.stringify(data)};const r=await fetch(url,options);let obj;try{obj=await r.json();}catch{throw Error('Resposta inválida do servidor (HTTP '+r.status+')');}if(!r.ok)throw Error(obj.error||'HTTP '+r.status);return obj;}
function parse(svg){const d=new DOMParser().parseFromString(String(svg),'image/svg+xml');if(d.querySelector('parsererror')||d.documentElement.localName!=='svg')throw Error('O documento não é um SVG válido');return d.documentElement;}
function serialize(){if(!S.svg)throw Error('Nenhum desenho carregado');const clone=S.svg.cloneNode(true);clone.removeAttribute('style');clone.setAttribute('xmlns',ns);clone.setAttribute('width','1280');clone.setAttribute('height','720');if(!clone.getAttribute('viewBox'))clone.setAttribute('viewBox','0 0 1280 720');return new XMLSerializer().serializeToString(clone);}
function currentLayers(){if(!S.svg)return [];return Array.from(S.svg.children).filter(n=>n.localName==='g'&&(n.classList.contains('layer')||n.getAttribute('data-name')||n.querySelector('title')));}
function layerName(layer){return layer.querySelector(':scope > title')?.textContent||layer.getAttribute('data-name')||layer.id||'Camada';}
function ensureLayers(){if(!S.svg)return;let groups=currentLayers();if(!groups.length){const group=el('g',{id:uid('camada'),class:'layer','data-name':'Camada 1'});const title=el('title');title.textContent='Camada 1';group.appendChild(title);const movable=Array.from(S.svg.children).filter(n=>n.localName!=='defs'&&n.localName!=='title'&&n.localName!=='desc');for(const n of movable)group.appendChild(n);S.svg.appendChild(group);groups=[group];}for(let i=0;i<groups.length;i++){const g=groups[i];if(!g.id)g.id=uid('camada');g.classList.add('layer');if(!g.querySelector(':scope > title')){let title=el('title');title.textContent='Camada '+(i+1);g.prepend(title);}if(g.getAttribute('data-locked')==='true')S.locked.add(g.id);}if(!S.layer||!S.layer.isConnected)S.layer=groups[groups.length-1];}
function snapshot(){return serialize();}
function remember(){const svg=snapshot();if(S.history[S.index]===svg)return;S.history=S.history.slice(0,S.index+1);S.history.push(svg);if(S.history.length>40)S.history.shift();S.index=S.history.length-1;}
function mutated(){S.dirty=true;state();remember();renderLayers();renderInspector();updateBox();syncQuickColors();}
function undo(){if(S.index<=0)return;S.index--;replace(S.history[S.index],false);S.dirty=true;state();}
function redo(){if(S.index>=S.history.length-1)return;S.index++;replace(S.history[S.index],false);S.dirty=true;state();}
function replace(svg,reset=true){const root=parse(svg);root.setAttribute('width','1280');root.setAttribute('height','720');root.setAttribute('viewBox',root.getAttribute('viewBox')||'0 0 1280 720');root.setAttribute('preserveAspectRatio','xMidYMid meet');S.svg=document.importNode(root,true);S.svg.style.cssText='width:100%;height:100%;display:block;touch-action:none';$('svgHost').replaceChildren(S.svg);S.selected=null;S.layer=null;S.locked.clear();ensureLayers();if(reset){S.history=[snapshot()];S.index=0;}renderLayers();renderInspector();updateBox();syncQuickColors();}
function editableTarget(target){let n=target;while(n&&n!==S.svg){if(SHAPES.has(n.localName))return n;n=n.parentNode;}return null;}
function getLayer(node){while(node&&node.parentNode!==S.svg)node=node.parentNode;return node&&node.localName==='g'?node:null;}
function isLocked(node){let layer=node?.localName==='g'?node:getLayer(node);return layer&&S.locked.has(layer.id);}
function select(node){
 if(node&&isLocked(node)){notice('Esta camada está bloqueada. Desbloqueie no painel Camadas.');return;}
 S.selected=node&&SHAPES.has(node.localName)?node:null;
 if(S.selected&&!S.selected.id){S.selected.id=uid('obj');S.dirty=true;state();remember();}
 if(S.selected)S.layer=getLayer(S.selected)||S.layer;
 renderLayers();renderInspector();updateBox();syncQuickColors();
}
function rgbHex(value){
 if(/^#[0-9a-f]{6}$/i.test(value||''))return value;
 if(/^#[0-9a-f]{3}$/i.test(value||''))return '#'+[...value.slice(1)].map(c=>c+c).join('');
 const m=String(value||'').match(/^rgba?\(\s*(\d+)\s*[, ]\s*(\d+)\s*[, ]\s*(\d+)/i);
 return m?'#'+m.slice(1,4).map(x=>Math.min(255,Number(x)).toString(16).padStart(2,'0')).join(''):null;
}
function syncQuickColors(){
 const selected=S.selected,has=!!selected;
 for(const [attr,id,noneId] of [['fill','quickFill','noFill'],['stroke','quickStroke','noStroke']]){
  const input=$(id),none=$(noneId);if(!input||!none)continue;
  input.disabled=!!(has&&isLocked(selected));none.disabled=!!(has&&isLocked(selected));
  const val=has?selected.getAttribute(attr):S.style[attr];
  const hex=rgbHex(val);
  if(hex)input.value=hex;
  input.title=(attr==='fill'?'Preenchimento':'Contorno')+' atual: '+(val||'padrão');
  none.setAttribute('aria-pressed',String(val==='none'));
 }
 const width=has?Number(selected.getAttribute('stroke-width')||S.style.width):S.style.width;
 $('strokeSize').value=Number.isFinite(width)?String(width):String(S.style.width);
 $('strokePattern').value=has?dashName(selected.getAttribute('stroke-dasharray')||''):S.style.pattern;
 $('deleteObject').disabled=!has||isLocked(selected);
}

function setQuickColor(attr,value){
 if(S.selected&&isLocked(S.selected))return;
 if(value!=='none')S.style[attr]=value;
 if(S.selected){S.selected.setAttribute(attr,value);mutated();}
 syncQuickColors();
}

function dashName(value){
 if(!value||value==='none')return 'solid';
 const parts=value.split(/[ ,]+/).map(Number).filter(Number.isFinite);
 if(parts.length===2&&parts[0]<=parts[1]*.5)return 'dot';
 if(parts.length>=4)return 'dashdot';
 return 'dash';
}
function dashValue(pattern,width){
 const w=Math.max(.5,Number(width)||8);
 return {solid:'',dash:`${3*w} ${1.8*w}`,dot:`${.15*w} ${1.3*w}`,dashdot:`${3*w} ${1.5*w} ${.15*w} ${1.5*w}`}[pattern]||'';
}
function updateStrokeStyle(){
 const width=Math.max(.5,Math.min(150,Number($('strokeSize').value)||8));
 const pattern=$('strokePattern').value;
 S.style.width=width;S.style.pattern=pattern;
 const n=S.selected;if(n&&!isLocked(n)){
  n.setAttribute('stroke-width',String(width));
  const dash=dashValue(pattern,width);
  if(dash)n.setAttribute('stroke-dasharray',dash);else n.removeAttribute('stroke-dasharray');
  n.setAttribute('stroke-linecap','round');
  mutated();
 }
}
function shapeStroke(){const a={stroke:S.style.stroke,'stroke-width':S.style.width,'stroke-linecap':'round','stroke-linejoin':'round'};
 const dash=dashValue(S.style.pattern,S.style.width);if(dash)a['stroke-dasharray']=dash;
 return a;
}
function renderLayers(){const host=$('layersList');host.replaceChildren();for(const layer of currentLayers().slice().reverse()){const card=document.createElement('div');card.className='layerCard'+(layer===S.layer?' active':'');const head=document.createElement('div');head.className='layerHead';const choose=document.createElement('button');choose.className='layerSelect';choose.textContent=layerName(layer);choose.title='Tocar para escolher a camada';choose.onclick=()=>{S.layer=layer;select(null);renderLayers();};head.append(choose);const eye=document.createElement('button');eye.className='iconBtn';eye.textContent=layer.getAttribute('display')==='none'?'◌':'◉';eye.title='Mostrar ou ocultar';eye.onclick=()=>{layer.getAttribute('display')==='none'?layer.removeAttribute('display'):layer.setAttribute('display','none');mutated();};head.append(eye);const lock=document.createElement('button');lock.className='iconBtn';lock.textContent=S.locked.has(layer.id)?'🔒':'♧';lock.title='Bloquear ou desbloquear';lock.onclick=()=>{if(S.locked.has(layer.id)){S.locked.delete(layer.id);layer.removeAttribute('data-locked');}else{S.locked.add(layer.id);layer.setAttribute('data-locked','true');if(S.selected&&getLayer(S.selected)===layer)select(null);}mutated();};head.append(lock);const up=document.createElement('button');up.className='iconBtn';up.textContent='↑';up.title='Subir camada';up.onclick=()=>{layer.parentNode.appendChild(layer);mutated();};head.append(up);card.append(head);
  const children=document.createElement('div');children.className='layerObjects';const objects=Array.from(layer.querySelectorAll('rect,circle,ellipse,path,line,polyline,polygon,text,image,use')).filter(n=>!n.closest('defs'));for(const obj of objects.slice().reverse()){const b=document.createElement('button');b.className='objectRow'+(obj===S.selected?' selected':'');const badge=document.createElement('span');badge.className='objBadge';badge.textContent={rect:'▭',circle:'◯',ellipse:'◯',path:'✎',line:'╱',text:'T',image:'▧'}[obj.localName]||'◆';const desc=document.createElement('span');desc.textContent=(obj.getAttribute('data-name')||obj.id||obj.localName).slice(0,60);b.append(badge,desc);b.onclick=()=>select(obj);children.appendChild(b);}if(!objects.length){let span=document.createElement('small');span.textContent='Camada vazia';children.appendChild(span);}card.append(children);host.append(card);} }
function addLayer(){const title='Camada '+(currentLayers().length+1);const g=el('g',{id:uid('camada'),class:'layer','data-name':title});const t=el('title');t.textContent=title;g.appendChild(t);S.svg.appendChild(g);S.layer=g;S.selected=null;mutated();}
function point(evt){const pt=S.svg.createSVGPoint();pt.x=evt.clientX;pt.y=evt.clientY;const inv=S.svg.getScreenCTM()?.inverse();if(!inv)return{x:0,y:0};const p=pt.matrixTransform(inv);return{x:Math.round(p.x*10)/10,y:Math.round(p.y*10)/10};}
function translate(node,dx,dy,base=''){
 // Coordinates are in the selected element's parent space, not the SVG root.
 // Keep the original transform stable for the full drag.
 node.setAttribute('transform',`translate(${dx.toFixed(2)} ${dy.toFixed(2)}) ${base}`.trim());
}
function toSpace(e,matrix){
 const p=new DOMPoint(e.clientX,e.clientY).matrixTransform(matrix);
 return {x:p.x,y:p.y};
}
function cancelDrag(){
 const d=S.drag;if(!d)return;
 if(d.type==='draw'){d.node.remove();if(S.selected===d.node)S.selected=null;}
 else if(d.type==='move'||d.type==='resize'||d.type==='rotate'){
   if(d.base)d.node.setAttribute('transform',d.base);else d.node.removeAttribute('transform');
 }
 S.drag=null;renderLayers();renderInspector();updateBox();syncQuickColors();
}
function startResize(e,corner){
 const node=S.selected;
 if(!node||isLocked(node))return;
 try{
  const bbox=node.getBBox(),inv=node.getScreenCTM().inverse();
  if(bbox.width<0||bbox.height<0)throw Error('Objeto sem área para redimensionar');
  if(bbox.width<1){bbox.x-=10;bbox.width=20;}
  if(bbox.height<1){bbox.y-=10;bbox.height=20;}
  const handle={nw:[bbox.x,bbox.y],ne:[bbox.x+bbox.width,bbox.y],sw:[bbox.x,bbox.y+bbox.height],se:[bbox.x+bbox.width,bbox.y+bbox.height]}[corner];
  const anchor={nw:[bbox.x+bbox.width,bbox.y+bbox.height],ne:[bbox.x,bbox.y+bbox.height],sw:[bbox.x+bbox.width,bbox.y],se:[bbox.x,bbox.y]}[corner];
  S.drag={type:'resize',node,base:node.getAttribute('transform')||'',inverse:inv,
    handle:{x:handle[0],y:handle[1]},anchor:{x:anchor[0],y:anchor[1]},moved:false,
    startClient:{x:e.clientX,y:e.clientY},pointerId:e.pointerId};
  $('stageScroll').setPointerCapture?.(e.pointerId);
  e.preventDefault();
 }catch(err){notice('Este objeto não pode ser redimensionado diretamente: '+err.message,true);}
}
function startRotate(e){
 const node=S.selected;
 if(S.tool!=='select'||!node||isLocked(node))return;
 try{
  const b=node.getBBox(),inverse=node.getScreenCTM().inverse();
  const center={x:b.x+b.width/2,y:b.y+b.height/2};
  const start=toSpace(e,inverse);
  S.drag={type:'rotate',node,base:node.getAttribute('transform')||'',inverse,center,
   startAngle:Math.atan2(start.y-center.y,start.x-center.x),moved:false,
   startClient:{x:e.clientX,y:e.clientY},pointerId:e.pointerId};
  $('stageScroll').setPointerCapture?.(e.pointerId);e.preventDefault();
 }catch(err){notice('Falha ao iniciar rotação: '+err.message,true);}
}
function rotateDrag(d,e){
 if(Math.hypot(e.clientX-d.startClient.x,e.clientY-d.startClient.y)<5&&!d.moved)return;
 const p=toSpace(e,d.inverse);
 const degrees=(Math.atan2(p.y-d.center.y,p.x-d.center.x)-d.startAngle)*180/Math.PI;
 const {x,y}=d.center;
 d.node.setAttribute('transform',`${d.base} rotate(${degrees.toFixed(3)} ${x.toFixed(2)} ${y.toFixed(2)})`.trim());
 d.moved=true;
}
function resizeDrag(d,e){
 if(Math.hypot(e.clientX-d.startClient.x,e.clientY-d.startClient.y)<5&&!d.moved)return;
 const q=toSpace(e,d.inverse),dx=d.handle.x-d.anchor.x,dy=d.handle.y-d.anchor.y;
 const signed=v=>Math.sign(v||1)*Math.max(.025,Math.min(30,Math.abs(v)));
 let sx=signed((q.x-d.anchor.x)/dx);
 let sy=signed((q.y-d.anchor.y)/dy);
 if(!Number.isFinite(sx)||!Number.isFinite(sy))return;
 // Holding Shift keeps proportional dimensions; crossing the opposite corner mirrors either axis.
 if(e.shiftKey){const scale=Math.max(Math.abs(sx),Math.abs(sy));sx=Math.sign(sx)*scale;sy=Math.sign(sy)*scale;}
 const a=d.anchor;
 const suffix=`translate(${a.x.toFixed(3)} ${a.y.toFixed(3)}) scale(${sx.toFixed(4)} ${sy.toFixed(4)}) translate(${-a.x.toFixed(3)} ${-a.y.toFixed(3)})`;
 d.node.setAttribute('transform',`${d.base} ${suffix}`.trim());d.moved=true;
}

function makeShape(tool,p){
 const shapeAttr={id:uid('obj'),'data-name':{rect:'Retângulo',ellipse:'Elipse',line:'Linha',pen:'Traço',text:'Texto'}[tool]||'Forma'};
 const stroke=shapeStroke();let shape;
 if(tool==='rect')shape=el('rect',{...shapeAttr,x:p.x,y:p.y,width:1,height:1,rx:10,fill:S.style.fill,...stroke});
 if(tool==='ellipse')shape=el('ellipse',{...shapeAttr,cx:p.x,cy:p.y,rx:1,ry:1,fill:S.style.fill,...stroke});
 if(tool==='line')shape=el('line',{...shapeAttr,x1:p.x,y1:p.y,x2:p.x,y2:p.y,...stroke});
 if(tool==='pen')shape=el('path',{...shapeAttr,d:`M ${p.x} ${p.y}`,fill:'none',...stroke});
 if(tool==='text'){shape=el('text',{...shapeAttr,x:p.x,y:p.y,'font-size':64,'font-family':'sans-serif',fill:S.style.fill});shape.textContent='Novo texto';}
 return shape;
}
function shapeDraw(shape,start,p,tool){const dx=p.x-start.x,dy=p.y-start.y;if(tool==='rect'){shape.setAttribute('x',Math.min(start.x,p.x));shape.setAttribute('y',Math.min(start.y,p.y));shape.setAttribute('width',Math.max(1,Math.abs(dx)));shape.setAttribute('height',Math.max(1,Math.abs(dy)));}else if(tool==='ellipse'){shape.setAttribute('cx',(start.x+p.x)/2);shape.setAttribute('cy',(start.y+p.y)/2);shape.setAttribute('rx',Math.max(1,Math.abs(dx)/2));shape.setAttribute('ry',Math.max(1,Math.abs(dy)/2));}else if(tool==='line'){shape.setAttribute('x2',p.x);shape.setAttribute('y2',p.y);}else if(tool==='pen'){const d=shape.getAttribute('d')||'';shape.setAttribute('d',d+` L ${p.x} ${p.y}`);}}
function pointerDown(e){
 if(e.button!==0&&e.pointerType==='mouse')return;
 const p=point(e);
 if(S.tool==='select'){
  const shape=editableTarget(e.target);
  if(!shape||isLocked(shape)){select(null);return;}
  // On the first tap, select only. A real drag starts after 7 screen pixels.
  // Do not use the viewport SVG coordinates for parent/group transforms.
  select(shape);
  try{
   const parent=shape.parentElement;
   const inverse=parent.getScreenCTM().inverse();
   S.drag={type:'move',node:shape,base:shape.getAttribute('transform')||'',inverse,
    start:toSpace(e,inverse),startClient:{x:e.clientX,y:e.clientY},moved:false,pointerId:e.pointerId};
  }catch(err){notice('Não foi possível iniciar movimento: '+err.message,true);return;}
 }else{
  if(!S.layer||isLocked(S.layer)){notice('Escolha ou crie uma camada desbloqueada.');return;}
  const shape=makeShape(S.tool,p);if(!shape)return;
  S.layer.appendChild(shape);
  S.drag={type:'draw',tool:S.tool,node:shape,start:p,last:p,moved:false,pointerId:e.pointerId};
  S.selected=shape;renderInspector();renderLayers();syncQuickColors();
 }
 if(S.drag){e.preventDefault();try{$('stageScroll').setPointerCapture(e.pointerId);}catch{}}
}
function pointerMove(e){
 if(S.svg){const p=point(e);$('xyInfo').textContent='x: '+Math.round(p.x)+' · y: '+Math.round(p.y);}
 const d=S.drag;if(!d||d.pointerId!==e.pointerId)return;
 if(d.type==='resize'){resizeDrag(d,e);updateBox();return;}
 if(d.type==='rotate'){rotateDrag(d,e);updateBox();return;}
 if(d.type==='move'){
  if(Math.hypot(e.clientX-d.startClient.x,e.clientY-d.startClient.y)<7&&!d.moved)return;
  const pos=toSpace(e,d.inverse);
  translate(d.node,pos.x-d.start.x,pos.y-d.start.y,d.base);d.moved=true;
 }else if(d.tool!=='text'){
  const p=point(e);shapeDraw(d.node,d.start,p,d.tool);
  if(Math.abs(p.x-d.start.x)+Math.abs(p.y-d.start.y)>1)d.moved=true;
 }
 updateBox();
}
function pointerUp(e){
 if(!S.drag||S.drag.pointerId!==e.pointerId)return;
 const d=S.drag;S.drag=null;
 try{$('stageScroll').releasePointerCapture?.(e.pointerId);}catch{}
 if(d.type==='move'||d.type==='resize'||d.type==='rotate'){
  if(d.moved)mutated();
 }else{
  if(d.tool==='rect'&&!d.moved){d.node.setAttribute('width',220);d.node.setAttribute('height',120);}
  if(d.tool==='ellipse'&&!d.moved){d.node.setAttribute('rx',90);d.node.setAttribute('ry',60);}
  if(d.tool==='line'&&!d.moved){d.node.setAttribute('x2',Number(d.node.getAttribute('x1'))+160);}
  if(d.tool==='pen'&&!d.moved)d.node.setAttribute('d',d.node.getAttribute('d')+' l 1 1');
  mutated();
 }
 if(S.tool==='select')select(d.node);else{S.selected=null;renderInspector();renderLayers();syncQuickColors();updateBox();}
}
// Navegação da prancheta: dois dedos ampliam/reduzem e deslocam sem editar o SVG.
// Estado de navegação é apenas visual; não entra no documento ou no undo.
function viewport(){
 $('artboard').style.transform=`translate(${S.panX}px, ${S.panY}px) scale(${S.zoom})`;
 $('zoomLabel').textContent=Math.round(S.zoom*100)+'%';
 requestAnimationFrame(updateBox);
}
function touchPair(){
 const [a,b]=Array.from(S.touches.values()).slice(0,2);
 return {x:(a.x+b.x)/2,y:(a.y+b.y)/2,d:Math.max(1,Math.hypot(a.x-b.x,a.y-b.y))};
}
function abortDraftForPinch(){cancelDrag();}
function startPinch(){
 if(S.touches.size<2)return;
 abortDraftForPinch();
 const p=touchPair(),r=$('artboard').getBoundingClientRect();
 // O centro sem translação é fixo durante o gesto (transform-origin: center).
 S.pinch={first:p,zoom:S.zoom,panX:S.panX,panY:S.panY,
  cx:r.left+r.width/2-S.panX,cy:r.top+r.height/2-S.panY};
 S.gestureUsed=true;
}
function touchDown(e){
 S.touches.set(e.pointerId,{x:e.clientX,y:e.clientY});
 try{$('stageScroll').setPointerCapture(e.pointerId);}catch{}
 if(S.touches.size>=2){startPinch();e.preventDefault();return;}
 if(!S.gestureUsed&&S.svg.contains(e.target))pointerDown(e);
}
function touchMove(e){
 if(!S.touches.has(e.pointerId))return;
 S.touches.set(e.pointerId,{x:e.clientX,y:e.clientY});
 if(S.touches.size>=2){
  if(!S.pinch)startPinch();
  const start=S.pinch,now=touchPair();
  S.zoom=Math.min(5,Math.max(0.3,start.zoom*now.d/start.first.d));
  const ratio=S.zoom/start.zoom;
  // Mantém o ponto sob os dedos ancorado enquanto a distância e o centro mudam.
  S.panX=start.panX+now.x-start.first.x+(1-ratio)*(start.first.x-start.cx-start.panX);
  S.panY=start.panY+now.y-start.first.y+(1-ratio)*(start.first.y-start.cy-start.panY);
  viewport();e.preventDefault();return;
 }
 if(S.gestureUsed){e.preventDefault();return;}
 pointerMove(e);
}
function touchEnd(e){
 const had=S.touches.delete(e.pointerId);
 try{$('stageScroll').releasePointerCapture(e.pointerId);}catch{}
 if(S.pinch&&S.touches.size<2)S.pinch=null;
 if(S.gestureUsed){
  if(S.touches.size===0)S.gestureUsed=false;
  e.preventDefault();return;
 }
 if(had&&S.drag)pointerUp(e);
}
function editorPointerDown(e){if(!S.svg)return;const rot=e.target.closest?.('[data-rotate]');if(rot&&S.selected){if(e.pointerType==='touch'){S.touches.set(e.pointerId,{x:e.clientX,y:e.clientY});if(S.touches.size>=2){startPinch();return;}}return startRotate(e);}const handle=e.target.closest?.('[data-resize]');if(handle&&S.selected){if(e.pointerType==='touch'){S.touches.set(e.pointerId,{x:e.clientX,y:e.clientY});if(S.touches.size>=2){startPinch();return;}}return startResize(e,handle.dataset.resize);}e.pointerType==='touch'?touchDown(e):pointerDown(e);}
function editorPointerMove(e){e.pointerType==='touch'?touchMove(e):pointerMove(e);}
function editorPointerUp(e){if(e.type==='pointercancel'){abortDraftForPinch();if(e.pointerType==='touch')touchEnd(e);return;}e.pointerType==='touch'?touchEnd(e):pointerUp(e);}
function updateBox(){
 const box=$('selectionBox'),node=S.selected;
 if(!node||!node.isConnected||S.tool!=='select'||S.drag?.type==='draw'||S.touches.size>=2){box.hidden=true;return;}
 try{
  const a=node.getBoundingClientRect(),b=$('artboard').getBoundingClientRect();
  if(!(a.width>0&&a.height>0)||!Number.isFinite(a.left)){box.hidden=true;return;}
  box.hidden=false;
  box.style.left=((a.left-b.left)/S.zoom)+'px';box.style.top=((a.top-b.top)/S.zoom)+'px';
  box.style.width=(a.width/S.zoom)+'px';box.style.height=(a.height/S.zoom)+'px';
 }catch{box.hidden=true;}
}
function esc(str){return String(str??'').replace(/[&"<>]/g,c=>({'&':'&amp;','"':'&quot;','<':'&lt;','>':'&gt;'}[c]));}
function field(label,attr,type='text'){let value=attr==='textContent'?S.selected?.textContent:S.selected?.getAttribute(attr);if(type==='number'&&value!=null&&value!==''&&Number.isFinite(Number(value)))value=Number(Number(value).toFixed(2));return `<label>${esc(label)}<input data-attr="${esc(attr)}" type="${type}" value="${esc(value??'')}" ${type==='number'?'step="any"':''}></label>`;}
function renderInspector(){const host=$('inspectorContent');if(!S.svg){host.innerHTML='<p>Carregando…</p>';return;}if(!S.selected){const layer=S.layer;host.innerHTML=`<div class="groupTitle">Camada ativa</div><label>Nome da camada<input id="layerRename" value="${esc(layer?layerName(layer):'')}"></label><p class="help">Desenhe retângulos, elipses, linhas, texto ou traços. Toque em um objeto para editar suas propriedades e arrastá-lo.</p><p class="help">Os desenhos ficam salvos como SVG real, com camadas e objetos editáveis.</p>`;const rename=$('layerRename');if(rename)rename.onchange=()=>{const t=rename.value.trim().slice(0,80)||'Camada';S.layer?.setAttribute('data-name',t);const title=S.layer?.querySelector(':scope > title');if(title)title.textContent=t;mutated();};return;}
 const n=S.selected,tag=n.localName;let html='<div class="groupTitle">'+esc({rect:'Retângulo',ellipse:'Elipse',circle:'Círculo',line:'Linha',path:'Traçado',text:'Texto',image:'Imagem'}[tag]||tag)+'</div>';
 html+=field('Nome do objeto','data-name');if(tag==='text')html+=field('Conteúdo','textContent');
 const dimensions={rect:['x','y','width','height','rx'],ellipse:['cx','cy','rx','ry'],circle:['cx','cy','r'],line:['x1','y1','x2','y2'],text:['x','y','font-size'],image:['x','y','width','height'],path:[]};const attrs=dimensions[tag]||[];
 if(attrs.length){html+='<div class="groupTitle">Posição e dimensões</div><div class="fieldGrid">';for(const a of attrs)html+=field(a,a,'number');html+='</div>';}html+='<div class="groupTitle">Aparência</div><div class="fieldGrid">';if(tag!=='line'&&tag!=='image')html+=field('Preenchimento','fill','color');if(tag!=='image')html+=field('Contorno','stroke','color');if(tag!=='image')html+=field('Espessura','stroke-width','number');html+=field('Opacidade (0–1)','opacity','number');html+='</div>';
 html+='<div class="groupTitle">Transformação SVG</div>'+field('Transformação','transform');if(tag==='path')html+='<div class="groupTitle">Traçado SVG</div>'+field('Comandos d','d');host.innerHTML=html;
 for(const input of host.querySelectorAll('[data-attr]')){const attr=input.dataset.attr;if(input.type==='color'){let v=n.getAttribute(attr);if(!v||!/^#[0-9a-f]{6}$/i.test(v))input.value=attr==='stroke'?'#1d2630':'#d77b53';}input.onchange=()=>{if(!S.selected||!S.selected.isConnected)return;let value=input.value;if(attr==='textContent')n.textContent=value;else if(value==='')n.removeAttribute(attr);else n.setAttribute(attr,value);mutated();};}
}
function changeTool(t){S.tool=t;if(t!=='select'){S.selected=null;renderLayers();renderInspector();syncQuickColors();}updateBox();document.querySelectorAll('[data-tool]').forEach(b=>b.classList.toggle('active',b.dataset.tool===t));$('toolHint').textContent={select:'Toque para selecionar; arraste para mover; use as alças para redimensionar',rect:'Arraste para desenhar um retângulo',ellipse:'Arraste para desenhar uma elipse',line:'Arraste para criar uma linha',pen:'Desenhe livremente com o dedo',text:'Toque para inserir um texto'}[t]||'';}
async function openScene(){if(!name||!Number.isInteger(scene)||scene<1)throw Error('Abra o editor através de uma cena SVG do Estúdio');const d=await api(`/api/svg/document?name=${encodeURIComponent(name)}&scene=${scene}`);replace(d.svg);S.revision=d.revision;S.loaded=true;S.dirty=false;state();$('sceneTag').textContent=`${name} · Cena ${scene} · ${d.title||'sem título'}`;notice('Documento carregado. Use as ferramentas e clique em Salvar cena.');}
async function save(){if(S.working)return;S.working=true;state();try{const svg=serialize();parse(svg);const r=await api('/api/svg/document','POST',{name,scene,svg,revision:S.revision});S.revision=r.revision;S.dirty=false;notice('Cena salva. Cache das outras cenas preservado.');try{localStorage.setItem('estudioSvgVectorSave',JSON.stringify({name,scene,ts:Date.now()}));}catch(_){/* Armazenamento opcional: não altera o resultado do salvamento. */}}catch(e){notice('Falha ao salvar: '+e.message,true);}finally{S.working=false;state();}}
function download(blob,filename){const a=document.createElement('a'),url=URL.createObjectURL(blob);a.href=url;a.download=filename;document.body.appendChild(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),10000);}
async function exportFile(){try{const svg=serialize(),format=$('exportType').value,filename=(name||'desenho')+'_cena_'+(scene||1);parse(svg);if(format==='svg'){download(new Blob([svg],{type:'image/svg+xml;charset=utf-8'}),filename+'.svg');notice('SVG exportado.');return;}const blob=new Blob([svg],{type:'image/svg+xml;charset=utf-8'}),url=URL.createObjectURL(blob);try{const im=new Image();await new Promise((resolve,reject)=>{im.onload=resolve;im.onerror=()=>reject(Error('O navegador não pôde rasterizar este SVG. Experimente exportar como SVG.'));im.src=url;});const cv=document.createElement('canvas');cv.width=1280;cv.height=720;const cx=cv.getContext('2d');if(format==='jpeg'){cx.fillStyle='#fff';cx.fillRect(0,0,cv.width,cv.height);}cx.drawImage(im,0,0,cv.width,cv.height);const mime=format==='jpeg'?'image/jpeg':format==='webp'?'image/webp':'image/png';const output=await new Promise(r=>cv.toBlob(r,mime,0.93));if(!output)throw Error('Formato indisponível no navegador');download(output,filename+'.'+(format==='jpeg'?'jpg':format));notice('Imagem '+format.toUpperCase()+' exportada.');}finally{URL.revokeObjectURL(url);}}catch(e){notice('Falha ao exportar: '+e.message,true);}}
async function importSvg(file){if(!file)return;if(file.size>4_000_000)throw Error('SVG maior que 4 MB');const content=await file.text();parse(content);const safe=await api('/api/svg/clean','POST',{svg:content});replace(safe.svg);S.dirty=true;state();notice('SVG importado. Clique em Salvar cena para persistir.');}
async function importImage(file){if(!file)return;if(file.size>6_000_000)throw Error('Imagem maior que 6 MB');const b=new Image();const src=URL.createObjectURL(file);try{await new Promise((ok,fail)=>{b.onload=ok;b.onerror=()=>fail(Error('O arquivo não é uma imagem válida'));b.src=src;});const scale=Math.min(1,1400/Math.max(b.naturalWidth,b.naturalHeight)),cv=document.createElement('canvas');cv.width=Math.max(1,Math.round(b.naturalWidth*scale));cv.height=Math.max(1,Math.round(b.naturalHeight*scale));cv.getContext('2d').drawImage(b,0,0,cv.width,cv.height);const data=cv.toDataURL('image/png');if(!S.layer||isLocked(S.layer))addLayer();const w=Math.min(850,b.naturalWidth),h=Math.max(1,w*b.naturalHeight/b.naturalWidth);const im=el('image',{id:uid('imagem'),'data-name':file.name.slice(0,80),x:(1280-w)/2,y:(720-h)/2,width:w,height:h,href:data});S.layer.append(im);S.selected=im;mutated();notice('Imagem incorporada como objeto SVG. Salve a cena para gravá-la no Termux.');}finally{URL.revokeObjectURL(src);}}
function openCode(){$('codeText').value=serialize();$('codeDialog').showModal();}
async function applyCode(){try{const xml=$('codeText').value;parse(xml);const safe=await api('/api/svg/clean','POST',{svg:xml});replace(safe.svg);S.dirty=true;state();$('codeDialog').close();notice('Código SVG aplicado ao desenho. Salve a cena.');}catch(e){notice('Falha no código: '+e.message,true);}}
function setZoom(z,fit=false){S.zoom=Math.min(5,Math.max(0.3,z));if(fit){S.panX=0;S.panY=0;}viewport();}
function deleteSelected(){if(!S.selected||isLocked(S.selected))return;S.selected.remove();S.selected=null;mutated();}
function shiftSelected(dir){if(!S.selected)return;const p=S.selected.parentNode;if(dir==='front')p.append(S.selected);else{const prev=S.selected.previousElementSibling;if(prev&&prev.localName!=='title')p.insertBefore(S.selected,prev);}mutated();}
function mobilePanel(p){const workspace=document.querySelector('.workspace');workspace.classList.remove('panel-canvas','panel-layers','panel-inspector');workspace.classList.add('panel-'+p);document.querySelectorAll('[data-panel]').forEach(b=>b.classList.toggle('active',b.dataset.panel===p));}
function initControls(){document.querySelectorAll('[data-tool]').forEach(b=>b.onclick=()=>{changeTool(b.dataset.tool);mobilePanel('canvas');});$('quickFill').oninput=e=>setQuickColor('fill',e.target.value);$('quickStroke').oninput=e=>setQuickColor('stroke',e.target.value);$('noFill').onclick=()=>setQuickColor('fill','none');$('noStroke').onclick=()=>setQuickColor('stroke','none');$('strokeSize').onchange=updateStrokeStyle;$('strokePattern').onchange=updateStrokeStyle;$('deleteObject').onclick=deleteSelected;$('addLayer').onclick=addLayer;$('addLayer2').onclick=addLayer;$('save').onclick=save;$('back').onclick=()=>{if(S.dirty&&!confirm('Há alterações não salvas. Deseja sair?'))return;location.href='/';};$('undo').onclick=undo;$('redo').onclick=redo;$('deleteSelection').onclick=deleteSelected;$('sendBack').onclick=()=>shiftSelected('back');$('bringFront').onclick=()=>shiftSelected('front');$('exportFile').onclick=exportFile;$('importSvg').onclick=()=>$('svgUpload').click();$('importImage').onclick=()=>$('imageUpload').click();$('svgUpload').onchange=async e=>{try{await importSvg(e.target.files[0]);}catch(err){notice(err.message,true);}e.target.value='';};$('imageUpload').onchange=async e=>{try{await importImage(e.target.files[0]);}catch(err){notice(err.message,true);}e.target.value='';};$('showCode').onclick=openCode;$('applyCode').onclick=applyCode;$('closeCode').onclick=$('cancelCode').onclick=()=>$('codeDialog').close();$('zoomIn').onclick=()=>setZoom(S.zoom*1.2);$('zoomOut').onclick=()=>setZoom(S.zoom/1.2);$('zoomFit').onclick=()=>setZoom(1,true);document.querySelectorAll('[data-panel]').forEach(b=>b.onclick=()=>mobilePanel(b.dataset.panel));$('stageScroll').addEventListener('pointerdown',editorPointerDown);$('stageScroll').addEventListener('pointermove',editorPointerMove);$('stageScroll').addEventListener('pointerup',editorPointerUp);$('stageScroll').addEventListener('pointercancel',editorPointerUp);document.addEventListener('keydown',e=>{if(e.target.closest('input,textarea,[contenteditable],dialog'))return;if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='s'){e.preventDefault();save();}else if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='z'){e.preventDefault();e.shiftKey?redo():undo();}else if(e.key==='Delete'||e.key==='Backspace'){deleteSelected();}});window.addEventListener('beforeunload',e=>{if(S.dirty){e.preventDefault();e.returnValue='';}});window.addEventListener('resize',()=>requestAnimationFrame(updateBox));}
async function main(){initControls();mobilePanel('canvas');await openScene();}
main().catch(e=>{console.error(e);notice(e.message,true);});
