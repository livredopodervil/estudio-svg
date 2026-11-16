// UI adapter: commands are shared with the console; no document mutation here.
const $=id=>document.getElementById(id);
const el=(tag,text)=>{const e=document.createElement(tag);if(text!==undefined)e.textContent=text;return e;};
const opt=(id,text=id)=>{const e=el('option',text);e.value=id;return e;};
export function createAuthoringUI({getDocument,getSelected,select,edit,getTime,report}){
 let chosen=new Set(),active=null;
 const guard=fn=>()=>{try{fn();}catch(e){report(e.message);}};
 const apply=cmd=>edit(cmd);
 const ids=()=>chosen.size?[...chosen]:[getSelected()];
 const writeTrack=()=>{const property=$('au-prop').value;if(!property)throw Error('Selecione propriedade numérica');apply({op:'track-put',id:getSelected(),property,animation:JSON.parse($('au-track').value)});};
 function updateDetails(){const d=getDocument(),id=getSelected(),n=d.nodes.find(o=>o.id===id);if(!n)return;active=id;
  const previous=$('au-prop').value;$('au-prop').replaceChildren(...Object.entries(n.props).filter(([,v])=>typeof v==='number').map(([k])=>opt(k)));if([...$('au-prop').options].some(o=>o.value===previous))$('au-prop').value=previous;
  $('au-parent').replaceChildren(opt('','Raiz'),...d.nodes.filter(o=>o.id!==id).map(o=>opt(o.id)));$('au-parent').value=n.parent??'';
  $('au-cues').replaceChildren(opt('','Novo efeito'),...d.spec.cues.flatMap((c,i)=>c.target===id?[opt(String(i),`${c.timing.start}s · ${c.timing.duration}s`)]:[]));
  $('au-cue-panel').hidden=n.kind!=='audio.tone';$('au-cue-start').value=Number(getTime().toFixed(3));$('au-cue-duration').value=.2;
  loadTrack();
 }
 function loadTrack(){const d=getDocument(),n=d.nodes.find(o=>o.id===getSelected()),k=$('au-prop').value;if(!n||!k)return;const a=d.spec.tracks.find(t=>t.target===n.id&&t.property===k);$('au-track').value=JSON.stringify(a?.animation??{keys:[[0,n.props[k]],[d.spec.stage.duration,n.props[k]]],ease:'smooth'},null,2);}
 function refresh(){const d=getDocument(),id=getSelected();chosen=new Set([...chosen].filter(x=>d.nodes.some(n=>n.id===x)));const tree=$('au-tree');tree.replaceChildren();const byParent=new Map();for(const n of d.nodes){if(!byParent.has(n.parent))byParent.set(n.parent,[]);byParent.get(n.parent).push(n);}const query=$('au-filter').value.toLowerCase().trim();
  function walk(parent,depth){for(const n of byParent.get(parent)??[]){if(!query||`${n.id} ${n.kind} ${n.resource}`.toLowerCase().includes(query)){const row=el('div');row.className='au-node';row.style.paddingLeft=Math.min(depth,10)*12+'px';const check=el('input');check.type='checkbox';check.checked=chosen.has(n.id);check.setAttribute('aria-label','Selecionar para lote '+n.id);check.onchange=()=>{if(check.checked)chosen.add(n.id);else chosen.delete(n.id);count();};const b=el('button',`${n.id} · ${n.kind}`);b.type='button';b.title=n.id;b.setAttribute('aria-pressed',String(n.id===id));b.onclick=()=>select(n.id);row.append(check,b);tree.append(row);}walk(n.id,depth+1);}}
  walk(null,0);count();const r=$('au-resource'),old=r.value;r.replaceChildren(...d.spec.resources.map(x=>opt(x.id,`${x.id} · ${x.kind}`)));if(d.spec.resources.some(x=>x.id===old))r.value=old;updateDetails();
 }
 const count=()=>{$('au-count').textContent=`${chosen.size} em lote (0 = objeto ativo)`;};
 $('au-filter').oninput=refresh;$('au-clear').onclick=()=>{chosen.clear();refresh();};$('au-all-type').onclick=()=>{const d=getDocument(),n=d.nodes.find(x=>x.id===getSelected());chosen=new Set(d.nodes.filter(x=>x.kind===n?.kind).map(x=>x.id));refresh();};
 $('au-prop').onchange=loadTrack;$('au-track-save').onclick=guard(writeTrack);$('au-track-remove').onclick=guard(()=>apply({op:'track-remove',id:getSelected(),property:$('au-prop').value}));
 $('au-key').onclick=guard(()=>{const a=JSON.parse($('au-track').value);if(a.expr)throw Error('A faixa é uma expressão; troque para keyframes explicitamente.');const t=Number(getTime().toFixed(3)),v=Number($('au-key-value').value);if($('au-key-value').value.trim()===''||!Number.isFinite(v))throw Error('Valor numérico necessário');a.keys=[...(a.keys??[]).filter(([x])=>x!==t),[t,v]].sort((x,y)=>x[0]-y[0]);$('au-track').value=JSON.stringify(a,null,2);writeTrack();});
 $('au-create').onclick=guard(()=>{const id=$('au-id').value.trim();let resource=$('au-resource').value;if($('au-new-kind').value.trim())resource={id:$('au-new-resource').value.trim(),kind:$('au-new-kind').value.trim(),props:JSON.parse($('au-defaults').value)};apply({op:'create',id,resource,parent:$('au-child').checked?getSelected():null,props:{}});select(id);});
 $('au-duplicate').onclick=guard(()=>{const id=$('au-id').value.trim();apply({op:'duplicate',id:getSelected(),newId:id});select(id);});
 $('au-reparent').onclick=guard(()=>apply({op:'reparent',id:getSelected(),parent:$('au-parent').value||null}));
 $('au-remove').onclick=guard(()=>{const target=ids();if(confirm(`Excluir ${target.length} seleção(ões), descendentes e suas faixas/cues? Arquivos de mídia não serão apagados.`))apply({op:'remove',ids:target});});
 $('au-many').onclick=guard(()=>apply({op:'set-many',ids:ids(),property:$('au-many-prop').value.trim(),value:JSON.parse($('au-many-value').value)}));
 for(const [id,dir] of [['au-front',1],['au-back',-1]])$(id).onclick=guard(()=>{const d=getDocument();const value=(dir>0?Math.max(...d.nodes.map(n=>n.props.layer)):Math.min(...d.nodes.map(n=>n.props.layer)))+dir;apply({op:'set-many',ids:ids(),property:'layer',value});});
 $('au-cues').onchange=()=>{const c=getDocument().spec.cues[Number($('au-cues').value)];if($('au-cues').value!==''&&c){$('au-cue-start').value=c.timing.start;$('au-cue-duration').value=c.timing.duration;}};
 $('au-cue-save').onclick=guard(()=>{const cmd={op:'cue-put',id:getSelected(),timing:{start:Number($('au-cue-start').value),duration:Number($('au-cue-duration').value)}};if($('au-cues').value!=='')cmd.index=Number($('au-cues').value);apply(cmd);});
 $('au-cue-remove').onclick=guard(()=>{if($('au-cues').value==='')throw Error('Selecione um efeito');apply({op:'cue-remove',id:getSelected(),index:Number($('au-cues').value)});});
 return {refresh,selectTrack(target,property){select(target);$('au-prop').value=property;loadTrack();},selectCue(target,index){select(target);$('au-cues').value=String(index);$('au-cues').onchange();}};
}
