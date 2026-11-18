// RD Studio — Roteiro 0.2. Autor: Rogério Duarte; assistência OpenAI.
// Extensão conservadora da linguagem Roteiro 0.1: compila para GIL Timeline existente.
// Nunca executa JS do roteiro, não cria relógio nem renderizador próprio.
const ID='[A-Za-z][A-Za-z0-9_.-]{0,63}', NUM='-?(?:[0-9]+(?:\\.[0-9]+)?|\\.[0-9]+)', SEC='('+NUM+')s';
const re=x=>new RegExp('^'+x+'$'), round=x=>Math.round(x*1e6)/1e6;
function ok(v,msg){if(!v)throw Error(msg);}
const seconds=s=>{const n=Number(s);ok(Number.isFinite(n)&&n>0&&n<=600,'Duração inválida');return round(n);};
export const ENTRIES=Object.freeze(['dissolver','esquerda','direita','subir','descer','crescer']);
export const EXITS=Object.freeze(['dissolver','esquerda','direita','subir','descer','encolher']);
export function parseRoteiro(source){
 ok(typeof source==='string'&&source.length<=100000,'Roteiro excessivo');
 const lines=source.split(/\r?\n/).map((raw,i)=>({s:raw.trim(),line:i+1})).filter(x=>x.s&&!x.s.startsWith('//'));
 ok(/^roteiro 0\.[12] \{$/.test(lines.shift()?.s||''),'Cabeçalho esperado: roteiro 0.2 {');
 const root={kind:'parallel',children:[]},stack=[root],markers=new Map();let count=0,closed=false;
 for(const {s,line} of lines){try{
  ok(stack.length&&!closed,'Conteúdo fora do roteiro');
  if(s==='}'){stack.pop();if(!stack.length)closed=true;continue;}
  let m,node;const parent=stack.at(-1);
  if((m=re('marca ('+ID+') '+SEC).exec(s))){ok(parent===root&&!markers.has(m[1]),'Marca duplicada ou fora da raiz');const t=Number(m[2]);ok(Number.isFinite(t)&&t>=0&&t<=600,'Marca inválida');markers.set(m[1],round(t));continue;}
  if(s==='sequencia {'||s==='paralelo {')node={kind:s==='sequencia {'?'sequence':'parallel',children:[],line};
  else if((m=re('em ('+ID+') \\{').exec(s))){ok(parent===root,'em só pode ocorrer na raiz');node={kind:'marker',name:m[1],children:[],line};}
  else if((m=re('esperar '+SEC).exec(s)))node={kind:'wait',duration:seconds(m[1]),line};
  else if((m=re('efeito ('+ID+') durante '+SEC).exec(s)))node={kind:'cue',target:m[1],duration:seconds(m[2]),line};
  else if((m=re('(mover|girar|escalar) ('+ID+') para (\\[[^\\]]+\\]) durante '+SEC).exec(s))){
   const a=JSON.parse(m[3]);ok(Array.isArray(a)&&a.length===3&&a.every(Number.isFinite),'Vetor inválido');
   node={kind:'tween',target:m[2],values:Object.fromEntries(({mover:['x','y','z'],girar:['rx','ry','rz'],escalar:['sx','sy','sz']}[m[1]]).map((p,i)=>[p,a[i]])),duration:seconds(m[4]),line};
  }else if((m=re('animar ('+ID+') ('+ID+') para ('+NUM+') durante '+SEC).exec(s)))node={kind:'tween',target:m[1],values:{[m[2]]:Number(m[3])},duration:seconds(m[4]),line};
  else if((m=re('(aparecer|desaparecer) ('+ID+') durante '+SEC).exec(s)))node={kind:'tween',target:m[2],values:{opacity:m[1]==='aparecer'?1:0},duration:seconds(m[3]),line};
  else if((m=re('(entrada|saida) ('+ID+') (dissolver|esquerda|direita|subir|descer|crescer|encolher) durante '+SEC).exec(s))){
   const types=m[1]==='entrada'?ENTRIES:EXITS;ok(types.includes(m[3]),'Movimento inválido para entrada/saída');
   node={kind:'preset',phase:m[1],target:m[2],style:m[3],duration:seconds(m[4]),line};
  }else if((m=re('pulso ('+ID+') durante '+SEC).exec(s)))node={kind:'pulse',target:m[1],duration:seconds(m[2]),line};
  else throw Error('Diretiva desconhecida');
  ok(++count<=1000,'Mais de 1000 ações');parent.children.push(node);if(node.children){ok(stack.length<32,'Hierarquia temporal profunda');stack.push(node);}
 }catch(e){throw Error(`Linha ${line}: ${e.message}`);}}
 ok(closed&&stack.length===0,'Bloco não fechado');return {root,markers};
}
export function compileRoteiro(base,source,{compile,serialize}){
 const doc=compile(base),spec=structuredClone(doc.spec),{root,markers}=parseRoteiro(source),nodes=new Map(doc.nodes.map(o=>[o.id,o]));
 const existing=new Set(spec.tracks.map(t=>t.target+'\0'+t.property)),tracks=new Map(),cues=[],events=[];
 const limit=spec.stage.duration;
 function add(target,property,start,end,value,line,from){
  const o=nodes.get(target),key=target+'\0'+property;
  ok(o,`Linha ${line}: objeto inexistente ${target}`);
  ok(Object.hasOwn(o.props,property)&&typeof o.props[property]==='number',`Linha ${line}: propriedade inválida ${property}`);
  ok(!existing.has(key),`Linha ${line}: faixa preexistente ${target}.${property}`);
  doc.registry.require(property).normalize(value);if(from!==undefined)doc.registry.require(property).normalize(from);
  if(!tracks.has(key))tracks.set(key,{target,property,initial:o.props[property],actions:[]});
  tracks.get(key).actions.push({start,end,value,from,line});
 }
 function visit(n,start){
  if(n.kind==='marker'){ok(markers.has(n.name),`Marca desconhecida: ${n.name}`);return visit({...n,kind:'sequence'},markers.get(n.name));}
  if(n.children){let end=start;for(const ch of n.children){const e=visit(ch,n.kind==='sequence'?end:start);end=Math.max(end,e);}return end;}
  const end=round(start+n.duration);ok(end<=limit&&end>start,`Linha ${n.line}: ação fora do palco (${limit}s)`);
  if(n.kind==='cue'){ok(nodes.get(n.target)?.kind==='audio.tone',`Linha ${n.line}: efeito inválido`);cues.push({target:n.target,timing:{start,duration:n.duration}});}
  else if(n.kind==='tween')for(const [p,v] of Object.entries(n.values))add(n.target,p,start,end,v,n.line);
  else if(n.kind==='preset'){
   const o=nodes.get(n.target);ok(o,`Linha ${n.line}: objeto inexistente ${n.target}`);const p=o.props,enter=n.phase==='entrada',style=n.style;
   if(style==='dissolver')add(n.target,'opacity',start,end,enter?1:0,n.line,enter?0:undefined);
   else if(style==='crescer'||style==='encolher')for(const k of ['sx','sy']){const value=p[k];add(n.target,k,start,end,enter?value:value*.15,n.line,enter?value*.15:undefined);}
   else {const k=['esquerda','direita'].includes(style)?'x':'y',sign=['esquerda','subir'].includes(style)?-1:1,offset=sign*2.2;
    add(n.target,k,start,end,enter?p[k]:p[k]+offset,n.line,enter?p[k]+offset:undefined);
    add(n.target,'opacity',start,end,enter?1:0,n.line,enter?0:undefined);
   }
  }else if(n.kind==='pulse'){
   const o=nodes.get(n.target);ok(o,`Linha ${n.line}: objeto inexistente ${n.target}`);const half=round((start+end)/2);
   for(const k of ['sx','sy']){const base=o.props[k];add(n.target,k,start,half,base*1.14,n.line);add(n.target,k,half,end,base,n.line);}
  }
  events.push({kind:n.kind,target:n.target||null,start,end,line:n.line});return end;
 }
 visit(root,0);
 for(const tr of tracks.values()){
  const actions=tr.actions.sort((a,b)=>a.start-b.start),keys=[];let lastEnd=-1,lastValue=tr.initial;
  for(const a of actions){ok(a.start>=lastEnd,`Linha ${a.line}: conflito temporal ${tr.target}.${tr.property}`);
   if(!keys.length){keys.push([a.start,a.from??lastValue]);}
   else if(a.start>lastEnd){keys.push([a.start,a.from??lastValue]);}
   else if(a.from!==undefined&&a.from!==lastValue)throw Error(`Linha ${a.line}: salto descontínuo em ${tr.target}.${tr.property}`);
   keys.push([a.end,a.value]);lastValue=a.value;lastEnd=a.end;
  }
  spec.tracks.push({target:tr.target,property:tr.property,animation:{start:keys[0][0],end:lastEnd,keys,ease:'smooth'}});
 }
 spec.cues.push(...cues);const validated=compile(spec);
 return {source:serialize(validated.spec),doc:validated,events:events.sort((a,b)=>a.start-b.start||a.line-b.line)};
}
