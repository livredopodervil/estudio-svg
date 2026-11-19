import test from 'node:test';
import assert from 'node:assert/strict';
import {instantiateSelected,duplicateInstance,groupSceneInstances,transformInstance,removeInstance} from '../web/instance-manager-v1.mjs';
import {expandSceneInstances} from '../web/instance-graph-v1.mjs';
const base=()=>({id:'foto1',kind:'image',file:'foto.jpg',x:.5,y:.5,w:.3,h:.4,opacity:1,start:0,end:7.5,motion:'',motion_programs:[]});
const make=()=>[{cenas:[],instance_library:undefined},{duracao:7.5,objetos_midia:[base()]}];
test('instanciar objeto existente preserva asset, criando referência reutilizável',()=>{
 const [project,scene]=make(),one=instantiateSelected(project,scene,base());
 assert.equal(one.ref,'d_foto1');assert.equal(project.instance_library.definitions.length,1);
 const two=instantiateSelected(project,scene,base());
 assert.equal(two.ref,one.ref);assert.equal(project.instance_library.definitions.length,1);
 assert.equal(expandSceneInstances(project.instance_library,scene.instances,{duration:7.5}).length,2);
});
test('duplicar e transformar mantém a definição e alteração reversível',()=>{
 const [project,scene]=make(),r=instantiateSelected(project,scene,base());
 const copy=duplicateInstance(project,scene,r.id);assert.notEqual(copy.id,r.id);
 const before=[...copy.transform.matrix];transformInstance(project,scene,copy.id,'rotate');
 assert.notDeepEqual(copy.transform.matrix,before);assert.equal(project.instance_library.definitions.length,1);
 assert.equal(removeInstance(scene,copy.id).id,copy.id);assert.equal(scene.instances.length,1);
});
test('agrupar instâncias cria group com arestas e mesma expansão visual',()=>{
 const [project,scene]=make();instantiateSelected(project,scene,base());instantiateSelected(project,scene,base());
 const prior=expandSceneInstances(project.instance_library,scene.instances,{duration:7.5});
 const root=groupSceneInstances(project,scene);
 assert.equal(project.instance_library.definitions.length,2);
 assert.equal(scene.instances.length,1);assert.equal(root.ref,'grupo1');
 const after=expandSceneInstances(project.instance_library,scene.instances,{duration:7.5});
 assert.equal(after.length,prior.length);
 after.forEach((item,i)=>assert.deepEqual(item.instance_matrix,prior[i].instance_matrix));
});
test('clipe com áudio e mudança singular são recusados',()=>{
 const [project,scene]=make();
 assert.throws(()=>instantiateSelected(project,scene,{...base(),kind:'video',audio_enabled:true}),/áudio/);
 const r=instantiateSelected(project,scene,base());
 assert.throws(()=>transformInstance(project,scene,r.id,'invalid'),/desconhecida/);
});
