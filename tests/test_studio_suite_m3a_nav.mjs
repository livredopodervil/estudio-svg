import test from 'node:test';
import assert from 'node:assert/strict';
import {placeSuiteButtonInComposeNav} from '../web/studio-suite-m3a.mjs';
function fixture({visible=true}={}) {
  const legacy={name:'workspaceTools'};
  const button={id:'openSuiteM3A', parentElement:legacy};
  const nav={name:'rdComposeNav', called:0, prepend(child){this.called++;child.parentElement=this;}};
  const document={getElementById:id=>id==='openSuiteM3A'?button:null,
    querySelector:selector=> selector==='.rdStudioUnified .rdComposeNav' && visible?nav:null};
  return {legacy,button,nav,document};
}
test('moves original Suite button into unified composition navbar, without cloning',()=>{
  const f=fixture();
  assert.equal(placeSuiteButtonInComposeNav(f.document),true);
  assert.equal(f.button.parentElement,f.nav);
  assert.equal(f.nav.called,1);
});
test('idempotent on repeated mounting',()=>{
  const f=fixture();
  placeSuiteButtonInComposeNav(f.document);
  placeSuiteButtonInComposeNav(f.document);
  assert.equal(f.nav.called,1);
});
test('leaves original button in legacy toolbar if unified navigation is absent',()=>{
  const f=fixture({visible:false});
  assert.equal(placeSuiteButtonInComposeNav(f.document),false);
  assert.equal(f.button.parentElement,f.legacy);
});
test('does not act if original button is not available',()=>{
  const f=fixture();f.document.getElementById=()=>null;
  assert.equal(placeSuiteButtonInComposeNav(f.document),false);
});
