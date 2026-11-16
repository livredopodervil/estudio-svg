// Experimental Roteiro frontend. Autor: Rogério Duarte; assistência OpenAI.
// No evaluation engine: compile to GIL validated by the installed GIL.
const ID='[A-Za-z][A-Za-z0-9_.-]{0,63}';
const NUM='-?(?:[0-9]+(?:\\.[0-9]+)?|\\.[0-9]+)';
const SEC='('+NUM+')s';
const rounded=x=>Math.round(x*1e6)/1e6;
const requireOk=(x,msg)=>{if(!x)throw Error(msg);};
const re=x=>new RegExp('^'+x+'$');
const positive=x=>{const n=Number(x);requireOk(Number.isFinite(n)&&n>0&&n<=600&&rounded(n)>0,'Duração inválida');return rounded(n);};
export function parseRoteiro(source){
 requireOk(typeof source==='string'&&source.length<=100000,'Fonte excessiva');
 const lines=source.split(/\r?\n/).map((raw,i)=>({s:raw.trim(),line:i+1})).filter(x=>x.s&&!x.s.startsWith('//'));
 requireOk(lines.shift()?.s==='roteiro 0.1 {','Cabeçalho roteiro 0.1 { esperado');
 const root={kind:'parallel',children:[]},stack=[root],markers=new Map();let count=0;
 for(const {s,line} of lines){try{
  requireOk(stack.length,'Conteúdo depois do fechamento');
  if(s==='}'){stack.pop();continue;}
  let m,node;const parent=stack.at(-1);
  if((m=re('marca ('+ID+') '+SEC).exec(s))){requireOk(parent===root&&!markers.has(m[1]),'Marca duplicada ou fora da raiz');const t=Number(m[2]);requireOk(Number.isFinite(t)&&t>=0&&t<=600,'Marca inválida');markers.set(m[1],rounded(t));continue;}
  if(s==='sequencia {'||s==='paralelo {')node={kind:s==='sequencia {'?'sequence':'parallel',children:[],line};
  else if((m=re('em ('+ID+') \\{').exec(s))){requireOk(parent===root,'em só pode ocorrer na raiz');node={kind:'marker',name:m[1],children:[],line};}
  else if((m=re('esperar '+SEC).exec(s)))node={kind:'wait',duration:positive(m[1]),line};
  else if((m=re('efeito ('+ID+') durante '+SEC).exec(s)))node={kind:'cue',target:m[1],duration:positive(m[2]),line};
  else if((m=re('corte ('+ID+') para ('+ID+') durante '+SEC).exec(s))){requireOk(m[1]!==m[2],'Corte exige dois objetos distintos');node={kind:'cut',target:m[1],to:m[2],duration:positive(m[3]),line};}
  else if((m=re('(deslizar|pulso) ('+ID+') para (\\[[^\\]]+\\]) durante '+SEC).exec(s))){const a=JSON.parse(m[3]);requireOk(Array.isArray(a)&&a.length===3&&a.every(Number.isFinite),'Vetor inválido');node={kind:m[1]==='deslizar'?'slide':'pulse',target:m[2],values:Object.fromEntries((m[1]==='deslizar'?['x','y','z']:['sx','sy','sz']).map((p,i)=>[p,a[i]])),duration:positive(m[4]),line};}
  else if((m=re('(mover|girar|escalar) ('+ID+') para (\\[[^\\]]+\\]) durante '+SEC).exec(s))){const a=JSON.parse(m[3]);requireOk(Array.isArray(a)&&a.length===3&&a.every(Number.isFinite),'Vetor inválido');node={kind:'tween',target:m[2],values:Object.fromEntries(({mover:['x','y','z'],girar:['rx','ry','rz'],escalar:['sx','sy','sz']}[m[1]]).map((p,i)=>[p,a[i]])),duration:positive(m[4]),line};}
  else if((m=re('animar ('+ID+') ('+ID+') para ('+NUM+') durante '+SEC).exec(s)))node={kind:'tween',target:m[1],values:{[m[2]]:Number(m[3])},duration:positive(m[4]),line};
  else if((m=re('(aparecer|desaparecer) ('+ID+') durante '+SEC).exec(s)))node={kind:'tween',target:m[2],values:{opacity:m[1]==='aparecer'?1:0},duration:positive(m[3]),line};
  else throw Error('Diretiva desconhecida');
  requireOk(++count<=1000,'Limite de ações excedido');parent.children.push(node);if(node.children){requireOk(stack.length<32,'Hierarquia temporal profunda');stack.push(node);}
 }catch(e){throw Error(`Linha ${line}: ${e.message}`);}}
 requireOk(stack.length===0,'Bloco não fechado');return {root,markers};
}
export function compileRoteiro(base,source,{compile,serialize}){
 const doc=compile(base),spec=structuredClone(doc.spec),{root,markers}=parseRoteiro(source),nodes=new Map(doc.nodes.map(o=>[o.id,o]));
 const existing=new Set(spec.tracks.map(t=>t.target+'\0'+t.property)),tracks=new Map(),cues=[],events=[];
 const limit=spec.stage.duration;
 function visit(n,start){
  if(n.kind==='marker'){requireOk(markers.has(n.name),`Marca desconhecida: ${n.name}`);return visit({...n,kind:'sequence'},markers.get(n.name));}
  if(n.children){let end=start;for(const ch of n.children){const e=visit(ch,n.kind==='sequence'?end:start);end=Math.max(end,e);}return end;}
  const end=rounded(start+n.duration);requireOk(end<=limit&&end>start,`Linha ${n.line}: ação fora do palco (${limit}s)`);
  if(n.kind==='cue'){requireOk(nodes.get(n.target)?.kind==='audio.tone',`Linha ${n.line}: efeito inválido`);cues.push({target:n.target,timing:{start,duration:n.duration}});}
  else if(['tween','slide','pulse','cut'].includes(n.kind)){
   const add=(target,values,mode)=>{const o=nodes.get(target);requireOk(o,`Linha ${n.line}: objeto inexistente ${target}`);for(const [property,value] of Object.entries(values)){const key=target+'\0'+property;requireOk(Object.hasOwn(o.props,property)&&typeof o.props[property]==='number',`Linha ${n.line}: propriedade inválida ${property}`);requireOk(!existing.has(key),`Linha ${n.line}: faixa preexistente ${target}.${property}; não sobrescrita`);doc.registry.require(property).normalize(value);if(!tracks.has(key))tracks.set(key,{target,property,initial:o.props[property],actions:[]});tracks.get(key).actions.push({start,end,value,line:n.line,mode});}};
   if(n.kind==='cut'){add(n.target,{opacity:0},'tween');add(n.to,{opacity:1},'tween');}else add(n.target,n.values,n.kind);
  }
  events.push({kind:n.kind,target:n.target??null,...(n.kind==='cut'?{to:n.to}:{}),start,end,line:n.line});return end;
 }
 visit(root,0);
 for(const tr of tracks.values()){
  const actions=tr.actions.sort((a,b)=>a.start-b.start);let end=actions[0].start,v=tr.initial;const keys=[[end,v]];
  for(const a of actions){requireOk(a.start>=end,`Linha ${a.line}: conflito temporal ${tr.target}.${tr.property}`);if(a.start>end)keys.push([a.start,v]);if(a.mode==='slide'){for(let i=1;i<=5;i++){const u=i/5,t=rounded(a.start+(a.end-a.start)*u);requireOk(t>keys.at(-1)[0],`Linha ${a.line}: deslizar demasiado curto`);keys.push([t,i===5?a.value:v+(a.value-v)*u*u*(3-2*u)]);}v=a.value;}
   else if(a.mode==='pulse'){const mid=rounded((a.start+a.end)/2);requireOk(mid>a.start&&mid<a.end,`Linha ${a.line}: pulso demasiado curto`);keys.push([mid,a.value],[a.end,v]);}
   else{keys.push([a.end,a.value]);v=a.value;}end=a.end;}
  spec.tracks.push({target:tr.target,property:tr.property,animation:{start:keys[0][0],end,keys,ease:'linear'}});
 }
 spec.cues.push(...cues);const validated=compile(spec);return {source:serialize(validated.spec),doc:validated,events:events.sort((a,b)=>a.start-b.start||a.line-b.line)};
}
