import test from 'node:test';import assert from 'node:assert/strict';
import {parseRoteiro,compileRoteiro} from '../web/roteiro-v02.mjs';
import {STYLES,createStyleBase,createStyleScript} from '../web/roteiro-styles.mjs';
import {pathToFileURL} from 'node:url';
import {resolve,join} from 'node:path';
const root=process.env.RD_GIL_ROOT;
let gil;
if(root){try{const m=await import(pathToFileURL(join(resolve(root),'src/model.mjs')).href);const l=await import(pathToFileURL(join(resolve(root),'src/language.mjs')).href);gil={compile:m.compile,serialize:l.serialize};}catch{}}
const supportsRuntime=Boolean(gil);
test('twelve distinct styles compile into GIL without audio cues',{skip:!supportsRuntime},()=>{
 const signatures=new Set();for(const s of STYLES){const r=compileRoteiro(createStyleBase({style:s.id}),createStyleScript({style:s.id}),gil);assert.equal(r.doc.cues.length,0);assert.ok(r.doc.tracks.length>=4);assert.equal(r.events.length,7);signatures.add(r.source);}assert.equal(signatures.size,12);
});
test('reject overlap and invented targets without changing the base',{skip:!supportsRuntime},()=>{
 const base=createStyleBase({});const script='roteiro 0.2 {\n paralelo {\n entrada titulo esquerda durante 2s\n saida titulo direita durante 2s\n }\n}';
 assert.throws(()=>compileRoteiro(base,script,gil),/conflito temporal/);
 assert.throws(()=>compileRoteiro(base,'roteiro 0.2 {\n aparecer inexistente durante 1s\n}',gil),/inexistente/);
 assert.equal(gil.compile(base).spec.tracks.length,0);
});
test('Roteiro 0.1 remains parseable; no arbitrary JavaScript evaluation',()=>{
 assert.equal(parseRoteiro('roteiro 0.1 {\n esperar 1s\n}').root.children.length,1);
 assert.throws(()=>parseRoteiro('roteiro 0.2 {\n eval process.exit()\n}'),/Diretiva desconhecida/);
});
