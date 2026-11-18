import test from 'node:test';
import assert from 'node:assert/strict';
import {splitRoteiro03,parseAgentPlan,previewScenePlan,transitionSource} from '../web/roteiro-plan-v03.mjs';
import {motionProgram} from '../web/scene-objects.mjs';
import {compileRoteiro} from '../web/roteiro-v02.mjs';
import {createStyleBase,createStyleScript} from '../web/roteiro-styles.mjs';
import {compile} from '../web/gil-runtime/src/model.mjs';
import {serialize} from '../web/gil-runtime/src/language.mjs';
const clip={id:'film1',kind:'video',file:'video.mp4',label:'Vídeo',x:.5,y:.5,w:.7,h:.6,start:0,end:8,offset:0,audio_enabled:false,audio_volume:1,audio_fade_in:0,audio_fade_out:0,motion:'',motion_programs:[]};
const scene=()=>({id:'sc1',tipo:'svg',duracao:8,titulo:'Inicial',subtitulo:'',objetos_midia:[structuredClone(clip)],audio:{scene_fade_in:0,scene_fade_out:0,tracks:[{file:'music.mp3',start:0,volume:1,fade_in:0,fade_out:0,loop:false}],voice_volume:1,voice_delay:0}});
const plan=operations=>({format:'rd-studio-plan-0.3',operations});
test('M1d module syntax regression: no duplicate seek binding',async()=>{
 const source=(await import('node:fs/promises')).readFile(new URL('../web/roteiro-editor.mjs',import.meta.url),'utf8');
 const src=await source;
 assert.match(src,/seek:seekScene/);assert.match(src,/seekSlider=get\('seek'\)/);
});
test('0.3 splits root-level document edits from existing GIL 0.2 animation',()=>{
 const original=createStyleScript({style:'editorial'}).replace('roteiro 0.2','roteiro 0.3');
 const s=original.replace(/\n}\s*$/, '\n clipe film1 entre 1s e 7s\n clipe film1 quadro [0.5,0.5,0.8,0.6]\n clipe film1 audio volume 0.8 entrada 0.2s saida 0.3s\n transicao film1 entrada dissolver durante 0.4s\n audio cena entrada 0.2s saida 0.3s\n texto cena titulo "Novo título"\n}');
 const parsed=splitRoteiro03(s);
 assert.equal(parsed.plan.operations.length,6);assert.match(parsed.gilScript,/^roteiro 0.2/);
 const g=compileRoteiro(createStyleBase({style:'editorial'}),parsed.gilScript,{compile,serialize});
 assert.ok(g.doc.tracks.length>0);
 const r=previewScenePlan(scene(),parsed.plan,{validateMotion:motionProgram});
 assert.equal(r.scene.objetos_midia[0].start,1);assert.equal(r.scene.objetos_midia[0].end,7);
 assert.equal(r.scene.objetos_midia[0].motion_programs.length,1);assert.equal(r.scene.audio.scene_fade_out,.3);assert.equal(r.scene.titulo,'Novo título');
});
test('0.3 plans reject JS, unknown props, missing clips and invalid media without mutation',()=>{
 const before=scene(),snapshot=JSON.stringify(before);
 for(const op of [{type:'javascript',code:'alert(1)'},{type:'clip.audio',id:'notfound',volume:1,fade_in:0,fade_out:0},{type:'clip.frame',id:'film1',x:10,y:.5,w:.5,h:.5},{type:'scene.text',field:'svg',text:'<script>'}]){
  assert.throws(()=>previewScenePlan(before,plan([op])));
 }
 assert.throws(()=>parseAgentPlan({format:'rd-studio-plan-0.3',operations:[],__proto__:null,bogus:true}));
 assert.equal(JSON.stringify(before),snapshot);
});
test('0.3 operations are transactional; overlap and nonexistent assets rejected',()=>{
 const original=scene(),s=JSON.stringify(original);
 assert.throws(()=>previewScenePlan(original,plan([{type:'scene.text',field:'titulo',text:'Changed'},{type:'clip.time',id:'film1',start:7,end:3}])));
 assert.throws(()=>previewScenePlan(original,plan([{type:'audio.track',index:1,start:0,volume:1,fade_in:0,fade_out:0}])));
 assert.equal(JSON.stringify(original),s);
});
test('0.3 non-destructive clip, audio and transition operations use canonical keys',()=>{
 const orig=scene();const r=previewScenePlan(orig,plan([
  {type:'clip.audio',id:'film1',volume:.6,fade_in:.3,fade_out:.4},
  {type:'audio.track',index:0,start:1.2,volume:.7,fade_in:.5,fade_out:.8},
  {type:'object.transition',id:'film1',phase:'entrada',style:'esquerda',duration:.6},
  {type:'object.transition',id:'film1',phase:'saida',style:'zoom',duration:1},
  {type:'audio.voice',volume:.9,delay:.3}
 ]),{validateMotion:motionProgram});
 assert.equal(r.scene.objetos_midia[0].file,'video.mp4');assert.equal(r.scene.objetos_midia[0].audio_enabled,true);
 assert.equal(r.scene.objetos_midia[0].motion_programs.length,2);assert.equal(r.scene.audio.tracks[0].file,'music.mp3');
 assert.equal(r.scene.audio.tracks[0].start,1.2);assert.equal(r.scene.audio.voice_delay,.3);
 assert.equal(orig.audio.tracks[0].start,0);assert.equal(orig.objetos_midia[0].motion_programs.length,0);
 for(const m of r.scene.objetos_midia[0].motion_programs) assert.doesNotThrow(()=>motionProgram(m));
});
test('0.3 root guard, malformed quotes, and transition limits',()=>{
 assert.throws(()=>splitRoteiro03('roteiro 0.3 {\n paralelo {\n clipe film1 entre 0s e 3s\n }\n}'),/apenas na raiz/);
 assert.throws(()=>splitRoteiro03('roteiro 0.3 {\n texto cena titulo "incompleto\n}'),/inválida/);
 assert.throws(()=>transitionSource({phase:'saida',style:'zoom',duration:9,objectDuration:8}),/maior|fora/);
});
