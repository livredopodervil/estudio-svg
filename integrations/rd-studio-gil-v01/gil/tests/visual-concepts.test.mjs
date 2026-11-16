import test from 'node:test';import assert from 'node:assert/strict';import {readFile} from 'node:fs/promises';
import {compileRoteiro} from '../src/roteiro.mjs';import {compile} from '../src/model.mjs';import {serialize} from '../src/language.mjs';import {Timeline} from '../src/timeline.mjs';import {renderSVG} from '../src/render-svg.mjs';
const gil={compile,serialize};const wrap=s=>'roteiro 0.1 {\n'+s+'\n}';
const base=`gil timeline 0.1 {
stage {"width":960,"height":540,"duration":8,"background":"#000000","camera":"cam"}
resource cam camera {"z":15}
resource group group {}
object cam cam - {}
object a group - {"x":0,"opacity":1,"sx":2}
object b group - {"opacity":0}
}`;
const run=s=>compileRoteiro(base,wrap(s),gil);const props=(r,t,id)=>new Timeline(r.doc).sample(t).objects.find(o=>o.id===id).props;
test('corte em opacidade preserva os objetos e registra alvo e destino',()=>{const r=run('corte a para b durante 0.04s');assert.equal(props(r,0,'a').opacity,1);assert.equal(props(r,.04,'b').opacity,1);assert.equal(props(r,.04,'a').opacity,0);assert.equal(r.events[0].to,'b');assert.equal(r.events[0].kind,'cut');});
test('deslizar preserva extremos, acelera e desacelera; pulso retorna à escala anterior',()=>{const r=run('sequencia {\ndeslizar a para [10,0,0] durante 2s\npulso a para [4,2,1] durante 2s\n}');assert.ok(props(r,.4,'a').x<2);assert.equal(props(r,2,'a').x,10);assert.equal(props(r,3,'a').sx,4);assert.equal(props(r,4,'a').sx,2);assert.deepEqual(props(r,1,'a'),props(r,1,'a'));});
test('eventos novos respeitam conflitos e alvos inválidos',()=>{assert.throws(()=>run('paralelo {\ncorte a para b durante 1s\naparecer a durante 2s\n}'),/conflito temporal/);assert.throws(()=>run('corte a para a durante 1s'),/distintos/);assert.throws(()=>run('deslizar falso para [1,2,3] durante 1s'),/inexistente/);assert.throws(()=>run('pulso a para [-1,1,1] durante 1s'),/sx/);});
test('exemplo data center compila exatamente para a fonte instalada e permite seek',async()=>{const example=JSON.parse(await readFile(new URL('../examples/roteiro-datacenter.json',import.meta.url),'utf8'));const r=compileRoteiro(example.base,example.script,gil);assert.equal(r.source,await readFile(new URL('../examples/datacenter.gil',import.meta.url),'utf8'));assert.equal(r.doc.nodes.length,474);assert.equal(r.doc.tracks.length,316);assert.equal(r.doc.cues.length,10);const timeline=new Timeline(r.doc);const first=timeline.sample(1);for(const shot of example.editorial.shots){const f=timeline.sample(shot.start+shot.duration/2);assert.equal(f.objects.find(o=>o.id===shot.id).props.opacity,1);assert.equal(f.objects.filter(o=>/^s\d\d$/.test(o.id)&&o.props.opacity>.99).length,1);assert.ok(renderSVG(f).svg.includes('<svg'));}assert.deepEqual(timeline.sample(1),first);});
