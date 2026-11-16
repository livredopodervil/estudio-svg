import {TemporalRuntime, AnalyticTimeDomains, evaluateCompiledAffineExpression, composeTransform,eulerQuaternion,multiplyMatrices,identityMatrix} from './spatialseed.mjs';
const clamp=(v,a,b)=>Math.max(a,Math.min(b,v));
export class Timeline {
 #doc;#runtime;#cache=null;
 constructor(doc){this.#doc=doc;this.#runtime=new TemporalRuntime({domains:new AnalyticTimeDomains({nowSeconds:()=>0})});
  const nodes=new Map(doc.nodes.map((o,i)=>[o.id,{o,i:i+1}]));
  for(const [i,tr] of doc.tracks.entries())this.#runtime.register({id:'track-'+i,targetId:tr.target,phase:'animation',evaluate:({t,result})=>{const {o,i}=nodes.get(tr.target);let v=o.props[tr.property];if(t>=tr.start){const s=clamp(t,tr.start,tr.end),u=(s-tr.start)/(tr.end-tr.start);if(tr.expr)v=evaluateCompiledAffineExpression(tr.expr,{t:s,u,i,count:doc.nodes.length,v});else {const keys=tr.keys;if(s<=keys[0][0])v=keys[0][1];else if(s>=keys.at(-1)[0])v=keys.at(-1)[1];else{const j=keys.findIndex(k=>k[0]>=s),[a,x]=keys[j-1],[b,y]=keys[j];let f=(s-a)/(b-a);if(tr.ease==='smooth')f=f*f*(3-2*f);v=x+(y-x)*f;}}}v=doc.registry.require(tr.property).normalize(v);return result.changed([{id:tr.target,property:tr.property,value:v}]);}});
 }
 sample(seconds){if(typeof seconds!=='number'||!Number.isFinite(seconds))throw Error('Tempo inválido');const time=clamp(seconds,0,this.#doc.spec.stage.duration);if(this.#cache?.time===time)return structuredClone(this.#cache);const props=new Map(this.#doc.nodes.map(n=>[n.id,{...n.props}]));
 // Avaliação analítica; frame independente da direção do seek.
 let result;try{result=this.#runtime.evaluate({globalTime:time,snapshot:this.#doc.spec});}catch(e){this.#runtime.wakeAll();throw e;}for(const c of result.changes)props.get(c.id)[c.property]=c.value;
 const frame=new Map(),index=new Map(this.#doc.nodes.map(n=>[n.id,n]));
 const visit=id=>{if(frame.has(id))return frame.get(id);const n=index.get(id),p=props.get(id),parent=n.parent?visit(n.parent):null;const local=composeTransform({position:[p.x,p.y,p.z],rotation:eulerQuaternion([p.rx,p.ry,p.rz]),scale:[p.sx,p.sy,p.sz]});const matrix=multiplyMatrices(parent?.matrix??identityMatrix(),local);const o={...n,props:p,matrix,opacity:p.opacity*(parent?.opacity??1)};frame.set(id,o);return o;};
 this.#cache={time,stage:this.#doc.spec.stage,objects:this.#doc.nodes.map(n=>visit(n.id)),evaluated:result.evaluated};return structuredClone(this.#cache);
 }
}
