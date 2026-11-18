// RD Studio 0.4 — declarative project operations, transactionally simulated.
// Original code for Rogério Duarte. No eval/network/filesystem. Reuses 0.3 scene operations.
import {previewScenePlan} from './roteiro-plan-v03.mjs';
const object=x=>x&&typeof x==='object'&&!Array.isArray(x);
const fail=s=>{throw Error(s);};
const exact=(o,keys)=>{if(!object(o)||Object.keys(o).some(k=>!keys.includes(k)))fail('Campos desconhecidos na operação');};
const id=s=>typeof s==='string'&&/^[A-Za-z0-9_-]{1,64}$/.test(s)?s:fail('ID inválido');
const txt=(s,max)=>typeof s==='string'&&s.length<=max?s:fail('Texto inválido ou longo demais');
const num=(x,a,b)=>typeof x==='number'&&Number.isFinite(x)&&x>=a&&x<=b?x:fail(`Número fora de ${a}–${b}`);
const get=(p,k)=>p.cenas.find(s=>s.id===id(k))||fail('Cena inexistente: '+k);
const getObj=(s,k)=>s.objetos_midia?.find(o=>o.id===id(k))||fail('Objeto inexistente: '+k);
const maxScenes=150,maxOps=100;
export function validateProjectPlan(raw){
 const p=typeof raw==='string'?JSON.parse(raw):raw;
 exact(p,['format','expect','operations']);
 if(p.format!=='rd-studio-project-plan-0.4'||!Array.isArray(p.operations)||p.operations.length>maxOps)fail('Formato 0.4 inválido ou mais de 100 operações');
 if(p.expect!==undefined){exact(p.expect,['title','scene_ids']);if(p.expect.title!==undefined)txt(p.expect.title,180);if(p.expect.scene_ids!==undefined&&(!Array.isArray(p.expect.scene_ids)||p.expect.scene_ids.some(x=>typeof x!=='string')))fail('expect.scene_ids inválido');}
 return p;
}
export function previewProjectPlan(project,raw,{validateMotion=()=>{}}={}){
 const plan=validateProjectPlan(raw);
 if(!object(project)||!Array.isArray(project.cenas)||project.cenas.length<1)fail('Documento inválido');
 if(plan.expect?.title!==undefined&&project.titulo!==plan.expect.title)fail('Projeto foi alterado: título inesperado');
 if(plan.expect?.scene_ids!==undefined&&JSON.stringify(project.cenas.map(s=>s.id))!==JSON.stringify(plan.expect.scene_ids))fail('Projeto foi alterado: cenas divergentes');
 const copy=structuredClone(project),changes=[];
 for(const [ix,p] of plan.operations.entries()){
  try{
   if(!object(p))fail('Operação não é objeto');
   if(p.type==='scene.clone'){
    exact(p,['type','source','id','after']);const source=get(copy,p.source);id(p.id);
    if(copy.cenas.some(s=>s.id===p.id)||copy.cenas.length>=maxScenes)fail('ID duplicado ou limite de cenas');
    const cloned=structuredClone(source);cloned.id=p.id;const pos=p.after===undefined?copy.cenas.indexOf(source):copy.cenas.indexOf(get(copy,p.after));copy.cenas.splice(pos+1,0,cloned);
   } else if(p.type==='scene.move'){
    exact(p,['type','id','after']);const s=get(copy,p.id);copy.cenas.splice(copy.cenas.indexOf(s),1);
    const idx=p.after===null?-1:copy.cenas.indexOf(get(copy,p.after));copy.cenas.splice(idx+1,0,s);
   } else if(p.type==='scene.duration'){
    exact(p,['type','id','seconds']);get(copy,p.id).duracao=num(p.seconds,.5,600);
   } else if(p.type==='scene.text'){
    exact(p,['type','id','field','text']);if(!['titulo','subtitulo','fala'].includes(p.field))fail('Campo de texto não autorizado');
    const s=get(copy,p.id),text=txt(p.text,p.field==='fala'?4000:p.field==='titulo'?250:400);s[p.field]=text;
    if(p.field==='fala'){s.audio??={};s.audio.voice_text=text;}
   } else if(p.type==='scene.voice'){
    exact(p,['type','id','enabled','volume']);const s=get(copy,p.id);s.audio??={};
    if(typeof p.enabled!=='boolean')fail('enabled deve ser booleano');s.audio.voice_enabled=p.enabled;
    s.audio.muted=!p.enabled;s.audio.voice_volume=num(p.volume,0,3);
   } else if(p.type==='object.clone'){
    exact(p,['type','scene_id','source','id']);const s=get(copy,p.scene_id),o=getObj(s,p.source);id(p.id);
    if((s.objetos_midia||[]).some(a=>a.id===p.id)||(s.objetos_midia||[]).length>=16)fail('ID duplicado ou limite de 16 objetos');
    s.objetos_midia.push({...structuredClone(o),id:p.id});
   } else if(p.type==='object.remove'){
    exact(p,['type','scene_id','id']);const s=get(copy,p.scene_id),o=getObj(s,p.id);
    s.objetos_midia.splice(s.objetos_midia.indexOf(o),1);
   } else if(p.type==='object.position'){
    exact(p,['type','scene_id','id','x','y','w','h','rotation','opacity']);const o=getObj(get(copy,p.scene_id),p.id);
    for(const [k,a,b] of [['x',-2,3],['y',-2,3],['w',.02,2],['h',.02,2],['rotation',-360,360],['opacity',0,1]])if(k in p)o[k]=num(p[k],a,b);
    if(!['x','y','w','h','rotation','opacity'].some(k=>k in p))fail('Informe ao menos uma propriedade');
   } else if(p.type==='object.appearance'){
    exact(p,['type','scene_id','id','corner_radius','border_width','shadow_blur','border_color','shadow_color']);const o=getObj(get(copy,p.scene_id),p.id);
    for(const [k,a,b] of [['corner_radius',0,.5],['border_width',0,20],['shadow_blur',0,60]])if(k in p)o[k]=num(p[k],a,b);
    for(const k of ['border_color','shadow_color'])if(k in p){if(typeof p[k]!=='string'||!/^#[\da-fA-F]{6}$/.test(p[k]))fail('Cor inválida');o[k]=p[k];}
   } else if(p.type==='scene.edit03'){
    exact(p,['type','scene_id','operations']);const s=get(copy,p.scene_id);
    const result=previewScenePlan(s,{format:'rd-studio-plan-0.3',operations:p.operations},{validateMotion});
    Object.assign(s,result.scene);
   } else fail('Operação desconhecida: '+p.type);
   changes.push({index:ix+1,type:p.type,id:p.id||p.scene_id||null});
  }catch(e){throw Error('Operação '+(ix+1)+' ('+String(p.type||'?')+'): '+e.message);}
 }
 return {project:copy,changes};
}
