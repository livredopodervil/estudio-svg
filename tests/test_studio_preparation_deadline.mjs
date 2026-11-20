import test from 'node:test';
import assert from 'node:assert/strict';
import {withDeadline} from '../web/studio-preparation-deadline.mjs';
test('retorna o valor quando a preparação completa',async()=>{
 assert.equal(await withDeadline('SVG',async()=>42,{ms:100}),42);
});
test('rejeita requisição presa e cancela operação interna',async()=>{
 let aborted=false;
 await assert.rejects(withDeadline('Cena 2',signal=>new Promise(()=>{signal.addEventListener('abort',()=>{aborted=true;});}),{ms:25}),/Cena 2: excedeu/);
 assert.equal(aborted,true);
});
test('propaga cancelamento do usuário',async()=>{
 const c=new AbortController();const task=withDeadline('SVG',()=>new Promise(()=>{}),{signal:c.signal,ms:200});
 c.abort();await assert.rejects(task,/cancelada/);
});
test('rejeita sucesso anterior seguido de operação cancelada',async()=>{
 const c=new AbortController();c.abort();await assert.rejects(withDeadline('SVG',async()=>1,{signal:c.signal,ms:100}),/cancelada/);
});
