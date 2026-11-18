import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const read = f => readFileSync(new URL('../'+f,import.meta.url),'utf8');
test('M1O captura quadro numerado em tempo virtual, sem MediaRecorder',()=>{
 const js=read('web/offline-render.mjs');
 assert.match(js,/next\s*\/\s*job\.fps/);
 assert.match(js,/paintOffline\(/);
 assert.match(js,/canvas\.toBlob\(/);
 assert.match(js,/api\/offline-export\/frame/);
 assert.doesNotMatch(js,/requestAnimationFrame\(|MediaRecorder\(/);
});
test('M1O espera SVG, GIL e decodificação de vídeo antes de desenhar',()=>{
 const render=read('web/browser-render.mjs');
 assert.match(render,/export async function paintOffline\(/);
 assert.match(render,/await exactSVG\(e\.base/);
 assert.match(render,/await exactSVG\(l\.slot/);
 assert.match(render,/await exactVideo\(l\.media/);
 assert.match(render,/drawSubtitle\(ctx,e\.scene,originalTime/);
});
test('M1O integrado na interface, rotas explícitas e CLI Python preservada',()=>{
 assert.match(read('web/index.html'),/id="offlineExport"/);
 assert.match(read('web/index.html'),/id="offlineQuality"/);
 assert.match(read('web/app.js'),/import\('\/offline-render\.mjs'\)/);
 assert.match(read('app.py'),/OfflineExport/);
 assert.match(read('app.py'),/route=='\/api\/offline-export\/start'/);
 assert.match(read('app.py'),/route=='\/api\/offline-export\/frame'/);
 assert.match(read('app.py'),/\/offline-render\.mjs/);
 assert.match(read('app.py'),/ThreadingHTTPServer/);
});
