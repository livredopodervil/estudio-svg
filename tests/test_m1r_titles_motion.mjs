import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import {dirname,resolve} from 'node:path';
const base=resolve(dirname(fileURLToPath(import.meta.url)),'..');
const source=file=>readFileSync(resolve(base,file),'utf8');
const title=await import('../web/title-gil.mjs');
const sourceFor=(t,w,h)=>title.createTitleGIL({text:t,subtitle:'SEGURANÇA',duration:8,width:w,height:h});

test('M1R-1 title on portrait stage and safe subtitle zone',()=>{
 const src=sourceFor('VIAGEM SEGURA COM CRIANÇAS',1080,1920);
 assert.match(src,/"width":1080,"height":1920/);
 const lines=src.split('\n');
 const objs=lines.filter(x=>/^object letter_/.test(x));
 assert.ok(objs.length>20);
 for(const line of objs){const p=JSON.parse(line.slice(line.indexOf('{')));assert.ok(Math.abs(p.x)<2.26,`X fora de 9:16: ${p.x}`);assert.ok(p.y<=4&&p.y>=.6,`Texto fora da zona superior: ${p.y}`);}
});
test('M1R-1 landscape preserves stage and accepts legacy text',()=>{
 const src=sourceFor('TÍTULO',1280,720);assert.match(src,/"width":1280,"height":720/);
});
test('M1R-1 rejects excessive portrait title rather than truncating silently',()=>{
 assert.throws(()=>sourceFor('PALAVRAS LONGAS '.repeat(30),1080,1920),/Título longo|limite|Título/);
});

test('M1R-1 motion generator reuses only canonical GIL media group',async()=>{
 const sourceCode=source('web/scene-objects.mjs');
 const start=sourceCode.indexOf('export function motionSource(');
 const end=sourceCode.indexOf('export function motionProgram(',start);
 assert.ok(start>0&&end>start);
 const fnCode=sourceCode.slice(start,end);
 const path=new URL('data:text/javascript;base64,'+Buffer.from(fnCode).toString('base64'));
 const {motionSource}=await import(path.href);
 for(const name of ['ken-burns','pan-left','pan-right','parallax','push-in','pull-out','pop','bounce','tilt-in','swing','wipe-in','shrink-away','drift-up','drift-down','orbit-soft','stagger-in','stagger-out']){
  const gil=motionSource(name,8);
  assert.match(gil,/gil timeline 0\.1/);assert.match(gil,/object media g - \{\}/);
  assert.ok(gil.includes('animate media '));
  const tracks=[...gil.matchAll(/^animate media (\w+) (\{.*\})$/gm)];
  assert.ok(tracks.length>0,name);
  for(const [,prop,payload] of tracks){assert.ok(['x','y','sx','sy','rz','opacity'].includes(prop),name);const v=JSON.parse(payload);assert.ok(v.keys.every(([t,val])=>Number.isFinite(t)&&Number.isFinite(val)&&t>=0&&t<=8));}
 }
});
