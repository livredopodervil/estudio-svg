import test from 'node:test';
import assert from 'node:assert/strict';
import {TITLE_STYLES,titleStyle,renderTitle,wrapTitle} from '../web/title-gallery.mjs';
function canvas(){
 const ops=[],ctx={measureText:s=>({width:String(s).length*18}),clearRect(...a){ops.push(['clear',...a]);},save(){ops.push(['save']);},restore(){ops.push(['restore']);},scale(...a){ops.push(['scale',...a]);},fillRect(...a){ops.push(['rect',...a]);},strokeRect(...a){ops.push(['strokeRect',...a]);},fillText(...a){ops.push(['text',...a]);}};
 return {width:1280,height:720,getContext:()=>ctx,ops};
}
test('eight distinct presets and supported GIL entrance names',()=>{
 assert.equal(TITLE_STYLES.length,8);
 assert.equal(new Set(TITLE_STYLES.map(x=>x.id)).size,8);
 for(const v of TITLE_STYLES)assert.ok(['fade','zoom-in','enter-right','enter-bottom'].includes(v.motion));
 assert.equal(titleStyle('bad').id,'editorial');
});
test('all title templates paint real geometry or glyphs into a transparent canvas',()=>{
 for(const v of TITLE_STYLES){const c=canvas();renderTitle(c,{text:'TEXTO TESTE',subtitle:'LEGENDA',style:v.id});
 assert.equal(c.ops[0][0],'clear',v.id);assert.ok(c.ops.some(x=>x[0]==='text'&&x[1].includes('TEXTO')),v.id);
 assert.ok(!c.ops.some(x=>x[0]==='text'&&String(x[1]).includes('undefined')),v.id);
 }
});
test('title wrapper bounds output and respects line budget',()=>{
 const c=canvas().getContext('2d');
 assert.deepEqual(wrapTitle(c,'um dois tres quatro',140,3),['um dois','tres','quatro']);
 assert.equal(wrapTitle(c,'a '.repeat(50),50,2).length,2);
});
