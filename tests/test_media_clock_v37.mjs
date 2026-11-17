import assert from 'node:assert/strict';
import {test} from 'node:test';
import vm from 'node:vm';
import fs from 'node:fs';
const code=fs.readFileSync(new URL('../web_player/v3/media_layer.js',import.meta.url),'utf8');
function setup(){
 const events={};const v={paused:true,seeking:false,currentTime:0,duration:10,readyState:4,style:{},playbackRate:1,playCount:0,addEventListener(n,fn){events[n]=fn;},setAttribute(){},load(){},removeAttribute(){},play(){this.paused=false;this.playCount++;return Promise.resolve();},pause(){this.paused=true;}};
 const status={textContent:''},stage={style:{},append(){},getBoundingClientRect:()=>({width:600,height:800})};
 const w={addEventListener(){}},ctx={window:w,document:{getElementById:id=>id==='stageShell'?stage:status,createElement:()=>v},location:{pathname:'/player-v3/'}};vm.runInNewContext(code,ctx);return {m:w.StudioMedia,v,events,status};
}
const c=(loop=false)=>({video_clipe:{arquivo:'clip.mp4',inicio:0,repetir:loop}}),dims={width:720,height:1280};
test('actual clock, pause, resume and non-repeat ending',async()=>{const {m,v,events}=setup();m.scene(1,c(),dims,3,true,1.5);assert.equal(v.src,'/api/media/clip?file=clip.mp4');assert.equal(v.currentTime,3);assert.equal(v.playbackRate,1.5);assert.equal(v.paused,false);await new Promise(r=>setImmediate(r));m.tick(1,5,true,2);assert.equal(v.currentTime,5);assert.equal(v.playbackRate,2);m.tick(1,5,false,2);assert.equal(v.paused,true);m.tick(1,11,true,2);assert.equal(v.style.display,'none');m.seek(1,1);assert.equal(v.style.display,'block');assert.equal(v.currentTime,1);events.loadedmetadata();});
test('metadata uses latest requested time and loops',async()=>{const {m,v,events}=setup();v.readyState=0;v.duration=NaN;m.scene(2,c(true),dims,0,true,.75);m.tick(2,13,true,.75);assert.equal(v.playCount,0);v.readyState=4;v.duration=10;events.loadedmetadata();assert.equal(v.currentTime,3);assert.equal(v.paused,false);assert.equal(v.playbackRate,.75);await new Promise(r=>setImmediate(r));m.scene(3,{},dims,0,true,1);assert.equal(v.paused,true);assert.equal(v.style.display,'none');m.tick(2,7,true,1);assert.equal(v.style.display,'none');});
