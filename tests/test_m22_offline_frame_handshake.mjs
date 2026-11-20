import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const file=new URL('../web/studio-spatialseed-viewport.mjs',import.meta.url);
const source=readFileSync(file,'utf8');
const start=source.indexOf(' async function frameAtOffline(scene,time,aspect,signal){');
const end=source.indexOf('\n // Browser export may use this bridge',start);
assert.ok(start>0&&end>start,'frameAtOffline() encontrada');
const snippet=source.slice(start,end);
const make=(video)=>new Function('video',`let exportActive=true;
 const beginExport=()=>{};const frameAt=async()=>video;
 ${snippet}
 return frameAtOffline;`)(video);
test('cena WebGL estática pode fornecer quadro válido sem callback novo',async()=>{
 const video={readyState:4,videoWidth:720,videoHeight:1280,
  requestVideoFrameCallback(){throw Error('não chamar: nenhuma atualização necessária');}};
 const result=await make(video)({},0,720/1280,{});
 assert.equal(result,video);
});
test('quadro ainda não decodificado permanece bloqueado',async()=>{
 await assert.rejects(make({readyState:1,videoWidth:720,videoHeight:1280})({},0,1,{}),/Quadro WebGL indisponível/);
});
test('dimensões WebGL nulas permanecem bloqueadas',async()=>{
 await assert.rejects(make({readyState:3,videoWidth:0,videoHeight:0})({},0,1,{}),/Quadro WebGL indisponível/);
});
test('cancelamento permanece efetivo',async()=>{
 await assert.rejects(make({readyState:4,videoWidth:720,videoHeight:1280})({},0,1,{aborted:true}),/cancelada/);
});
test('sincronização de desenho usa o iframe SpatialSeed',()=>{
 assert.match(source,/w\.requestAnimationFrame\(\(\)=>w\.requestAnimationFrame\(resolve\)\)/);
});
