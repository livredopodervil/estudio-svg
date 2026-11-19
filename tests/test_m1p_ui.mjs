import test from 'node:test';
import assert from 'node:assert/strict';
import {gilTextObjects,changeGilText,applySubtitleStyleAll} from '../web/studio-m1p.mjs';

test('GIL title edits preserve other objects, source syntax lines',()=>{
 const src='gil timeline 0.1 {\nobject heading caption - {"text":"Olá","x":1}\nobject cam camera - {}\n}';
 assert.deepEqual(gilTextObjects(src).map(x=>x.text),['Olá']);
 const result=changeGilText(src,1,'Título novo');
 assert.match(result,/"text":"Título novo"/);
 assert.match(result,/object cam camera - \{\}/);
 assert.throws(()=>changeGilText(src,2,'Invalid'),/texto/);
});
test('subtitle bulk settings preserve per-scene cue times and texts',()=>{
 const p={cenas:[{legendas:{enabled:true,mode:'karaoke',effect:'slide',max_words:4,text_color:'#ff0000',font_scale:1.2,cues:[{start:0,end:1,text:'A'}]}},{legendas:{mode:'frase',cues:[{start:2,end:3,text:'B'}]}},{legendas:{cues:[]}}]};
 assert.equal(applySubtitleStyleAll(p,0),2);
 assert.equal(p.cenas[1].legendas.mode,'karaoke');
 assert.equal(p.cenas[1].legendas.effect,'slide');
 assert.equal(p.cenas[1].legendas.text_color,'#ff0000');
 assert.equal(p.cenas[1].legendas.font_scale,1.2);
 assert.deepEqual(p.cenas[1].legendas.cues,[{start:2,end:3,text:'B'}]);
 assert.equal(p.cenas[2].legendas.enabled,true);
});
