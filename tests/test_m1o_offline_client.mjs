import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtempSync,writeFileSync,readFileSync,rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {pathToFileURL} from 'node:url';

function fixture(){
 const folder=mkdtempSync(join(tmpdir(),'m1o-browser-'));
 const source=readFileSync(new URL('../web/offline-render.mjs',import.meta.url),'utf8');
 writeFileSync(join(folder,'offline-render.mjs'),source);
 writeFileSync(join(folder,'browser-render.mjs'),`export function plan(p,d){const duration=d?d[0]:p.cenas[0].duracao;return {duration,fps:p.video.fps,width:p.video.width,height:p.video.height,entries:[{index:0,start:0,end:duration,nominal:duration,duration,scene:p.cenas[0]}]};}\nexport function atTime(e,t){return e[0];}\nexport async function prepareEntry(e,p,s,vs){return {...e,layers:[]};}\nexport async function paintOffline(ctx,canvas,e,t,settings,signal){globalThis.__painted.push(t);}\nexport function collectGILAudioEvents(){return [];}`);
 writeFileSync(join(folder,'gil-native.mjs'),'export function prepare() {return {};}'+'\n');
 return folder;
}
function reply(value,status=200){return {ok:status===200,status,json:async()=>value};}

test('Cliente M1O retoma quadro persistido e não depende do relógio real',async()=>{
 const folder=fixture(),original=globalThis.fetch;
 const requests=[];
 globalThis.__painted=[];
 globalThis.fetch=async(url,opts)=>{
  requests.push({url,opts});
  if(url.endsWith('/plan'))return reply({durations:[5/24]});
  if(url.endsWith('/start'))return reply({token:'1'.repeat(32),frames:5,next_frame:3,width:320,height:320,fps:24,resumed:true});
  if(url.includes('/frame?')){
   const i=Number(new URL(url,'http://localhost').searchParams.get('index'));
   return reply({next_frame:i+1,encoded_chunk:true,request_seconds:.02});
  }
  if(url.endsWith('/finish'))return reply({url:'/api/output/finished.mp4',file:'finished.mp4',bytes:1000,stats:{encoded_frames:5,fps:24}});
  throw Error('URL inesperada: '+url);
 };
 const canvas={width:0,height:0,getContext:()=>({}),toBlob:cb=>cb(new Blob([new Uint8Array([137,80,78,71])],{type:'image/png'}))};
 const project={video:{width:320,height:320,fps:24,draw_fps:12},cenas:[{duracao:5/24}]};
 try{
  const {exportOffline}=await import(pathToFileURL(join(folder,'offline-render.mjs')));
  const output=await exportOffline(project,{canvas,quality:'native'});
  assert.equal(output.frames,5);assert.equal(output.resumed,true);
  assert.deepEqual(globalThis.__painted.map(x=>Math.round(x*24)),[3,4]);
  assert.equal(requests.filter(x=>x.url.includes('/frame?')).length,2);
  assert.equal(output.url,'/api/output/finished.mp4');
 }finally{globalThis.fetch=original;rmSync(folder,{recursive:true,force:true});delete globalThis.__painted;}
});
