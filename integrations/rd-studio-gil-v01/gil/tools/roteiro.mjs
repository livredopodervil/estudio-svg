#!/usr/bin/env node
// CLI adapter; compiler is shared with the browser. Autor: Rogério Duarte; assistência OpenAI.
import {readFile,writeFile} from 'node:fs/promises';
import {compileRoteiro} from '../src/roteiro.mjs';
import {compile} from '../src/model.mjs';
import {serialize} from '../src/language.mjs';
try {
 const args=process.argv.slice(2);
 if(args.length!==3)throw Error('Uso: node tools/roteiro.mjs BASE.gil ROTEIRO.txt SAIDA.gil');
 const [base,script,out]=args;
 const r=compileRoteiro(await readFile(base,'utf8'),await readFile(script,'utf8'),{compile,serialize});
 await writeFile(out,r.source,{flag:'wx'});
 console.log(JSON.stringify({objects:r.doc.nodes.length,tracks:r.doc.tracks.length,cues:r.doc.cues.length,events:r.events},null,2));
} catch(e){console.error(e.message);process.exitCode=1;}
