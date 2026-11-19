import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {createTitleGIL} from '../web/title-gil.mjs';
const read=n=>fs.readFileSync(new URL('../web/'+n,import.meta.url),'utf8');
const metric=(s,size)=>{let width=0;for(const c of s)width+=c===' '?size*.20:size*.62;for(let i=0;i<s.length-1;i++)if(s.slice(i,i+2)==='AV')width-=size*.16;return width;};
const position=(line)=>JSON.parse(line.slice(line.indexOf('{'))).x;

test('M1R2 kerning: prefix measure respects A-V pair',()=>{
 const source=createTitleGIL({text:'AVA',duration:6,entry:'none',exit:'none',measureText:metric});
 const objs=source.split('\n').filter(s=>s.startsWith('object letter_'));
 assert.equal(objs.length,3);
 const p=objs.map(position);
 const nominal=metric('A',70)/90;
 assert.ok(p[1]-p[0]<nominal,'adjacent AV pair must be kerning-adjusted');
});
test('M1R2 word mode preserves full word as single shaped SVG text object',()=>{
 const source=createTitleGIL({text:'AVATAR VITAL',textMode:'words',duration:6,entry:'cascade',measureText:metric});
 assert.match(source,/"text":"AVATAR"/);
 const objs=source.split('\n').filter(s=>s.startsWith('object letter_'));
 assert.equal(objs.length,2);
});
test('M1R2 rejects unsupported typographic segment modes',()=>{
 assert.throws(()=>createTitleGIL({text:'TESTE',textMode:'bogus'}),/Agrupamento/);
});
test('M1R2 insertion enumerates actual existing tool handlers and no invented LaTeX converter',()=>{
 const e=read('scene-object-editor.mjs');
 for(const id of ['image','video','svg','title','gil','audio','scene3d'])assert.ok(e.includes(`['${id}'`),id);
 assert.match(e,/\$\('openLibrary'\)\?\.click\(\)/);
 assert.match(e,/textContent='LaTeX: adaptador MathJax/);
 assert.doesNotMatch(e,/\$\('objectExamples'\)\.value='orbit'[^;]*$/);
});
test('M1R2 inspector is moved out of playback stack and quick movements visible',()=>{
 const layout=read('studio-layout-v1.js'),editor=read('scene-object-editor.mjs');
 assert.match(layout,/M1R2_INSPECTOR_AFTER_PLAYER/);
 assert.match(layout,/player\.after\(inspector\)/);
 assert.match(editor,/rdQuickMotion/);
 assert.match(editor,/Ken Burns/);
});
