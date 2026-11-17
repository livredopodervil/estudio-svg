import test from 'node:test';
import assert from 'node:assert/strict';
import {geometry,dragPose} from '../web/viewport-affine.mjs';
import {tools} from '../web/viewport-gizmo.mjs';

const W=360,H=250;
const base=()=>({x:.5,y:.5,w:.44,h:.44,rotation:0,shear:0,pivot_x:0,pivot_y:0});
const pose=o=>({...o,rz:o.rotation});
const near=(a,b)=>assert(Math.abs(a-b)<1e-8,`${a} != ${b}`);
test('viewport exposes exactly the six distinct action modes',()=>{
 assert.deepEqual(tools,['select','move','scale','rotate','shear','pivot']);
});
test('free-drag modes act on the same affine object without mutating input',()=>{
 for(const [handle,field] of [['move','x'],['scale-free','w'],['rotate-free','rotation'],['shear-free','shear'],['pivot','pivot_x']]){
  const o=base();const p=pose(o);const r=dragPose(o,p,W,H,handle,{x:100,y:100},{x:126,y:114});
  assert.notEqual(r[field],o[field],handle);
  assert.equal(o[field],base()[field],'preview is reversible');
  for(const k of ['x','y','w','h','rotation','shear','pivot_x','pivot_y'])assert(Number.isFinite(r[k]),handle+': '+k);
 }
});
test('rotating through 360 degrees wraps and scale preserves aspect ratio',()=>{
 const o=base(),p=pose(o),s=dragPose(o,p,W,H,'scale-free',{x:0,y:0},{x:34,y:12});
 near(s.w/o.w,s.h/o.h);
 const r=dragPose(o,p,W,H,'rotate-free',{x:0,y:0},{x:390,y:0});
 near(r.rotation,30);
});
test('corner grip remains distinct from moving the stage crop',()=>{
 const o=base(),g=geometry(pose(o),W,H);const from=g.at(1,1);
 const moved=dragPose(o,pose(o),W,H,'1,1',from,{x:from.x+30,y:from.y+30});
 assert(moved.w>o.w&&moved.h>o.h);near(moved.x,o.x);near(moved.y,o.y);
});
