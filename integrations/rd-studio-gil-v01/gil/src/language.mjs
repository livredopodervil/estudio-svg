import {compileAffineExpression, evaluateCompiledAffineExpression} from './spatialseed.mjs';
export const LANGUAGE = 'gil-timeline-0.1';
// DSL por linhas; argumentos estruturados são JSON. Não executa JavaScript.
export function parse(source) {
  if (typeof source !== 'string' || source.length > 250000) throw Error('Fonte inválida ou excessiva');
  const spec = {version: LANGUAGE, stage: null, resources: [], objects: [], tracks: [], cues: []};
  let open = false, end = false;
  const json = s => JSON.parse(s);
  for (const [i, raw] of source.split(/\r?\n/).entries()) {
    const line = raw.trim(); if (!line || line.startsWith('//')) continue;
    try {
      if (!open) { if (line !== 'gil timeline 0.1 {') throw Error('Cabeçalho esperado: gil timeline 0.1 {'); open=true; continue; }
      if (end) throw Error('Conteúdo após fechamento');
      if (line === '}') { end=true; continue; }
      let m;
      if ((m=/^stage\s+(.+)$/.exec(line))) { if(spec.stage) throw Error('stage duplicado'); spec.stage=json(m[1]); }
      else if ((m=/^resource\s+(\S+)\s+(\S+)\s+(.+)$/.exec(line))) spec.resources.push({id:m[1],kind:m[2],props:json(m[3])});
      else if ((m=/^object\s+(\S+)\s+(\S+)\s+(\S+)\s+(.+)$/.exec(line))) spec.objects.push({id:m[1],resource:m[2],parent:m[3]==='-'?null:m[3],props:json(m[4])});
      else if ((m=/^repeat\s+(\S+)\s+(\S+)\s+(\S+)\s+(\d+)\s+(.+)$/.exec(line))) {
        const count=Number(m[4]), template=json(m[5]);
        if (count<1||count>128||!template||Array.isArray(template)||typeof template!=='object') throw Error('repeat inválido (máximo 128)');
        const properties=Object.entries(template).map(([k,v])=>[k,v, v&&typeof v==='object'&&Object.keys(v).length===1&&typeof v.expr==='string'?compileAffineExpression(v.expr):null]);
        for(let j=1;j<=count;j++) spec.objects.push({id:`${m[1]}_${j}`,resource:m[2],parent:m[3]==='-'?null:m[3],props:Object.fromEntries(properties.map(([k,v,e])=>[k,e?evaluateCompiledAffineExpression(e,{i:j,count,u:count===1?0:(j-1)/(count-1)}):v]))});
      }
      else if ((m=/^animate\s+(\S+)\s+(\S+)\s+(.+)$/.exec(line))) spec.tracks.push({target:m[1],property:m[2],animation:json(m[3])});
      else if ((m=/^cue\s+(\S+)\s+(.+)$/.exec(line))) spec.cues.push({target:m[1],timing:json(m[2])});
      else throw Error('Diretiva desconhecida');
      if(spec.objects.length>512||spec.tracks.length>1024||spec.resources.length>128||spec.cues.length>128) throw Error('Limite de projeto excedido');
    } catch(e) {throw Error(`Linha ${i+1}: ${e.message}`);}
  }
  if(!open||!end||!spec.stage) throw Error('Documento incompleto'); return spec;
}
export function serialize(s) {
  const j=JSON.stringify; return ['gil timeline 0.1 {',`stage ${j(s.stage)}`,
    ...s.resources.map(r=>`resource ${r.id} ${r.kind} ${j(r.props)}`),
    ...s.objects.map(o=>`object ${o.id} ${o.resource} ${o.parent??'-'} ${j(o.props)}`),
    ...s.tracks.map(a=>`animate ${a.target} ${a.property} ${j(a.animation)}`),
    ...s.cues.map(c=>`cue ${c.target} ${j(c.timing)}`),'}',''].join('\n');
}
