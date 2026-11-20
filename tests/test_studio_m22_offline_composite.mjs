import {test} from 'node:test';
import assert from 'node:assert/strict';
import {paintOffline} from '../web/browser-render.mjs';
test('composição offline desenha WebGL primeiro e SVG em seguida', async()=>{
  const rendered=[];
  const frame={videoWidth:720,videoHeight:1280};
  const base={id:'svg-background'};
  globalThis.window={StudioSpatialSeedViewport:{async frameAtOffline(s,t,aspect){
    assert.equal(t,0); assert.equal(aspect,720/1280); return frame;
  }}};
  try{
    const ctx={globalAlpha:1,fillRect(){},drawImage(im){rendered.push(im);}};
    const e={scene:{spatialseed_viewport:{enabled:true},legendas:{enabled:false}},
      base:{at:0,image:base},nominal:1,duration:1,layers:[]};
    await paintOffline(ctx,{width:720,height:1280},e,0,{baseFPS:8,gilFPS:10},{aborted:false});
    assert.deepEqual(rendered,[frame,base]);
  }finally{delete globalThis.window;}
});
test('falha explicitamente quando falta um quadro WebGL', async()=>{
  globalThis.window={StudioSpatialSeedViewport:{async frameAtOffline(){return null;}}};
  try{
    const ctx={fillRect(){},drawImage(){}};
    const e={scene:{spatialseed_viewport:{enabled:true},legendas:{enabled:false}},
      base:{at:0,image:{}},nominal:1,duration:1,layers:[]};
    await assert.rejects(paintOffline(ctx,{width:720,height:1280},e,0,{baseFPS:8,gilFPS:10},{aborted:false}),/quadro WebGL offline inválido/i);
  }finally{delete globalThis.window;}
});
