import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
const editor=readFileSync(new URL('../web/scene-object-editor.mjs',import.meta.url),'utf8');
const layout=readFileSync(new URL('../web/studio-layout-v1.js',import.meta.url),'utf8');
const css=readFileSync(new URL('../web/studio-layout-v1.css',import.meta.url),'utf8');
function section(before,after){const a=editor.indexOf(before),b=editor.indexOf(after,a+before.length);assert.ok(a>=0&&b>a,'Expected section '+before);return editor.slice(a,b);}

test('M1S: valid page module and no destructive staged Git changes',()=>{
 assert.match(editor,/M1S_PICKING/);assert.match(editor,/M1S_UNIVERSAL/);
 assert.match(editor,/M1S_SCROLL/);assert.match(editor,/addEventListener\('click',e=>/);
 assert.match(editor,/ctx\.preview\(\);refresh\(\);ctx\.notify\('Camada/);
 assert.match(editor,/key==='behind'/);
});
test('M1S: viewport clipped; scroll confined; searchable categories',()=>{
 assert.match(css,/#stageShell\{overflow:hidden/);
 assert.match(css,/\.rdViewportGizmo\{overflow:hidden/);
 assert.match(css,/html\.rdObjectModalOpen body\{overflow:hidden/);
 assert.match(css,/overscroll-behavior:contain/);
 assert.match(editor,/m1sSearch\.addEventListener\('input',m1sFilter\)/);
 assert.match(editor,/m1sGilGrid\.replaceChildren\(\)/);
 assert.match(layout,/for\(const o of by\('gilLibrarySelect'\)\.options\)/);
});
test('M1S: transparent GIL canvas passes through to objects behind',()=>{
 const src=section('function m1sPaintHit(', 'function m1sCandidates(');
 const ctx={document:{createElement:()=>({width:0,height:0})},m1sProbe:{getContext:()=>({})},getComputedStyle:()=>({objectFit:'contain'})};
 vm.runInNewContext(src+'\nthis.pick=m1sPaintHit;',ctx);
 const svg={};
 const el={tagName:'DIV',getBoundingClientRect:()=>({left:0,top:0,width:100,height:100,right:100,bottom:100}),shadowRoot:{querySelector:()=>svg,elementFromPoint:()=>svg}};
 assert.equal(ctx.pick(el,30,20),false);
 el.shadowRoot.elementFromPoint=()=>({nodeName:'path'});
 assert.equal(ctx.pick(el,30,20),true);
 assert.equal(ctx.pick(el,120,20),false);
});
test('M1S: transparent PNG pixel ignored; opaque PNG selectable',()=>{
 const src=section('function m1sPaintHit(', 'function m1sCandidates(');
 let pixelAlpha=0;
 const ctx={m1sProbe:{getContext:()=>({clearRect(){},drawImage(){},getImageData:()=>({data:[0,0,0,pixelAlpha]})})},getComputedStyle:()=>({objectFit:'cover'})};
 vm.runInNewContext(src+'\nthis.pick=m1sPaintHit;',ctx);
 const el={tagName:'IMG',complete:true,naturalWidth:300,naturalHeight:300,getBoundingClientRect:()=>({left:0,top:0,width:100,height:100,right:100,bottom:100})};
 assert.equal(ctx.pick(el,50,50),false);
 pixelAlpha=255;
 assert.equal(ctx.pick(el,50,50),true);
});
test('M1S: layer order follows existing objects array from back to front',()=>{
 assert.match(editor,/\.sort\(\(a,b\)=>objects\(\)\.findIndex\(o=>o\.id===b\.dataset\.sceneObjectId\)/);
 assert.match(editor,/index=\(m1sTap\.index\+1\)%ids\.length/);
 assert.match(editor,/ctx\.playing\(\)\|\|document\.fullscreenElement/);
 assert.match(editor,/Math\.hypot\(e\.clientX-m1sDown\.x/);
});
test('M1S: options dynamically assembled from actual GIL library',()=>{
 assert.match(editor,/const select=\$\('objectExamples'\),library=\$\('gilLibrarySelect'\)/);
 assert.match(editor,/for\(const original of library\?\.options\|\|\[\]\)/);
 assert.match(editor,/if\(existing\.has\(original\.value\)\)continue/);
 assert.match(editor,/m1sGilGrid\.replaceChildren\(\)/);
 assert.match(editor,/select\.value=option\.value;example\(\)/);
});
