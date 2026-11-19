import {test} from 'node:test';
import assert from 'node:assert/strict';
import {validateKeyframes,sampleCameraTrack} from '../web/spatialseed-camera-track.mjs';
const a={t:0,camera:{position:[0,0,10],quaternion:[0,0,0,1],focusDistance:10,fov:55,near:.1,far:1000}};
const b={t:10,camera:{position:[10,0,0],quaternion:[0,1,0,0],focusDistance:4,fov:40,near:.2,far:200}};
test('camera track seek with aspect portrait',()=>{
 const sample=sampleCameraTrack([a,b],5,9/16);
 assert.deepEqual(sample.position,[5,0,5]);
 assert.equal(sample.aspect,9/16);
 assert.ok(Math.abs(Math.hypot(...sample.quaternion)-1)<1e-10);
});
test('hold and invalid camera tracks',()=>{
 assert.deepEqual(sampleCameraTrack([{...a,easing:'hold'},b],5,1).position,a.camera.position);
 assert.throws(()=>validateKeyframes([b,a]),/time/);
 assert.throws(()=>sampleCameraTrack([a,b],5,-1),/aspect/);
});
