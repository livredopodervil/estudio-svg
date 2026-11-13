(() => {'use strict';
const $ = id => document.getElementById(id);
const clone = v => JSON.parse(JSON.stringify(v));
const params = new URL(location.href).searchParams;
const name = params.get('name') || 'demo_organico';
const index = Math.max(0, Number(params.get('scene') || 1) - 1);
let project = null, baseline = '', selected = '', progress = 0, playing = false, lastTime = 0, lastDraw = 0;
let history = [], generation = 0;
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const status = text => { $('status').textContent = text; };
const request = async(path, options={}) => {
 const r = await fetch(path,options), raw = await r.text();
 let data; try { data=JSON.parse(raw); } catch { data=raw; }
 if(!r.ok) throw Error(data?.error || `HTTP ${r.status}`);
 return data;
};
const post = (path, value) => request(path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(value)});
const scene = () => project.cenas[index];
const spatial = () => scene().espacial;
const unique = prefix => {let n=1;while(spatial().objetos.some(o=>o.id===prefix+n))n++;return prefix+n;};
function remember(){history.push(clone(spatial())); if(history.length>40)history.shift();}
function changed(redraw=true){status('Alterações ainda não salvas');renderControls();if(redraw)preview();}
function currentObject(){return spatial().objetos.find(o=>o.id===selected);}
function renderControls(){
 const all=spatial().objetos; if(!all.some(o=>o.id===selected))selected=all[0]?.id||'';
 $('objects').innerHTML=all.map(o=>`<option value="${esc(o.id)}" ${o.id===selected?'selected':''}>${esc(o.id)} · ${esc(o.tipo)}</option>`).join('') || '<option>Sem objetos</option>';
 const o=currentObject();
 $('duplicate').disabled=$('delete').disabled=!o;
 $('spin').disabled=$('pulse').disabled=$('bounce').disabled=$('clearTracks').disabled=!o;
 const controls=$('inspector');
 if(!o){controls.innerHTML='<p class="hint">Crie um objeto para editar.</p>';} else {
  const field=(key,label,val,min,max)=>`<label>${label}<input data-edit="${key}" type="number" step="any" min="${min}" max="${max}" value="${val}"></label>`;
  const axes=(name,arr,lo,hi)=>`<div class="compact">${['X','Y','Z'].map((axis,i)=>field(`${name}.${i}`,`${name==='posicao'?'Posição':'Rotação'} ${axis}`,arr[i],lo,hi)).join('')}</div>`;
  const parentList=[['','Nenhum (raiz)'],...all.filter(x=>x.id!==o.id).map(x=>[x.id,x.id])];
  const parentSelect=`<label>Objeto-pai (hierarquia)<select data-edit="pai">${parentList.map(([id,label])=>`<option value="${esc(id)}" ${o.pai===id?'selected':''}>${esc(label)}</option>`).join('')}</select></label>`;
  controls.innerHTML=`<label>Cor <input data-edit="cor" type="color" value="${esc(o.cor)}"></label>`+parentSelect+axes('posicao',o.posicao,-20,20)+axes('rotacao',o.rotacao,-3600,3600)+field('escala','Escala',o.escala,.1,5);
 }
 const cam=spatial().camera;
 $('yaw').value=cam.azimute; $('pitch').value=cam.elevacao; $('distance').value=cam.distancia;
 const tracks=spatial().animacoes.filter(a=>a.alvo===selected);
 $('tracks').innerHTML=tracks.length ? tracks.map((a,i)=>`<div class="track"><b>${esc(a.propriedade)}</b> ${a.de} → ${a.ate} (${Math.round(a.inicio*100)}–${Math.round(a.fim*100)}%) <button data-remove-track="${i}" aria-label="Remover faixa">✕</button></div>`).join('') : '<p class="hint">Nenhuma faixa neste objeto.</p>';
 const cameraTracks=spatial().animacoes.filter(a=>a.alvo==='__camera__');
 $('cameraTracks').innerHTML=cameraTracks.length?cameraTracks.map(a=>`<div>◉ ${esc(a.propriedade)}: ${a.de} → ${a.ate}</div>`).join(''):'<span class="hint">Câmera estática</span>';
 $('clearCameraTracks').disabled=!cameraTracks.length;
 $('seek').value=Math.round(progress*1000);$('time').value=Math.round(progress*100)+'%';
}
async function preview(){
 const mark=++generation;
 if(!project)return;
 const c=clone(scene());const current=progress;
 try{
  const r=await fetch('/api/preview',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({scene:c,video:project.video,progress:current,index,total:project.cenas.length})});
  const svg=await r.text();if(mark!==generation)return;
  if(!r.ok)throw Error('Prévia '+r.status+': '+svg.slice(0,140));
  $('frame').innerHTML=svg;
  const root=$('frame').querySelector('svg');if(root){root.style.width='100%';root.style.height='100%';root.setAttribute('preserveAspectRatio','xMidYMid meet');}
 }catch(e){if(mark===generation)status(e.message);}
}
function clampValue(n,low,high){if(!Number.isFinite(n))throw Error('Valor numérico inválido');return Math.max(low,Math.min(high,n));}
function updateField(key,value){
 const o=currentObject();if(!o)return;
 if(key==='cor'){if(!/^#[0-9a-fA-F]{6}$/.test(value))throw Error('Cor inválida');o.cor=value;return;}
 if(key==='pai'){o.pai=value;return;}
 const num=Number(value);if(key==='escala'){o.escala=clampValue(num,.1,5);return;}
 const [field,axis]=key.split('.');if(!['posicao','rotacao'].includes(field)||!['0','1','2'].includes(axis))throw Error('Campo não autorizado');
 o[field][Number(axis)]=clampValue(num,field==='posicao'?-20:-3600,field==='posicao'?20:3600);
}
function applyOperations(raw){
 const ops=raw?.operacoes;if(!Array.isArray(ops)||ops.length>32)throw Error('Forneça uma lista operacoes de no máximo 32 comandos');
 const tmp=clone(spatial());
 for(const op of ops){
  if(!op||typeof op!=='object')throw Error('Comando inválido');
  if(op.op==='adicionar'){
   const id=op.id||'novo_'+(tmp.objetos.length+1);
   if(!/^[a-zA-Z_][a-zA-Z0-9_-]{0,39}$/.test(id)||tmp.objetos.some(o=>o.id===id))throw Error('ID inválido ou duplicado: '+id);
   tmp.objetos.push({id,tipo:op.tipo||'cubo',posicao:op.posicao||[0,0,0],rotacao:op.rotacao||[0,0,0],escala:op.escala??1,cor:op.cor||'#67bfe9',pai:op.pai||'',visivel:true});
  }else if(op.op==='alterar'){
   const obj=tmp.objetos.find(o=>o.id===op.alvo);if(!obj)throw Error('Objeto desconhecido: '+op.alvo);
   if(!['cor','posicao','rotacao','escala','visivel','pai'].includes(op.campo))throw Error('Campo não autorizado');
   obj[op.campo]=op.valor;
  }else if(op.op==='excluir'){
   if(!tmp.objetos.some(o=>o.id===op.alvo))throw Error('Objeto desconhecido');
   tmp.objetos=tmp.objetos.filter(o=>o.id!==op.alvo);
   tmp.objetos.forEach(o=>{if(o.pai===op.alvo)o.pai='';});
   tmp.animacoes=tmp.animacoes.filter(a=>a.alvo!==op.alvo);
  }else if(op.op==='animar'){
   tmp.animacoes.push({alvo:op.alvo,propriedade:op.propriedade,inicio:op.inicio??0,fim:op.fim??1,de:op.de??0,ate:op.ate??360,easing:op.easing||'suave'});
  }else throw Error('Operação desconhecida: '+op.op);
 }
 return tmp;
}
async function validate(candidate){
 const copy=clone(project);copy.cenas[index].espacial=candidate;
 return (await post('/api/project/validate',{project:copy})).project;
}
async function save(){
 try {
  const normalized=await validate(spatial());
  // Do not silently overwrite changes saved from another tab.
  const server=(await request('/api/project?name='+encodeURIComponent(name))).project;
  if(JSON.stringify(server)!==baseline)throw Error('Projeto alterado em outra aba. Recarregue antes de salvar.');
  await post('/api/project',{name,project:normalized});
  project=normalized;baseline=JSON.stringify(normalized);history=[];status('Projeto salvo');renderControls();
 }catch(e){status('Não salvo: '+e.message);}
}
function tick(now){
 if(!playing)return;
 if(lastTime){progress+=(now-lastTime)/1000/Math.max(.5,scene().duracao);}
 lastTime=now;if(progress>=1){progress=1;playing=false;$('play').textContent='▶';}
 if(now-lastDraw>130){lastDraw=now;$('seek').value=Math.round(progress*1000);$('time').value=Math.round(progress*100)+'%';preview();}
 if(playing)requestAnimationFrame(tick);
}
async function init(){
 try {
  const result=await request('/api/project?name='+encodeURIComponent(name));project=result.project;baseline=JSON.stringify(project);
  if(!scene()||scene().tipo!=='espacial')throw Error('A cena selecionada não é espacial. Crie uma usando + 3D.');
  $('sceneTitle').textContent=scene().titulo||'Cena espacial';
  $('back').href='/?v=3.0.0-alpha.1';renderControls();status('Cena carregada');preview();
 }catch(e){status(e.message);}
}
$('objects').onchange=e=>{selected=e.target.value;renderControls();};
document.querySelectorAll('[data-create]').forEach(b=>b.onclick=()=>{
 remember();let id=unique('obj_');spatial().objetos.push({id,tipo:b.dataset.create,posicao:[0,0,0],rotacao:[0,0,0],escala:1,cor:'#67bfe9',pai:'',visivel:true});selected=id;changed();
});
$('duplicate').onclick=()=>{const o=currentObject();if(!o)return;remember();const copy=clone(o);copy.id=unique('obj_');copy.posicao[0]+=1;spatial().objetos.push(copy);selected=copy.id;changed();};
$('delete').onclick=()=>{const o=currentObject();if(!o)return;remember();spatial().objetos=spatial().objetos.filter(x=>x.id!==o.id);spatial().objetos.forEach(x=>{if(x.pai===o.id)x.pai='';});spatial().animacoes=spatial().animacoes.filter(a=>a.alvo!==o.id);selected='';changed();};
$('inspector').onchange=async e=>{if(!e.target.dataset.edit)return;const before=clone(spatial());try{
  updateField(e.target.dataset.edit,e.target.value);
  await validate(spatial());history.push(before);changed();
 }catch(x){scene().espacial=before;renderControls();status(x.message);}};
for(const [id,field,lo,hi] of [['yaw','azimute',-360,360],['pitch','elevacao',-80,80],['distance','distancia',3,40]]){
 $(id).onchange=e=>{try{const n=clampValue(Number(e.target.value),lo,hi);remember();spatial().camera[field]=n;changed();}catch(x){status(x.message);}};
}
$('orbit').onclick=()=>{remember();const start=spatial().camera.azimute;spatial().animacoes.push({alvo:'__camera__',propriedade:'azimute',inicio:0,fim:1,de:start,ate:start+360,easing:'linear'});changed();};
$('clearCameraTracks').onclick=()=>{remember();spatial().animacoes=spatial().animacoes.filter(a=>a.alvo!=='__camera__');changed();};
$('spin').onclick=()=>{if(!selected)return;remember();spatial().animacoes.push({alvo:selected,propriedade:'rotacao_y',inicio:0,fim:1,de:0,ate:360,easing:'linear'});changed();};
$('pulse').onclick=()=>{if(!selected)return;remember();spatial().animacoes.push({alvo:selected,propriedade:'escala',inicio:0,fim:1,de:.75,ate:1.25,easing:'sine.inOut',repeticoes:3,yoyo:true});changed();};
$('bounce').onclick=()=>{if(!selected)return;remember();const o=currentObject();spatial().animacoes.push({alvo:selected,propriedade:'posicao_y',inicio:0,fim:1,de:o.posicao[1]+2,ate:o.posicao[1],easing:'bounce.out'});changed();};
$('clearTracks').onclick=()=>{remember();spatial().animacoes=spatial().animacoes.filter(a=>a.alvo!==selected);changed();};
$('tracks').onclick=e=>{if(!e.target.dataset.removeTrack)return;const indices=spatial().animacoes.map((a,i)=>a.alvo===selected?i:-1).filter(i=>i>=0);remember();spatial().animacoes.splice(indices[Number(e.target.dataset.removeTrack)],1);changed();};
$('seek').oninput=e=>{playing=false;$('play').textContent='▶';progress=Number(e.target.value)/1000;$('time').value=Math.round(progress*100)+'%';preview();};
$('play').onclick=()=>{playing=!playing;$('play').textContent=playing?'Ⅱ':'▶';if(playing){if(progress>=1)progress=0;lastTime=0;requestAnimationFrame(tick);}};
$('apply').onclick=async()=>{try{const proposal=applyOperations(JSON.parse($('commands').value));const norm=await validate(proposal);remember();scene().espacial=norm.cenas[index].espacial;changed();status('Comandos validados e aplicados em memória. Use Salvar.');}catch(e){status('Comandos rejeitados: '+e.message);}};
$('undo').onclick=()=>{if(!history.length)return;scene().espacial=history.pop();changed();};
$('save').onclick=save;
window.addEventListener('beforeunload', e=>{if(project&&JSON.stringify(project)!==baseline){e.preventDefault();e.returnValue='';}});
init();
})();
