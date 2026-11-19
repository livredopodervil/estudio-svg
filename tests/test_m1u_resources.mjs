import test from 'node:test';import assert from 'node:assert/strict';
import {instantiateSelected,duplicateInstance,replaceDefinitionMedia,exportDefinitionBundle,importDefinitionBundle,groupSceneInstances} from '../web/instance-manager-v1.mjs';
import {expandSceneInstances,assertGraph} from '../web/instance-graph-v1.mjs';
const image=(id='foto',file='photoA.jpg')=>({id,kind:'image',file,label:'Minha imagem',x:.5,y:.5,w:.4,h:.3,opacity:1,start:0,end:8,fit:'cover',loop:true,motion:'',motion_programs:[],rotation:0});
const init=()=>{const scene={id:'s1',duracao:8,objetos_midia:[image()],instances:[]};return {scene,project:{cenas:[scene]}}};
test('instance sourced from selected object keeps definition id canonical',()=>{
 const {project,scene}=init();const inst=instantiateSelected(project,scene,scene.objetos_midia[0]);
 assert.equal(project.instance_library.definitions[0].media.id,inst.ref);
 assertGraph(project.instance_library,scene.instances);
});
test('shared source replacement propagates to all instance leaves',()=>{
 const {project,scene}=init();const root=instantiateSelected(project,scene,scene.objetos_midia[0]);duplicateInstance(project,scene,root.id);
 replaceDefinitionMedia(project,root.ref,{file:'nova.jpg',label:'Novo recurso',x:.55,rotation:11});
 const leaves=expandSceneInstances(project.instance_library,scene.instances,{duration:8});
 assert.equal(leaves.length,2);assert(leaves.every(x=>x.file==='nova.jpg'&&x.rotation===11));
 assert.equal(project.instance_library.definitions.length,1);
});
test('invalid changes never mutate project',()=>{
 const {project,scene}=init();const root=instantiateSelected(project,scene,scene.objetos_midia[0]);const before=JSON.stringify(project);
 assert.throws(()=>replaceDefinitionMedia(project,root.ref,{opacity:2}));assert.equal(JSON.stringify(project),before);
 assert.throws(()=>replaceDefinitionMedia(project,root.ref,{file:'../../secret.jpg'}));assert.equal(JSON.stringify(project),before);
});
test('export/import group with linked assets and stable remapped ids',()=>{
 const {project,scene}=init();const r=instantiateSelected(project,scene,scene.objetos_midia[0]);duplicateInstance(project,scene,r.id);const grp=groupSceneInstances(project,scene);
 const exported=exportDefinitionBundle(project,grp.ref);
 assert.equal(exported.format,'rd-studio-element-1');assert.equal(exported.definitions.length,2);
 const dst=init();dst.project.instance_library=structuredClone(project.instance_library);const originalLen=dst.project.instance_library.definitions.length;
 const next=importDefinitionBundle(dst.project,dst.scene,exported);
 assert.equal(dst.project.instance_library.definitions.length,originalLen+2);
 assert.equal(expandSceneInstances(dst.project.instance_library,dst.scene.instances,{duration:8}).length,2);
 assert(next.ref!==grp.ref);
});
test('reference cycles or missing dependencies are rejected without mutation',()=>{
 const {project,scene}=init();const before=JSON.stringify(project);
 const bad={format:'rd-studio-element-1',root:'grp',definitions:[{id:'grp',kind:'group',children:[{id:'x',ref:'grp',transform:{matrix:[1,0,0,1,0,0]}}]}]};
 assert.throws(()=>importDefinitionBundle(project,scene,bad));assert.equal(JSON.stringify(project),before);
});
