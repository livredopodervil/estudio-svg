import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
const context={};context.window=context;
vm.runInNewContext(readFileSync(new URL('../web/edit-history.js',import.meta.url),'utf8'),context);
const History=context.StudioDocumentHistory;
test('history restores scene duration and independent object insertions',()=>{
 const p={cenas:[{duracao:7,objetos_midia:[]}]},h=new History();h.reset(p);
 p.cenas[0].duracao=11;h.record(p);
 p.cenas[0].objetos_midia.push({id:'obj1'});h.record(p);
 assert.equal(h.undo(p),true);assert.equal(p.cenas[0].objetos_midia.length,0);assert.equal(p.cenas[0].duracao,11);
 assert.equal(h.undo(p),true);assert.equal(p.cenas[0].duracao,7);
 assert.equal(h.redo(p),true);assert.equal(p.cenas[0].duracao,11);
 assert.equal(h.redo(p),true);assert.equal(p.cenas[0].objetos_midia.length,1);
 assert.equal(h.canRedo,false);
});
test('new change after undo clears redo; reset prevents crossing projects',()=>{
 const h=new History(4),p={cenas:[{duracao:1}]};h.reset(p);
 p.cenas[0].duracao=2;h.record(p);h.undo(p);p.cenas[0].duracao=3;h.record(p);
 assert.equal(h.canRedo,false);assert.equal(h.undo(p),true);assert.equal(p.cenas[0].duracao,1);
 const q={cenas:[{duracao:23}]};h.reset(q);assert.equal(h.undo(q),false);assert.equal(h.undo(p),false);
});
test('coalescing repeated field edits and bounded history',()=>{
 const h=new History(3),p={v:0};h.reset(p);for(let i=1;i<=9;i++){p.v=i;h.record(p,'duration');}
 assert.equal(h.past.length,1);h.undo(p);assert.equal(p.v,0);
 for(let i=1;i<=10;i++){p.v=i;h.record(p);}assert.equal(h.past.length,3);
});
test('never silently undoes a change not recorded by editor',()=>{
 const h=new History(),p={x:1};h.reset(p);p.x=2;assert.equal(h.undo(p),false);assert.equal(p.x,2);
});
