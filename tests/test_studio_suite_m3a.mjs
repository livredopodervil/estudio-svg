import test from 'node:test';
import assert from 'node:assert/strict';
import {checkedStatus,SERVICE_IDS} from '../web/studio-suite-m3a.mjs';
const sample={schema:1,read_only:true,ports:{admin:8885,preview:8886},services:[{id:'admin',label:'RD Studio',state:'online',detail:'main · 8e8554f'}]};
test('contract validates local ports and fixed service IDs',()=>{
  assert.equal(checkedStatus(sample).ports.admin,8885);
  assert.equal(checkedStatus({...sample,ports:{admin:'http://evil',preview:0}}).ports.admin,null);
  assert.ok(SERVICE_IDS.includes('audio'));
});
test('rejects duplicate or unknown service',()=>{
  assert.throws(()=>checkedStatus({...sample,services:[...sample.services,...sample.services]}));
  assert.throws(()=>checkedStatus({...sample,services:[{id:'publish',label:'!',state:'ok',detail:''}]}));
  assert.throws(()=>checkedStatus({...sample,read_only:false}));
});
test('does not pass through custom HTML in fields',()=>{
  const data=checkedStatus({...sample,services:[{id:'admin',label:'<img src=x>',state:'online',detail:'x'.repeat(900)}]});
  assert.equal(data.services[0].label,'<img src=x>');
  assert.equal(data.services[0].detail.length,300);
  // Actual renderer uses textContent, never innerHTML.
});
