import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {inspectNarrations,enableNarrations} from '../web/voice-bulk.mjs';
const specimen=()=>({volume_voz:0,cenas:[
 {id:'c1',duracao:11,componente_gil:{source:'keep'},audio:{voice_text:'Texto com voz',voice_enabled:false,muted:true,voice_volume:1,voice_file:'',tracks:[{file:'keep.wav'}]}},
 {id:'c2',duracao:8,audio:{voice_text:'Outra fala',voice_enabled:true,muted:false,voice_volume:0,voice_file:'voz_pronta.wav',tracks:[]}},
 {id:'c3',duracao:6,audio:{voice_text:'',voice_enabled:false,muted:true,voice_volume:1,tracks:[]}}
]});
test('auditoria detecta quatro condições de silêncio sem alterar dados',()=>{
 const p=specimen(),original=JSON.stringify(p),r=inspectNarrations(p);
 assert.deepEqual(r.eligible,[0,1]);assert.deepEqual(r.disabled,[0]);assert.deepEqual(r.muted,[0]);
 assert.deepEqual(r.zeroSceneVolume,[1]);assert.equal(r.zeroGlobalVolume,true);assert.equal(JSON.stringify(p),original);
});
test('ativação em lote preserva textos, mídias e vídeo, sem mexer em cenas sem locução',()=>{
 const p=specimen(),before=structuredClone(p),result=enableNarrations(p);
 assert.equal(result.changed,true);assert.equal(result.after.needsFix,false);assert.equal(p.volume_voz,1);
 assert.equal(p.cenas[0].audio.voice_enabled,true);assert.equal(p.cenas[0].audio.muted,false);
 assert.equal(p.cenas[1].audio.voice_volume,1);assert.deepEqual(p.cenas[2],before.cenas[2]);
 assert.equal(p.cenas[0].audio.voice_text,before.cenas[0].audio.voice_text);
 assert.equal(p.cenas[0].audio.voice_file,before.cenas[0].audio.voice_file);
 assert.deepEqual(p.cenas[0].audio.tracks,before.cenas[0].audio.tracks);
 assert.deepEqual(p.cenas[0].componente_gil,before.cenas[0].componente_gil);
 assert.equal(p.cenas[0].duracao, before.cenas[0].duracao);
});
test('ativação repetida não modifica o projeto',()=>{
 const p=specimen();enableNarrations(p);const copy=JSON.stringify(p);const next=enableNarrations(p);
 assert.equal(next.changed,false);assert.equal(JSON.stringify(p),copy);
});
test('não altera projeto sem locução',()=>{
 const p={volume_voz:0,cenas:[{audio:{voice_text:'',voice_enabled:false,muted:true}}]};
 const copy=JSON.stringify(p);enableNarrations(p);assert.equal(JSON.stringify(p),copy);
});
test('EDO original contém voz global e cenas silenciadas, ativação as torna audíveis',{skip:!process.env.EDO_JSON},()=>{
 const p=JSON.parse(readFileSync(process.env.EDO_JSON,'utf8'));
 assert.equal(p.cenas.length,16);assert.equal(p.volume_voz,0);
 const audit=inspectNarrations(p);assert.equal(audit.disabled.length,16);assert.equal(audit.muted.length,16);
 const before=p.cenas.map(c=>[c.id,c.duracao,c.svg,c.gil_nativo,c.objetos_midia,c.audio.voice_text]);
 enableNarrations(p);
 assert.equal(inspectNarrations(p).needsFix,false);assert.equal(p.volume_voz,1);
 assert.deepEqual(p.cenas.map(c=>[c.id,c.duracao,c.svg,c.gil_nativo,c.objetos_midia,c.audio.voice_text]),before);
});
