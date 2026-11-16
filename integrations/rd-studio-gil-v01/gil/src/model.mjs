import {PropertyRegistry, RuntimeCapabilities, createOccurrenceRef, childOccurrenceRef, compileAffineExpression, evaluateCompiledAffineExpression, compileAffineProgram, evaluateAffineProgram, createAffineEvaluationContext, composeTransform, eulerQuaternion, multiplyMatrices, invertAffineMatrix, identityMatrix} from './spatialseed.mjs';
import {parse,serialize,LANGUAGE} from './language.mjs';
const BASE=Object.freeze({x:0,y:0,z:0,rx:0,ry:0,rz:0,sx:1,sy:1,sz:1,opacity:1,layer:0});
const ID=/^[A-Za-z][A-Za-z0-9_.-]{0,63}$/;
const plain=x=>x!==null&&typeof x==='object'&&!Array.isArray(x)&&Object.getPrototypeOf(x)===Object.prototype;
const ensure=(ok,msg)=>{if(!ok)throw Error(msg);};
const validId=x=>typeof x==='string'&&ID.test(x)&&!['constructor','prototype','__proto__'].includes(x);
const number=x=>typeof x==='number'&&Number.isFinite(x)&&Math.abs(x)<=1e7;
const hex=x=>typeof x==='string'&&/^#[0-9a-f]{6}$/i.test(x);
const normal=(k,v,type)=>{ensure(typeof v===type && (type==='number'?number(v):type==='string'?v.length<=2048:type==='boolean'),`Valor inválido: ${k}`);if(k==='opacity')ensure(v>=0&&v<=1,'opacity: 0..1');if(['sx','sy','sz'].includes(k))ensure(v>0&&v<=1000,`${k}: escala positiva`);return v;};
function mapUnique(arr, label){const m=new Map();for(const x of arr){ensure(plain(x)&&validId(x.id)&&!m.has(x.id),`${label}: ID inválido ou duplicado`);m.set(x.id,x);}return m;}
function deepFreeze(x){if(x&&typeof x==='object'&&!Object.isFrozen(x)){for(const v of Object.values(x))deepFreeze(v);Object.freeze(x);}return x;}
export function compile(sourceOrSpec){
 const spec=typeof sourceOrSpec==='string'?parse(sourceOrSpec):structuredClone(sourceOrSpec);
 ensure(plain(spec)&&spec.version===LANGUAGE,'Versão inválida');
 const st=spec.stage;ensure(plain(st)&&Number.isInteger(st.width)&&Number.isInteger(st.height)&&st.width>=160&&st.width<=3840&&st.height>=160&&st.height<=3840&&number(st.duration)&&st.duration>0&&st.duration<=600&&hex(st.background)&&validId(st.camera),'stage inválido');
 for(const [k,max] of [['resources',128],['objects',512],['tracks',1024],['cues',128]])ensure(Array.isArray(spec[k])&&spec[k].length<=max,`${k}: lista inválida`);
 const resources=mapUnique(spec.resources,'resource'), byId=mapUnique(spec.objects,'object'), types=new Map(Object.entries(BASE).map(([k,v])=>[k,typeof v]));
 for(const r of resources.values()){
  ensure(validId(r.kind)&&plain(r.props),'resource inválido');
  for(const [k,v] of Object.entries(r.props)){ensure(validId(k),`Propriedade inválida: ${k}`);const type=typeof v;normal(k,v,type);ensure(!types.has(k)||types.get(k)===type,`Tipos incompatíveis: ${k}`);types.set(k,type);}
 }
 const registry=new PropertyRegistry();for(const [k,type] of types)registry.register({id:k,valueType:type,read:o=>o.props[k],normalize:v=>normal(k,v,type),supports:o=>Object.hasOwn(o.props,k),editableMany:true,procedural:type==='number'});
 const resolved=new Map(), visiting=new Set();
 function resolve(id,depth=0){if(resolved.has(id))return resolved.get(id);ensure(depth<=64&&!visiting.has(id),`Ciclo ou hierarquia profunda: ${id}`);const o=byId.get(id);ensure(o,`Objeto inexistente: ${id}`);const r=resources.get(o.resource);ensure(r&&plain(o.props),`Objeto sem recurso válido: ${id}`);visiting.add(id);const p=o.parent===null?null:resolve(o.parent,depth+1);const props={...BASE,...r.props};for(const [k,v] of Object.entries(o.props)){ensure(Object.hasOwn(props,k),`${id}: propriedade não declarada ${k}`);props[k]=registry.require(k).normalize(v);}const occurrence=p?childOccurrenceRef(p.occurrence,id):createOccurrenceRef({rootInstanceId:id});const n=deepFreeze({id,kind:r.kind,resource:r.id,parent:o.parent,occurrence,props});resolved.set(id,n);visiting.delete(id);return n;}
 const nodes=spec.objects.map(o=>resolve(o.id));ensure(resolved.get(st.camera)?.kind==='camera','Câmera do stage inválida');
 const trackKeys=new Set();
 const tracks=spec.tracks.map((a,i)=>{
  const o=resolved.get(a.target), k=a.property, v=a.animation;ensure(o&&Object.hasOwn(o.props,k)&&typeof o.props[k]==='number'&&plain(v),`Faixa ${i}: alvo não numérico`);let key=a.target+'\0'+k;ensure(!trackKeys.has(key),`Faixa duplicada: ${a.target}.${k}`);trackKeys.add(key);
  const start=v.start??0,end=v.end??st.duration;ensure(number(start)&&number(end)&&start>=0&&end>start&&end<=st.duration,'Intervalo inválido');
  if(typeof v.expr==='string') {ensure(v.expr.length<=512,'Expressão excessiva');const expr=compileAffineExpression(v.expr);const context={t:start,u:0,i:nodes.indexOf(o)+1,count:nodes.length,v:o.props[k]};registry.require(k).normalize(evaluateCompiledAffineExpression(expr,context));return deepFreeze({target:a.target,property:k,start,end,expr});}
  const keys=v.keys;ensure(Array.isArray(keys)&&keys.length>=2&&keys.length<=100&&['linear','smooth'].includes(v.ease??'linear'),'Keyframes inválidos');let prev=-1;
  for(const pair of keys){ensure(Array.isArray(pair)&&pair.length===2&&number(pair[0])&&pair[0]>=start&&pair[0]<=end&&pair[0]>prev,'Tempo de keyframe inválido');registry.require(k).normalize(pair[1]);prev=pair[0];}
  return deepFreeze({target:a.target,property:k,start,end,keys,ease:v.ease??'linear'});
 });
 const cues=spec.cues.map(c=>{const n=resolved.get(c.target),v=c.timing;ensure(n?.kind==='audio.tone'&&plain(v)&&number(v.start)&&number(v.duration)&&v.start>=0&&v.duration>0&&v.start+v.duration<=st.duration,'Cue de áudio inválido');return deepFreeze({target:c.target,start:v.start,duration:v.duration});});
 const capabilities=new RuntimeCapabilities();capabilities.register('gil.language',{version:LANGUAGE,math:'spatialseed-math-v1',commands:['set','move','undo','redo'],resourceKinds:[...new Set(nodes.map(n=>n.kind))]});capabilities.register('gil.properties',()=>registry.describe());
 return Object.freeze({spec:deepFreeze(spec),nodes:Object.freeze(nodes),tracks:Object.freeze(tracks),cues:Object.freeze(cues),registry,capabilities});
}
// Autoridade editorial do laboratório: todos os caminhos passam por compile, commit único.
export class DocumentService{
 #doc;#undo=[];#redo=[];#revision=0;
 constructor(input){this.#doc=compile(input);}
 get document(){return this.#doc;}get revision(){return this.#revision;}get source(){return serialize(this.#doc.spec);}
 replace(input){const next=compile(input);this.#undo.push(this.#doc);if(this.#undo.length>50)this.#undo.shift();this.#doc=next;this.#redo=[];this.#revision++;return next;}
 set(id,property,value){const o=this.#doc.nodes.find(n=>n.id===id);ensure(o&&Object.hasOwn(o.props,property),'Alvo/propriedade inexistente');const spec=structuredClone(this.#doc.spec);spec.objects.find(n=>n.id===id).props[property]=this.#doc.registry.require(property).normalize(value);return this.replace(spec);}
 move(id,vector){const o=this.#doc.nodes.find(n=>n.id===id);ensure(o&&Array.isArray(vector)&&vector.length===3&&vector.every(v=>number(v)||(typeof v==='string'&&v.length<=512)),'move exige 3 componentes');const program=compileAffineProgram([{type:'move',value:vector}],{translationSpace:'local'});const [{value}]=evaluateAffineProgram(program,createAffineEvaluationContext({}));const spec=structuredClone(this.#doc.spec);const p=spec.objects.find(n=>n.id===id).props;for(let i=0;i<3;i++)p['xyz'[i]]=o.props['xyz'[i]]+value[i];return this.replace(spec);}
 // Compatibilidade semântica com selection.translate: deslocamento mundial
 // da seleção única no documento-base; não usa a pose efêmera da prévia.
 moveWorld(id,delta){const doc=this.#doc,o=doc.nodes.find(n=>n.id===id);ensure(o&&Array.isArray(delta)&&delta.length===3&&delta.every(number),'move: vetor mundial inválido');const byId=new Map(doc.nodes.map(n=>[n.id,n]));function matrix(id){if(!id)return identityMatrix();const n=byId.get(id),p=n.props;return multiplyMatrices(matrix(n.parent),composeTransform({position:[p.x,p.y,p.z],rotation:eulerQuaternion([p.rx,p.ry,p.rz]),scale:[p.sx,p.sy,p.sz]}));}const inv=invertAffineMatrix(matrix(o.parent));const local=[0,1,2].map(row=>inv[row]*delta[0]+inv[4+row]*delta[1]+inv[8+row]*delta[2]);return this.move(id,local);}
 undo(){if(!this.#undo.length)return false;this.#redo.push(this.#doc);this.#doc=this.#undo.pop();this.#revision++;return true;}
 redo(){if(!this.#redo.length)return false;this.#undo.push(this.#doc);this.#doc=this.#redo.pop();this.#revision++;return true;}
 execute(line){let m;if(line==='undo')return this.undo();if(line==='redo')return this.redo();if((m=/^set\s+(\S+)\s+(\S+)\s+(.+)$/.exec(line)))return this.set(m[1],m[2],JSON.parse(m[3]));if((m=/^move\s+(\S+)\s+(.+)$/.exec(line)))return this.move(m[1],JSON.parse(m[2]));throw Error('Comandos: set ID PROPRIEDADE JSON | move ID [dx,dy,dz] | undo | redo');}
}
