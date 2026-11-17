import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {motionSource,motionProgram,objectMotion} from '../web/scene-objects.mjs';
import {appearance,cssAppearance} from '../web/visual-effects.mjs';

const root=new URL('../',import.meta.url);
const source=name=>readFileSync(new URL(name,root),'utf8');

test('media gate serializes concurrent play and cancellation',async()=>{
 const context={};context.window=context;
 vm.runInNewContext(source('web/media-start-gate.js'),context);
 let resolvePlay, rejectPlay, calls=0, pauses=0;
 const media={paused:true,play(){calls++;return new Promise((resolve,reject)=>{resolvePlay=resolve;rejectPlay=reject;});},pause(){pauses++;this.paused=true;}};
 const gate=context.RDMediaGate.create(media);
 const a=gate.start(),b=gate.start();assert.equal(calls,1);
 gate.stop();rejectPlay(Object.assign(Error('interrupted'),{name:'AbortError'}));
 assert.equal(await a,false);assert.equal(await b,false);assert.equal(pauses,1);
 const c=gate.start();resolvePlay();assert.equal(await c,true);
});

test('playback rejection is surfaced when cancellation was not requested',async()=>{
 const context={};context.window=context;vm.runInNewContext(source('web/media-start-gate.js'),context);
 const media={paused:true,play:()=>Promise.reject(Object.assign(Error('policy'),{name:'NotAllowedError'})),pause(){}};
 await assert.rejects(context.RDMediaGate.create(media).start(),/policy/);
});

test('GIL motion palette compiles and can stack programs',()=>{
 const presets=['enter','exit','fade','fade-out','enter-right','enter-top','enter-bottom','exit-left','exit-right','zoom-in','zoom-out','spin','float','pulse'];
 for(const preset of presets){const p=motionProgram(motionSource(preset,8));assert(Number.isFinite(p(0).x));assert(Number.isFinite(p(4).sx));assert(Number.isFinite(p(8).opacity));}
 const stacked={motion:motionSource('enter-right',8),motion_programs:[motionSource('fade',8),motionSource('float',8)]};
 const p=objectMotion(stacked);assert(p(0).x>.5);assert.equal(p(0).opacity,0);assert.equal(p(4).opacity,1);
});

test('appearance values normalize and styles are shared',()=>{
 assert.deepEqual(appearance({corner_radius:.7,border_width:100,shadow_blur:-1,border_color:'bad'}),{radius:.5,border:20,borderColor:'#ffffff',shadow:0,shadowColor:'#000000'});
 assert.match(cssAppearance({corner_radius:.2,border_width:3,border_color:'#aabbcc'}).border,/3px solid #aabbcc/);
 assert.match(source('web/browser-render.mjs'),/canvasAppearance/);
 assert.match(source('web/scene-objects.mjs'),/cssAppearance/);
 assert.match(source('standalone_native.py'),/visual-effects\.mjs/);
});

test('legacy selection requires explicit conversion; original audio is transferred',()=>{
 const editor=source('web/scene-object-editor.mjs');
 assert.match(editor,/function selectLegacy\(/);
 assert.match(editor,/confirm\('Converter o clipe original/);
 assert.match(editor,/audio_enabled:clip\.audio_enabled/);
 assert.match(editor,/c\.video_clipe=\{\.\.\.clip,arquivo:'',audio_enabled:false\}/);
 assert.match(source('web/app.js'),/selectLegacy\('clip'\)/);
 assert.match(source('web/app.js'),/selectLegacy\(project\.cenas\[selected\]\.tipo==='svg'/);
});

test('same native graphics runtime referenced by editor, presentation and standalone',()=>{
 assert.match(source('web/app.js'),/import\('\/scene-objects\.mjs'\)/);
 assert.match(source('web/captura.js'),/import\('\/scene-objects\.mjs'\)/);
 assert.match(source('standalone_native.py'),/scene-objects\.mjs/);
 assert.match(source('web_player/v3/player.js'),/import\('\/scene-objects\.mjs'\)/);
});
