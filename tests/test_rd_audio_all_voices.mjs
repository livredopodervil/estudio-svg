import test from 'node:test';import assert from 'node:assert/strict';
import {normalizeCatalog,filterVoices,browserVoices} from '../web/rd-audio-all-voices.mjs';
test('catálogo multi-motor com idiomas, sem lista fixa',()=>{
 const d={count:4,voices:[{id:'piper:cadu',name:'Cadu',locale:'pt-BR',provider:'piper',available:true},
 {id:'kokoro:pf_dora',name:'pf_dora',locale:'pt-BR',provider:'kokoro',available:true},
 {id:'edge:fr-FR-DeniseNeural',name:'Denise',locale:'fr-FR',provider:'edge',available:true},
 {id:'edge:pt-BR-ThalitaNeural',name:'Thalita',locale:'pt-BR',provider:'edge',available:true}]};
 const c=normalizeCatalog(d);assert.equal(c.length,4);assert.equal(filterVoices(c,'fr-FR').length,1);
 assert.equal(filterVoices(c,'piper')[0].id,'piper:cadu');
});
test('vozes do navegador sinalizam indisponibilidade de exportação',()=>{
 const c=browserVoices({getVoices:()=>[{voiceURI:'local',name:'Voz Android',lang:'pt-BR'}]});
 assert.equal(c[0].exportable,false);assert.equal(c[0].id,'browser:local');
});
