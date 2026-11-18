import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const source=readFileSync(new URL('../web/browser-render.mjs',import.meta.url),'utf8');
const first=source.indexOf('// M1N_AUDIO_BEGIN');
const last=source.indexOf('// M1N_AUDIO_END');
if(first<0||last<first)throw Error('Integração M1N ausente');
const api=await import('data:text/javascript;charset=utf-8,'+encodeURIComponent(source.slice(first,last)));
const {parseGILToneCues,collectGILAudioEvents,scheduleGILToneEvents}=api;
const src=`gil timeline 0.1 {
stage {"width":960,"height":540,"duration":10,"background":"#000000","camera":"cam"}
resource camera camera {"z":15}
resource b audio.tone {"frequency":440,"gain":0.03,"wave":"sine"}
object cam camera - {}
object beep b - {}
cue beep {"start":1.25,"duration":0.4}
cue beep {"start":8.0,"duration":0.2}
}`;
const compiler=()=>({duration:10,cues:true});
test('tom GIL mantém frequência, volume, forma e posição',()=>{
 assert.deepEqual(parseGILToneCues(src,{duration:10,compiledCues:true}),[
 {target:'beep',start:1.25,duration:.4,frequency:440,gain:.03,wave:'sine'},
 {target:'beep',start:8,duration:.2,frequency:440,gain:.03,wave:'sine'}]);
});
test('rejeita evento que não possui sintetizador suportado, sem silenciar',()=>{
 assert.throws(()=>parseGILToneCues(src.replace('audio.tone','audio.external'),{duration:10,compiledCues:true}),/não suportado/);
 assert.throws(()=>parseGILToneCues(src.replace('cue beep','cue missing'),{duration:10,compiledCues:true}),/cue sem objeto/);
 assert.throws(()=>parseGILToneCues(src.replace('"wave":"sine"','"wave":"bad"'),{duration:10,compiledCues:true}),/parâmetros/);
 assert.throws(()=>parseGILToneCues(src.replaceAll('cue beep','// cue beep'),{duration:10,compiledCues:true}),/eventos de tipo/);
});
test('nominal preservada quando a fala estende duração efetiva',()=>{
 const events=collectGILAudioEvents([{start:15,nominal:10,duration:18,scene:{gil_nativo:{source:src}}}],compiler);
 assert.deepEqual(events.map(x=>x.time),[16.25,23]);
});
test('objeto com offset e loop usa o relógio da cena',()=>{
 const entry={start:20,nominal:30,scene:{objetos_midia:[{kind:'gil',start:2,end:25,offset:2,loop:true,gil:{source:src}}]}};
 const events=collectGILAudioEvents([entry],compiler);
 assert.ok(events.every(e=>e.time>=22&&e.time<45));
 assert.ok(events.some(e=>e.time===31.25));
 assert.ok(events.some(e=>e.time===41.25));
});
test('agendamento usa o mesmo clock Web Audio do mix e envelope sem estalos',()=>{
 const osc=[],gains=[];
 const ac={createOscillator(){const a={frequency:{setValueAtTime(...args){a.frequencyArgs=args;}},connect(){},disconnect(){},start(t){a.started=t;},stop(t){a.stopped=t;}};osc.push(a);return a;},createGain(){const g={gain:{setValueAtTime(){},linearRampToValueAtTime(...args){g.lastRamp=args;}},connect(){},disconnect(){}};gains.push(g);return g;}};
 scheduleGILToneEvents(ac,{},[{time:12,duration:.25,frequency:440,gain:.04,wave:'sine'}],60);
 assert.equal(osc.length,1);assert.equal(osc[0].started,72);assert.equal(osc[0].stopped,72.25);assert.equal(gains[0].lastRamp[1],72.25);
});
test('M1N integrado ao exportador, não abandona sons GIL',()=>{
 const code=readFileSync(new URL('../web/browser-render.mjs',import.meta.url),'utf8');
 assert.match(code,/collectGILAudioEvents\(settings\.entries,prepare\)/);
 assert.match(code,/scheduleGILToneEvents\(context,dest,gilAudio,start\)/);
 assert.doesNotMatch(code,/A camada GIL possui som ainda não suportado/);
});
