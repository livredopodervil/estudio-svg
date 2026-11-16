import assert from 'node:assert/strict';
import '../web/layers-v36.js';
const m=globalThis.StudioLayersV36;
const a={tipo:'foto',titulo:'A',imagem:{arquivo:'a.jpg',modo:'fundo'}},b={tipo:'cartoes',titulo:'B',imagem:{arquivo:'b.jpg',modo:'quadro'}};
assert.equal(m.config(a,'imagem').z,10);assert.equal(m.config(b,'imagem').z,30);
for(const c of [a,b]){assert(m.editRoles(c,['imagem'],'front'));assert.equal(m.sortedRoles(c).at(-1),'imagem');assert(m.editRoles(c,['imagem'],'back'));assert.equal(m.sortedRoles(c)[0],'imagem');assert(m.editRoles(c,['imagem'],'move',20,-12));assert.equal(c.camadas.imagem.dx,20);assert.equal(c.camadas.imagem.dy,-12);assert(m.editRoles(c,['imagem'],'hide'));assert.equal(c.camadas.imagem.oculta,true);assert(m.editRoles(c,['imagem'],'show'));assert.equal(c.camadas.imagem.oculta,false);assert(c.imagem.arquivo);}
assert.equal(m.editRoles({tipo:'cartoes'},['imagem'],'front'),false);
console.log('OK: camada imagem em fundo/quadro, ordem, movimento, ocultação, mídia preservada.');
