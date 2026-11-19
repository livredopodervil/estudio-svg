import test from 'node:test';
import assert from 'node:assert/strict';
import {IDENTITY,affineMultiply,affineFrom,affineInverse,affinePoint,pixelMatrix,assertGraph,expandSceneInstances,pickGraphLeaf,renderableLayers} from '../web/instance-graph-v1.mjs';
const img={id:'photo',kind:'image',file:'image.jpg',label:'Photo',x:.5,y:.5,w:.28,h:.3,start:0,end:8,opacity:1,loop:true,fit:'cover',motion:'',motion_programs:[]};
const group={id:'pair',kind:'group',children:[{id:'left',ref:'photo',transform:{matrix:[1,0,0,1,-.22,0]}},{id:'right',ref:'photo',transform:{matrix:[1,0,0,1,.22,0]}}]};
const library={format:'rd-instance-library-1',definitions:[{id:'photo',kind:'media',media:img},group]};
const root={id:'r1',ref:'pair',transform:{matrix:IDENTITY},start:0,end:8};
const approx=(a,b)=>assert.ok(Math.abs(a-b)<1e-9,`${a} != ${b}`);
test('composições afins e inversão, incluindo shear e pivô',()=>{
 const a=affineFrom({x:.2,y:-.1,sx:.75,sy:1.2,rotation:22,shear:.35,pivotX:.5,pivotY:.5});
 const b=affineFrom({x:-.13,y:.09,rotation:-14,sx:1.4});
 const m=affineMultiply(a,b),q=[.31,.69],p=affinePoint(m,...q),inverse=affinePoint(affineInverse(m),...p);
 inverse.forEach((v,i)=>approx(v,q[i]));
 assert.equal(pixelMatrix(IDENTITY,1080,1920)[0],1);
 assert.deepEqual(pixelMatrix([1,0,0,1,.2,.3],1080,1920).slice(4),[216,576]);
});
test('definição de mídia compartilhada por duas instâncias, IDs estáveis',()=>{
 const leaves=expandSceneInstances(library,[root],{duration:8});
 assert.equal(leaves.length,2);assert.equal(leaves[0].file,leaves[1].file);
 assert.equal(leaves[0].instance_definition,'photo');
 assert.notEqual(leaves[0].id,leaves[1].id);
 assert.deepEqual(leaves.map(o=>o.instance_matrix[4]),[-.22,.22]);
 assert.deepEqual(leaves.map(o=>o.instance_path),['r1/left','r1/right']);
 assert.deepEqual(leaves,expandSceneInstances(library,[root],{duration:8}));
});
test('grupos aninhados preservam a ordem de matriz e opacidade',()=>{
 const lib={format:'rd-instance-library-1',definitions:[...library.definitions,{id:'outer',kind:'group',children:[{id:'nest',ref:'pair',transform:{matrix:[2,0,0,2,-.4,-.5]},opacity:.5}]}]};
 const leaves=expandSceneInstances(lib,[{id:'one',ref:'outer',transform:{matrix:[1,0,0,1,.1,.1]},opacity:.7}],{duration:8});
 assert.equal(leaves.length,2);approx(leaves[0].opacity,.35);
 approx(leaves[0].instance_matrix[4],-.74);approx(leaves[1].instance_matrix[4],.14);
});
test('picking usa inversão afim e pode atravessar píxeis transparentes',()=>{
 const leaves=expandSceneInstances(library,[root],{duration:8});
 assert.equal(pickGraphLeaf(leaves,.28,.5)?.instance_path,'r1/left');
 assert.equal(pickGraphLeaf(leaves,.72,.5)?.instance_path,'r1/right');
 assert.equal(pickGraphLeaf(leaves,.72,.5,()=>false),null);
 assert.equal(pickGraphLeaf(leaves,.01,.02),null);
});
test('erros de ciclo, aresta repetida, ref ausente, matriz singular e explosão recusados',()=>{
 const cyc={format:'rd-instance-library-1',definitions:[{id:'a',kind:'group',children:[{id:'b',ref:'b'}]},{id:'b',kind:'group',children:[{id:'a',ref:'a'}]}]};
 assert.throws(()=>assertGraph(cyc,[]),/Ciclo/);
 const bad={format:'rd-instance-library-1',definitions:[{id:'x',kind:'group',children:[{id:'a',ref:'missing'}]}]};
 assert.throws(()=>assertGraph(bad,[]),/ausente/);
 assert.throws(()=>assertGraph(library,[{...root,transform:{matrix:[0,0,0,0,0,0]}}]),/singular/);
 assert.throws(()=>assertGraph(library,Array.from({length:33},(_,i)=>({...root,id:'x'+i}))),/inválidas/);
 const explode={format:'rd-instance-library-1',definitions:[{id:'leaf',kind:'media',media:{...img,id:'leaf'}},{id:'g',kind:'group',children:Array.from({length:20},(_,i)=>({id:'e'+i,ref:'leaf'}))}]};
 assert.throws(()=>assertGraph(explode,Array.from({length:7},(_,i)=>({id:'r'+i,ref:'g'}))),/128/);
});
test('compatibilidade: projetos sem instâncias não alterados',()=>{
 const original={id:'original',kind:'image'};
 assert.deepEqual(renderableLayers({}, {objetos_midia:[original]}),[original]);
 const scene={duracao:8,objetos_midia:[original],instances:[root]};
 assert.equal(renderableLayers({instance_library:library},scene).length,3);
});
