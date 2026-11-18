import test from 'node:test';import assert from 'node:assert/strict';
import {CATALOG,createMotifGIL,sourceFor,soundSamples,wavBlob,MOTIFS,PALETTES} from '../web/roteiro-catalog-v04.mjs';
import {prepare} from '../web/gil-native.mjs';
import {previewProjectPlan} from '../web/roteiro-project-v04.mjs';
test('catálogo possui mais de quatrocentas variantes geráveis, com IDs únicos',()=>{
 assert.ok(CATALOG.length>400);assert.equal(new Set(CATALOG.map(x=>x.id)).size,CATALOG.length);
});
test('todas as geometrias têm GIL executável em começo, meio e fim',()=>{
 for(const motif of MOTIFS){const source=createMotifGIL({motif:motif[0],duration:4,label:'AÇÕES → 𝛑'});const p=prepare(source);for(const t of [0,2,4])assert.match(p.frame(t),/<svg\b/);}
});
test('todas as variantes sonoras geram PCM finito e RIFF',()=>{
 for(const item of CATALOG.filter(a=>a.type==='sound')){const {pcm,rate}=soundSamples(item);assert.ok(pcm.length>0&&rate===22050);assert.ok(pcm.every(Number.isFinite));}
 const b=wavBlob(CATALOG.find(a=>a.type==='sound'));assert.equal(b.type,'audio/wav');assert.ok(b.size>44);
});
const fixture={titulo:'Base',cenas:[{id:'a',tipo:'svg',duracao:8,titulo:'A',subtitulo:'',audio:{voice_text:''},objetos_midia:[{id:'v',kind:'video',file:'clip.mp4',start:0,end:8}]}]};
test('planos validam e não mudam documento original',()=>{
 const before=JSON.stringify(fixture);
 const res=previewProjectPlan(fixture,{format:'rd-studio-project-plan-0.4',expect:{title:'Base',scene_ids:['a']},operations:[{type:'scene.clone',source:'a',id:'b'},{type:'scene.text',id:'b',field:'titulo',text:'B'},{type:'object.clone',scene_id:'b',source:'v',id:'c'},{type:'object.position',scene_id:'b',id:'c',x:.8,rotation:40}]});
 assert.equal(res.project.cenas.length,2);assert.equal(res.project.cenas[1].objetos_midia.length,2);assert.equal(res.project.cenas[1].objetos_midia[1].rotation,40);assert.equal(JSON.stringify(fixture),before);
});
test('operação inválida impede aplicação parcial',()=>{
 const before=JSON.stringify(fixture);
 assert.throws(()=>previewProjectPlan(fixture,{format:'rd-studio-project-plan-0.4',operations:[{type:'scene.clone',source:'a',id:'b'},{type:'object.clone',scene_id:'a',source:'inexistente',id:'c'}]}),/Operação 2/);
 assert.equal(JSON.stringify(fixture),before);
});
