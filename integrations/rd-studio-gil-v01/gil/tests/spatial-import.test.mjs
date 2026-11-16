import {test} from 'node:test';import assert from 'node:assert/strict';import {convert} from '../tools/import_spatialseed.mjs';import {compile} from '../src/model.mjs';import {Timeline} from '../src/timeline.mjs';
const root=process.env.RD_SPATIALSEED_ROOT;
const box={id:'box',kind:'box',parentId:'g',position:[2,0,0],rotation:[0,0,0,1],scale:[1,1,1],geometry:{type:'box',size:[1,2,3]},material:{color:'#66aacc'}};
const snapshot={format:'spatial-seed',schemaVersion:4,scene:{objects:[{id:'g',kind:'group',position:[1,1,0],rotation:[0,0,Math.SQRT1_2,Math.SQRT1_2],scale:[1,1,1]},box]}};
test('invalid snapshot refused',async()=>{await assert.rejects(convert({},root??'.'));});
test('canonical projector + world transform for group and box', {skip:!root},async()=>{const d=compile(await convert(snapshot,root)),f=new Timeline(d).sample(0),g=f.objects.find(o=>o.kind==='mesh.box');assert.equal(g.props.sourceId,'box');assert.ok(Math.abs(g.matrix[12]-1)<1e-8);assert.ok(Math.abs(g.matrix[13]-3)<1e-8);assert.equal(g.props.sy,2);const unsupported=structuredClone(snapshot);unsupported.scene.objects[1].geometry.type='sphere';await assert.rejects(convert(unsupported,root));});
