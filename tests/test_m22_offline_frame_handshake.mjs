import test from 'node:test';
import assert from 'node:assert/strict';
import {mountStudioSpatialSeed} from '../web/studio-spatialseed-viewport.mjs';

// Exercise the public viewport API, including import, seek and native frame acknowledgement.
function fixture({badClock=false,fault=null}={}){
 const calls=[],elements=new Map();
 const scene={id:'s',duracao:4,spatialseed_viewport:{enabled:true,source:'{"v":1}',camera_keys:[]}};
 const bitmap={width:64,height:36};
 const native={
  query(id){
   if(id==='viewer.frame.capture'){calls.push('capture');return bitmap;}
   if(id==='time.execution')return {fault,running:false,readiness:{readyCount:0}};
   if(id==='time.domain')return {paused:false};
   if(id==='viewer.camera.snapshot')return {position:[0,0,1],fov:48};
   throw Error(id);
  },
  execute(id,args){
   calls.push([id,args]);
   if(id==='project.open')return {loaded:true};
   if(id==='time.domain.seek')return {domain:{paused:true,localTime:args.localTime+(badClock?1:0)}};
   if(id==='time.domain.pause')return {};
   throw Error(id);
  }
 };
 const el=id=>{
  if(!elements.has(id))elements.set(id,{dataset:{},hidden:false,style:{},width:64,height:36,
   classList:{toggle(){},contains(){return false},add(){}},setAttribute(){},addEventListener(){}});
  return elements.get(id);
 };
 const frame=el('ssViewportFrame');
 globalThis.window={};globalThis.location=new URL('http://localhost:8771/');
 globalThis.document={getElementById:el,activeElement:null};
 frame.contentWindow={get location(){return new URL(frame.src||location.href)},document:{getElementById:el},__SPATIAL_SEED__:native};
 const viewport=mountStudioSpatialSeed({getScene:()=>scene,getAspect:()=>16/9,getTime:()=>0,onEdit(){},onError(){}});
 return {calls,bitmap,frameAt:(t,signal)=>viewport.exportAPI.frameAtOffline(scene,t,16/9,signal)};
}
test('captura exata abre a fonte uma vez e busca 1, 3, 1 sem keyframes',async()=>{
 const f=fixture();
 for(const t of [1,3,1])assert.equal(await f.frameAt(t),f.bitmap);
 assert.equal(f.calls.filter(v=>v[0]==='project.open').length,1);
 assert.deepEqual(f.calls.filter(v=>v[0]==='time.domain.seek').map(v=>v[1].localTime),[0,1,3,1]);
 assert.equal(f.calls.filter(v=>v==='capture').length,3);
});
test('tempo divergente impede captura',async()=>{const f=fixture({badClock:true});await assert.rejects(f.frameAt(1),/instante/);assert.ok(!f.calls.includes('capture'));});
test('falha de avaliação temporal impede captura',async()=>{const f=fixture({fault:{message:'falha temporal'}});await assert.rejects(f.frameAt(1),/falha temporal/);assert.ok(!f.calls.includes('capture'));});
test('cancelamento não carrega o mundo',async()=>{const f=fixture();await assert.rejects(f.frameAt(1,{aborted:true}),/cancelada/);assert.deepEqual(f.calls,[]);});
