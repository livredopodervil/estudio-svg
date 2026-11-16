/* Estúdio SVG — editor incremental de camadas; Rogério Duarte. */
(function(global){
'use strict';
const roles=['imagem','conteudo','cabecalho','titulo','subtitulo','rodape'];
const names={imagem:'Imagem',conteudo:'Conteúdo / gráfico',cabecalho:'Cabeçalho',titulo:'Título',subtitulo:'Subtítulo',rodape:'Rodapé'};
const NS='http://www.w3.org/2000/svg', clone=x=>JSON.parse(JSON.stringify(x)), cap=(x,a,b)=>Math.max(a,Math.min(b,x));
function defaultZ(scene,key){return key==='imagem'?(scene.imagem?.modo==='fundo'?10:30):({conteudo:20,cabecalho:40,titulo:50,subtitulo:60,rodape:70})[key];}
function present(scene,key){if(key==='imagem')return !!scene.imagem?.arquivo;if(key==='titulo'||key==='subtitulo')return !!scene[key];if(key==='conteudo')return scene.tipo!=='foto'||!scene.imagem?.arquivo;return true;}
function config(scene,key){return {z:defaultZ(scene,key),dx:0,dy:0,oculta:false,...scene.camadas?.[key]};}
function sortedRoles(scene){return roles.filter(k=>present(scene,k)).sort((a,b)=>config(scene,a).z-config(scene,b).z||roles.indexOf(a)-roles.indexOf(b));}
function editRoles(scene,keys,op,dx=0,dy=0){
 const order=sortedRoles(scene), selected=order.filter(k=>keys.includes(k));if(!selected.length)return false;
 scene.camadas=scene.camadas||{};
 const set=(k,values)=>scene.camadas[k]={...config(scene,k),...values};
 if(op==='front'||op==='back'){
  const others=order.filter(k=>!selected.includes(k));const target=op==='front'?[...others,...selected]:[...selected,...others];
  target.forEach((k,i)=>set(k,{z:(i+1)*10}));
 }else for(const k of selected){const c=config(scene,k);
  if(op==='move')set(k,{dx:cap(c.dx+dx,-4800,4800),dy:cap(c.dy+dy,-4800,4800)});
  else if(op==='hide'||op==='show')set(k,{oculta:op==='hide'});
  else if(op==='reset')delete scene.camadas[k];
 }
 if(!Object.keys(scene.camadas).length)delete scene.camadas;
 return true;
}
function parseArt(scene){
 if(scene.tipo!=='svg'||!String(scene.svg||'').trim())return null;
 const p=new DOMParser(),raw=scene.svg.trim();let doc=p.parseFromString(raw,'image/svg+xml');
 if(doc.querySelector('parsererror')||doc.documentElement.localName!=='svg')doc=p.parseFromString(`<svg xmlns="${NS}" xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 1280 720">${raw}</svg>`,'image/svg+xml');
 if(doc.querySelector('parsererror')||doc.documentElement.localName!=='svg')return null;
 const root=doc.documentElement, allowed=new Set(['g','path','circle','ellipse','rect','line','polyline','polygon','text','image','use']);
 const all=[...root.querySelectorAll('[id]')],counts=new Map();all.forEach(el=>counts.set(el.id,(counts.get(el.id)||0)+1));
 const objects=all.filter(el=>allowed.has(el.localName)&&counts.get(el.id)===1&&!el.closest('defs,clipPath,mask,pattern,symbol,marker,filter'));
 return {root,objects};
}
function editObjects(scene,ids,op,dx,dy){
 const art=parseArt(scene);if(!art)return false;
 const picked=art.objects.filter(el=>ids.includes(el.id));
 // A selected group moves once, not again for each selected descendant.
 const els=picked.filter(el=>!picked.some(parent=>parent!==el&&parent.contains(el)));
 if(!els.length||!['front','back','move','hide','show','delete'].includes(op))return false;
 const parents=new Set(els.map(el=>el.parentNode));
 if(op==='front'||op==='back')for(const parent of parents){
   const subset=els.filter(el=>el.parentNode===parent),remaining=[...parent.children].filter(el=>!subset.includes(el)&&!['defs','title','desc'].includes(el.localName));
   if(op==='front')subset.forEach(el=>parent.appendChild(el));else{const before=remaining[0]||null;subset.forEach(el=>parent.insertBefore(el,before));}
 }else if(op==='delete'){
  const removed=new Set();for(const el of els){if(el.id)removed.add(el.id);for(const child of el.querySelectorAll('[id]'))removed.add(child.id);}
  // Protect external <use>, gradients, masks and other ID references.
  for(const node of art.root.querySelectorAll('*')){
    if(els.some(el=>el===node||el.contains(node)))continue;
    for(const a of node.attributes){for(const id of removed){if(a.value===`#${id}`||a.value.includes(`url(#${id})`)||a.value.includes(`url('#${id}')`)||a.value.includes(`url("#${id}")`))throw Error('Objeto '+id+' é referenciado por outro elemento. Oculte em vez de excluir.');}}
  }
  els.forEach(el=>el.remove());
 }else for(const el of els){
  if(op==='move')el.setAttribute('transform',`translate(${dx} ${dy}) ${el.getAttribute('transform')||''}`.trim());
  else if(op==='hide')el.setAttribute('display','none');else el.removeAttribute('display');
 }
 const result=new XMLSerializer().serializeToString(art.root);if(result.length>2000000)throw Error('SVG excederia o limite de 2 MB.');
 scene.svg=result;return true;
}
function connect({get,change,notify,jump}){
 const host=document.getElementById('stageShell'),stage=document.getElementById('stage');
 const panel=document.createElement('section');panel.hidden=true;panel.style.cssText='border:1px solid #846e5c;border-radius:9px;padding:10px;margin:8px 0;max-width:100%;';
 panel.innerHTML=`<div style="display:flex;justify-content:space-between;gap:8px"><b>Camadas e objetos SVG</b><button type="button" data-action="close">Fechar</button></div>
 <p class="info">Toque em um objeto na prévia ou marque abaixo. Ocultar remove da composição sem apagar o arquivo. Para SVG, a ordem é relativa ao grupo pai.</p>
 <label>Escopo <select id="layersScopeV36"><option value="scene">Cena atual</option><option value="all">Todas as cenas (mesmos tipos/IDs)</option></select></label>
 <div id="layersListV36" style="max-height:210px;overflow:auto;margin:6px 0"></div>
 <div style="display:flex;flex-wrap:wrap;gap:5px"><button data-action="all">Todas as camadas</button><button data-action="clear">Limpar seleção</button><button data-action="front">Trazer à frente</button><button data-action="back">Enviar atrás</button><button data-action="hide">Ocultar da cena</button><button data-action="delete">Excluir SVG</button><button data-action="show">Mostrar</button><button data-action="reset">Restaurar camadas</button><button data-action="undo">Desfazer</button></div>
 <div style="display:flex;flex-wrap:wrap;gap:5px;align-items:center;margin-top:5px"><label>Passo <input id="layersStepV36" type="number" min="1" max="480" value="20" style="width:65px"></label><button data-action="left" aria-label="Mover esquerda">←</button><button data-action="right" aria-label="Mover direita">→</button><button data-action="up" aria-label="Mover acima">↑</button><button data-action="down" aria-label="Mover abaixo">↓</button></div><p id="layersStatusV36" class="info"></p>`;
 host.insertAdjacentElement('beforebegin',panel);
 const list=panel.querySelector('#layersListV36'),status=panel.querySelector('#layersStatusV36'),scope=panel.querySelector('#layersScopeV36');
 let selected=new Set(),history=[],currentProject=null,lastScene=null;
 function sync(){const state=get();if(!state.project)return null;
  if(currentProject!==state.project){selected.clear();history=[];currentProject=state.project;lastScene=null;}
  if(scope.value==='scene'&&lastScene!==null&&lastScene!==state.selected)selected.clear();lastScene=state.selected;return state;
 }
 function render(){if(panel.hidden)return;const state=sync();if(!state)return;const scene=state.project.cenas[state.selected];list.replaceChildren();
  const append=(id,title)=>{const label=document.createElement('label');label.style.cssText='display:flex;gap:8px;align-items:center;padding:4px';const cb=document.createElement('input');cb.type='checkbox';cb.checked=selected.has(id);cb.onchange=()=>{if(cb.checked)selected.add(id);else selected.delete(id);highlight();};label.append(cb,document.createTextNode(title));list.append(label);};
  if(scope.value==='all'){
   for(const k of [...roles].reverse()){
    const count=state.project.cenas.filter(c=>present(c,k)).length;if(count)append('role:'+k,names[k]+' · '+count+' cena(s)');
   }
   const counts=new Map();for(const c of state.project.cenas){const art=parseArt(c);if(art)for(const el of art.objects)counts.set(el.id,(counts.get(el.id)||0)+1);}
   for(const [id,count] of counts)append('svg:'+id,'SVG · '+id+' · '+count+' cena(s)');
  }else{
   sortedRoles(scene).slice().reverse().forEach(k=>append('role:'+k,names[k]+(config(scene,k).oculta?' · oculta':'')));
   const art=parseArt(scene);if(art)art.objects.slice().reverse().forEach(el=>append('svg:'+el.id,'SVG · '+el.id+(el.getAttribute('display')==='none'?' · oculto':'')));
  }
  status.textContent=`Cena ${state.selected+1} · ${selected.size} selecionado(s)`;highlight();
 }
 function highlight(){for(const el of stage.querySelectorAll('[data-studio-layer], [id]')){
   const active=selected.has('role:'+el.dataset.studioLayer)||selected.has('svg:'+el.id);
   if(active)el.style.outline='2px dashed #00d9e8';else if(el.style.outline==='rgb(0, 217, 232) dashed 2px'||el.style.outline.includes('dashed'))el.style.removeProperty('outline');
 }status.textContent=`Cena ${get().selected+1} · ${selected.size} selecionado(s)`;}
 function close(){panel.hidden=true;selected.clear();for(const el of stage.querySelectorAll('[data-studio-layer],[id]'))if(el.style.outline.includes('dashed'))el.style.removeProperty('outline');}
 function action(op){const state=sync();if(!state||state.playing){notify('Pause a prévia antes de editar.',true);return;}
  if(op==='close'){close();return;}
  if(op==='all'){const available=scope.value==='all'?roles.filter(k=>state.project.cenas.some(c=>present(c,k))):sortedRoles(state.project.cenas[state.selected]);for(const k of available)selected.add('role:'+k);render();return;}
  if(op==='clear'){selected.clear();render();return;}
  if(op==='undo'){
   const last=history.pop();if(!last){notify('Não há operação para desfazer.',true);return;}
   if(last.some(x=>!state.project.cenas.some(c=>c.id===x.id))){history.push(last);notify('Cenas alteradas desde a operação; desfazer interrompido.',true);return;}
   // Do not overwrite edits made later outside the layer panel.
   if(last.some(x=>{const c=state.project.cenas.find(c=>c.id===x.id);return JSON.stringify([c.camadas||null,c.svg])!==x.after;})){history.push(last);notify('Outra edição alterou a cena; use o histórico da prancheta.',true);return;}
   for(const x of last){const c=state.project.cenas.find(c=>c.id===x.id);if(x.camadas)c.camadas=x.camadas;else delete c.camadas;c.svg=x.svg;}change();render();return;
  }
  if(!selected.size){notify('Selecione camadas ou objetos.',true);return;}
  const step=cap(Number(panel.querySelector('#layersStepV36').value)||20,1,480),moves={left:[-step,0],right:[step,0],up:[0,-step],down:[0,step]},[dx,dy]=moves[op]||[0,0],cmd=moves[op]?'move':op;
  const keys=[...selected].filter(k=>k.startsWith('role:')).map(k=>k.slice(5)),ids=[...selected].filter(k=>k.startsWith('svg:')).map(k=>k.slice(4));
  const indices=scope.value==='all'?state.project.cenas.map((_,i)=>i):[state.selected];
  if(cmd==='delete'&&!ids.length){notify('Selecione IDs SVG. Camadas de título, imagem e conteúdo são ocultadas, não destruídas.',true);return;}
  if(cmd==='delete'&&!confirm('Excluir objetos SVG selecionados? Os arquivos de mídia não serão apagados.'))return;
  if(scope.value==='all'&&!confirm(`Aplicar ${op==='hide'?'ocultação':'operação'} a até ${indices.length} cenas, por tipo de camada ou ID SVG?`))return;
  try{const staged=[];for(const i of indices){const original=state.project.cenas[i],scene=clone(original);const a=cmd==='delete'?false:editRoles(scene,keys,cmd,dx,dy),b=editObjects(scene,keys.includes('conteudo')&&['move','hide','show'].includes(cmd)?[]:ids,cmd,dx,dy);if(a||b){staged.push({i,scene,backup:{id:original.id,camadas:original.camadas?clone(original.camadas):null,svg:original.svg,after:JSON.stringify([scene.camadas||null,scene.svg])}});}}
   if(!staged.length){notify('Nenhuma camada ou ID correspondente.',true);return;}
   for(const x of staged)state.project.cenas[x.i]=x.scene;history.push(staged.map(x=>x.backup));if(history.length>30)history.shift();change();render();notify(`${staged.length} cena(s) alterada(s). Use Salvar.`);
  }catch(e){notify(e.message,true);}
 }
 panel.addEventListener('click',e=>{const b=e.target.closest('[data-action]');if(b)action(b.dataset.action);});
 scope.onchange=()=>{selected.clear();render();};
 stage.addEventListener('click',e=>{if(panel.hidden)return;const state=sync();if(!state||state.playing)return;const art=parseArt(state.project.cenas[state.selected]),ids=new Set(art?.objects.map(el=>el.id)||[]);let node=e.target,target=null;
  while(node&&node!==stage){if(ids.has(node.id)){target='svg:'+node.id;break;}if(node.dataset?.studioLayer){target='role:'+node.dataset.studioLayer;break;}node=node.parentElement;}
  if(target){if(selected.has(target))selected.delete(target);else selected.add(target);render();}
 });
 new MutationObserver(()=>{if(!panel.hidden&&!get().playing)render();}).observe(stage,{childList:true});
 return {open(){panel.hidden=false;render();}};
}
global.StudioLayersV36={connect,editRoles,config,sortedRoles,parseArt,editObjects};
})(typeof window==='undefined'?globalThis:window);
