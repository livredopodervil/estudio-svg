// Pure plans. The current DocumentService validates and commits the entire result once.
export function moveKey(animation,index,time,duration){
 if(!Array.isArray(animation.keys)||!Number.isInteger(index)||index<0||index>=animation.keys.length||!Number.isFinite(time))throw Error('Keyframe inválido');
 const next=structuredClone(animation),lo=Math.max(animation.start??0,index?next.keys[index-1][0]+.001:0),hi=Math.min(animation.end??duration,index+1<next.keys.length?next.keys[index+1][0]-.001:duration);
 if(hi<lo)throw Error('Não há espaço entre keyframes');next.keys[index][0]=Math.min(hi,Math.max(lo,Math.round(time*1000)/1000));return next;
}
export const MOTIONS=[['entrance','Entrada'],['pulse','Pulso'],['orbit','Rotação'],['float','Oscilação'],['rise','Elevação']];
export function motionPlan(doc,id,kind,time,length){
 const n=doc.nodes.find(x=>x.id===id);if(!n||!MOTIONS.some(([k])=>k===kind)||!Number.isFinite(time)||!Number.isFinite(length)||length<=0)throw Error('Movimento inválido');
 const s=structuredClone(doc.spec),p=n.props,end=Math.min(s.stage.duration,time+length);if(time<0||end-time<.05)throw Error('Sem espaço na timeline');const mid=(time+end)/2,tracks=[];
 const keys=(property,points)=>tracks.push({target:id,property,animation:{start:time,end,keys:points,ease:'smooth'}});
 if(kind==='entrance'){keys('opacity',[[time,0],[end,p.opacity]]);keys('x',[[time,p.x-2],[end,p.x]]);}
 if(kind==='pulse')for(const k of ['sx','sy','sz'])keys(k,[[time,p[k]],[mid,Math.min(1000,p[k]*1.18)],[end,p[k]]]);
 if(kind==='orbit')keys('ry',[[time,p.ry],[end,p.ry+360]]);
 if(kind==='float')keys('y',[[time,p.y],[mid,p.y+.6],[end,p.y]]);
 if(kind==='rise'){keys('y',[[time,p.y-2],[end,p.y]]);keys('opacity',[[time,0],[end,p.opacity]]);}
 if(kind==='entrance'||kind==='rise'){const target=s.objects.find(o=>o.id===id);target.props.opacity=0;const axis=kind==='entrance'?'x':'y';target.props[axis]=p[axis]-2;}
 const conflicts=tracks.filter(a=>s.tracks.some(t=>t.target===a.target&&t.property===a.property)).map(t=>t.property);
 s.tracks=s.tracks.filter(t=>!tracks.some(a=>a.target===t.target&&a.property===t.property)).concat(tracks);
 return {spec:s,conflicts};
}
