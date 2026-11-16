// Semantic edition plans. No DOM, renderer, or persistent I/O.
// DocumentService remains the only owner of validation and history.
const requireThat=(ok,msg)=>{if(!ok)throw Error(msg);};
const idOK=id=>typeof id==='string'&&/^[A-Za-z][A-Za-z0-9_.-]{0,63}$/.test(id)&&!['constructor','prototype','__proto__'].includes(id);
const record=o=>o&&Object.getPrototypeOf(o)===Object.prototype;
export const EDIT_OPERATIONS=Object.freeze(['create','set-many','reparent','duplicate','remove','track-put','track-remove','cue-put','cue-remove']);
export function planEdit(doc,cmd){
 requireThat(record(cmd)&&EDIT_OPERATIONS.includes(cmd.op),'Operação de autoria desconhecida');
 const s=structuredClone(doc.spec), objects=new Map(s.objects.map(o=>[o.id,o])), nodes=new Map(doc.nodes.map(o=>[o.id,o]));
 const get=id=>{requireThat(objects.has(id),'Objeto inexistente: '+id);return objects.get(id);};
 const unique=id=>{requireThat(idOK(id)&&!objects.has(id),'ID inválido ou já existente: '+id);return id;};
 const parent=id=>{if(id!==null)get(id);return id;};
 const subtree=id=>{get(id);const ids=new Set([id]);let changed=true;while(changed){changed=false;for(const o of s.objects)if(ids.has(o.parent)&&!ids.has(o.id)){ids.add(o.id);changed=true;}}return ids;};
 const selection=ids=>{requireThat(Array.isArray(ids)&&ids.length>0&&ids.length<=512,'Seleção vazia ou inválida');return [...new Set(ids)].map(get);};
 switch(cmd.op){
 case 'create':{
  const id=unique(cmd.id), p=parent(cmd.parent??null);let resource=cmd.resource;
  if(record(resource)){requireThat(idOK(resource.id)&&!s.resources.some(r=>r.id===resource.id),'Recurso inválido ou já existente');s.resources.push({id:resource.id,kind:resource.kind,props:resource.props??{}});resource=resource.id;}
  requireThat(s.resources.some(r=>r.id===resource),'Recurso inexistente');s.objects.push({id,resource,parent:p,props:cmd.props??{}});break;}
 case 'set-many':{
  requireThat(idOK(cmd.property),'Propriedade inválida');for(const o of selection(cmd.ids)){requireThat(Object.hasOwn(nodes.get(o.id).props,cmd.property),'Propriedade não disponível: '+o.id);o.props[cmd.property]=doc.registry.require(cmd.property).normalize(cmd.value);}break;}
 case 'reparent':{const o=get(cmd.id);o.parent=parent(cmd.parent??null);break;} // local transform is preserved; validation rejects cycles
 case 'duplicate':{
  const ids=subtree(cmd.id), prefix=unique(cmd.newId), mapping=new Map();let index=0;
  for(const id of ids){const next=id===cmd.id?prefix:`${prefix}_${++index}`;unique(next);requireThat(![...mapping.values()].includes(next),'ID duplicado');mapping.set(id,next);}
  for(const o of [...s.objects])if(ids.has(o.id))s.objects.push({...structuredClone(o),id:mapping.get(o.id),parent:mapping.get(o.parent)??o.parent});
  for(const a of [...s.tracks])if(ids.has(a.target))s.tracks.push({...structuredClone(a),target:mapping.get(a.target)});
  for(const c of [...s.cues])if(ids.has(c.target))s.cues.push({...structuredClone(c),target:mapping.get(c.target)});break;}
 case 'remove':{
  const ids=new Set(selection(cmd.ids).flatMap(o=>[...subtree(o.id)]));requireThat(!ids.has(s.stage.camera),'A câmera ativa não pode ser excluída');s.objects=s.objects.filter(o=>!ids.has(o.id));s.tracks=s.tracks.filter(a=>!ids.has(a.target));s.cues=s.cues.filter(c=>!ids.has(c.target));break;}
 case 'track-put':{get(cmd.id);requireThat(record(cmd.animation),'Animação inválida');const a={target:cmd.id,property:cmd.property,animation:cmd.animation},i=s.tracks.findIndex(t=>t.target===a.target&&t.property===a.property);if(i<0)s.tracks.push(a);else s.tracks[i]=a;break;}
 case 'track-remove':{get(cmd.id);const i=s.tracks.findIndex(t=>t.target===cmd.id&&t.property===cmd.property);requireThat(i>=0,'Faixa inexistente');s.tracks.splice(i,1);break;}
 case 'cue-put':{get(cmd.id);requireThat(record(cmd.timing),'Cue inválido');const c={target:cmd.id,timing:cmd.timing};if(cmd.index===undefined)s.cues.push(c);else{requireThat(Number.isInteger(cmd.index)&&s.cues[cmd.index]?.target===cmd.id,'Cue inexistente');s.cues[cmd.index]=c;}break;}
 case 'cue-remove':{requireThat(Number.isInteger(cmd.index)&&s.cues[cmd.index]?.target===cmd.id,'Cue inexistente');s.cues.splice(cmd.index,1);break;}
 }
 return s;
}
