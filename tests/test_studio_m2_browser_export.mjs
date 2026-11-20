import test from 'node:test';
import assert from 'node:assert/strict';
import {plan} from '../web/browser-render.mjs';
const project={video:{width:720,height:1280,fps:24,draw_fps:8},cenas:[{id:'test',duracao:2,objetos_midia:[],spatialseed_viewport:{enabled:true,source:'',camera_keys:[]}}]};
test('offline continua bloqueada sem provedor WebGL',()=>{
 assert.throws(()=>plan(project),/offline/);
});
test('offline exige provedor real antes de permitir WebGL',()=>{
 globalThis.window={StudioSpatialSeedViewport:{frameAtOffline(){}}};
 try{assert.equal(plan(project).duration,2);}finally{delete globalThis.window;}
});
test('exportação pelo navegador pode planejar cena WebGL',()=>{
 const result=plan(project,null,{allowWebGL:true});
 assert.equal(result.duration,2);assert.equal(result.width,720);assert.equal(result.height,1280);
});
