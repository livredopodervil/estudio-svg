import test from 'node:test';import assert from 'node:assert/strict';
import {TITLE_ENTRIES,TITLE_EXITS,createTitleGIL} from '../web/title-gil.mjs';
import {existsSync} from 'node:fs';
for(const [mode] of TITLE_ENTRIES)test(`GIL por grafema ${mode}`,()=>{
 const source=createTitleGIL({text:'Árvore e ciência 🌍',subtitle:'ESTÚDIO',entry:mode,exit:'fade',duration:7});
 assert.match(source,/gil timeline 0\.1/);assert.match(source,/resource glyph_res_\d+ text/);
 assert.match(source,/animate letter_\d+ opacity/);assert.ok(source.includes('🌍'));
 assert.ok(source.split('\n').filter(l=>l.startsWith('object letter_')).length>5);
});
test('limites de fontes e edição de texto arbitrário',()=>{
 assert.throws(()=>createTitleGIL({text:'x'.repeat(111)}));assert.throws(()=>createTitleGIL({text:'test',entry:'inexistente'}));
 for(const [exit] of TITLE_EXITS)assert.match(createTitleGIL({text:'Ção',exit}),/object letter_/);
});
test('compilador GIL nativo e renderizador compartilham semântica por quadro',{skip:!existsSync(new URL('../web/gil-runtime/src/model.mjs',import.meta.url))},async()=>{
 const {compile}=await import('../web/gil-runtime/src/model.mjs'),{Timeline}=await import('../web/gil-runtime/src/timeline.mjs'),{renderSVG}=await import('../web/gil-runtime/src/render-svg.mjs');
 for(const [entry] of TITLE_ENTRIES){const source=createTitleGIL({text:'TÍTULO BRASIL + 🌍',subtitle:'Legendas com acento',entry,duration:8}),doc=compile(source),timeline=new Timeline(doc);
  assert.ok(doc.nodes.length>10);for(const t of [0,.6,3,7.8,8]){const frame=renderSVG(timeline.sample(t));assert.equal(frame.missing.length,0);if(t===3)assert.match(frame.svg,/<text/);}}
});
