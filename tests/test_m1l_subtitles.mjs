import test from 'node:test';
import assert from 'node:assert/strict';
import {subtitleState,subtitleSVG,drawSubtitle} from '../web/subtitle-frame.mjs';
import {CATALOG,CATALOG_FAMILIES,sourceFor,soundSamples} from '../web/roteiro-catalog-v04.mjs';
const scene=(text='Hoje começamos uma análise do arcabouço fiscal e seus impactos.')=>({duracao:10,audio:{voice_text:text,voice_delay:.25},legendas:{enabled:true,mode:'karaoke',effect:'rise',max_words:4,position:'bottom'}});
test('sem ativação não desenha legendas',()=>assert.equal(subtitleSVG({...scene(),legendas:{enabled:false}},1,10,960,540),''));
test('seek determinístico e segmentação de frases com realce',()=>{
 const s=scene(),a=subtitleState(s,2,10),b=subtitleState(s,2,10);
 assert.deepEqual(a,b);assert.ok(a.words.length<=4);assert.match(subtitleSVG(s,2,10,960,540),/<svg/);
 assert.match(subtitleSVG(s,2,10,960,540),/fill=/);
});
test('não mostrar antes do atraso ou fora da voz',()=>{
 const s=scene();assert.equal(subtitleState(s,.1,10),null);assert.equal(subtitleState(s,10,10),null);
});
test('tempos explícitos prevalecem e texto é escapado',()=>{
 const s=scene();s.legendas.cues=[{start:2,end:3,text:'A & B <texto>'}];
 assert.equal(subtitleState(s,1,10),null);
 assert.match(subtitleSVG(s,2.5,10,960,540),/A/);
 assert.match(subtitleSVG(s,2.5,10,960,540),/&amp;/);
 assert.doesNotMatch(subtitleSVG(s,2.5,10,960,540),/<texto>/);
});
test('modo palavra, animações e fonte cabem em quadros vertical e horizontal',()=>{
 for(const effect of ['fade','rise','pop','slide','typewriter','none'])for(const mode of ['karaoke','word','phrase']){
  const s=scene('Este é um texto muito longo para simular legendas muito longas em telas pequenas e retrato.');s.legendas={...s.legendas,mode,effect,max_words:9,font_scale:1.6};
  for(const [w,h] of [[960,540],[540,960]]){
   const svg=subtitleSVG(s,2,10,w,h);assert.match(svg,/<svg/);assert.ok(!svg.includes('NaN'));
   const calls=[];const fake=new Proxy({}, {get(_obj,k){if(k==='save'||k==='restore'||k==='fill'||k==='beginPath'||k==='roundRect'||k==='rect'||k==='translate'||k==='scale'||k==='fillText')return (...args)=>{calls.push([k,args]);};return undefined;},set(){return true;}});
   drawSubtitle(fake,s,2,10,w,h);assert.ok(calls.some(([name])=>name==='fillText'));
  }
 }
});
test('catálogo M1L expõe tipos e parâmetros sem multiplicar objetos',()=>{
 assert.equal(CATALOG_FAMILIES.length,43);
 assert.equal(CATALOG_FAMILIES.filter(x=>x.type==='title').length,1);
 assert.equal(CATALOG_FAMILIES.filter(x=>x.type==='geometry').length,24);
 assert.ok(CATALOG.length>400,'compatibilidade preservada');
 assert.match(sourceFor(CATALOG_FAMILIES.find(x=>x.type==='geometry'),{palette:'neon'}),/gil timeline/);
 assert.match(sourceFor(CATALOG_FAMILIES.find(x=>x.type==='title'),{label:'ANÁLISE',style:'cinema',entry:'typewriter'}),/gil timeline/);
 assert.equal(soundSamples({...CATALOG_FAMILIES.find(x=>x.type==='sound'),variant:3}).rate,22050);
 assert.throws(()=>soundSamples({...CATALOG_FAMILIES.find(x=>x.type==='sound'),variant:33}),/Variante/);
});
test('preview e exportação referenciam a mesma implementação de legendas',async()=>{
 const fs=await import('node:fs/promises');
 const preview=await fs.readFile(new URL('../web/app.js',import.meta.url),'utf8');
 const exportCode=await fs.readFile(new URL('../web/browser-render.mjs',import.meta.url),'utf8');
 const html=await fs.readFile(new URL('../web/index.html',import.meta.url),'utf8');
 assert.match(preview,/subtitleSVG\(/);
 assert.match(exportCode,/drawSubtitle\(ctx,e\.scene,subtitleTime,e\.duration/);
 assert.match(html,/id="rdSubtitleLayer"/);
});
