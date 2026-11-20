import test from 'node:test';
import assert from 'node:assert/strict';
import {collectNativeActions,collectNativeFields} from '../web/studio-spatialseed-panel.mjs';
function element({id='',title='',name='',type='text',tagName='INPUT',value='',hidden=false,disabled=false}={}) {
 return {id,title,name,type,tagName,value,hidden,disabled,textContent:title,
  getAttribute(key){return key==='aria-label'?null:key==='title'?title:null;},
  closest(){return null;},labels:[]};
}
test('menus originais são coletados sem duplicar renderizador',()=>{
 const button=element({id:'create',title:'Criar esfera',tagName:'BUTTON'});
 const doc={querySelectorAll(){return [button];}};
 const items=collectNativeActions(doc);
 assert.equal(items.length,1);assert.equal(items[0].element,button);
 assert.equal(items[0].label,'Criar esfera');
});
test('campos originais mantêm a identidade e excluem credenciais',()=>{
 const x=element({id:'position-x',title:'Posição X',type:'number',value:'1.5'});
 const secret=element({id:'secret-token',title:'Credencial',type:'text'});
 const doc={querySelectorAll(){return [x,secret];}};
 const items=collectNativeFields(doc);
 assert.equal(items.length,1);assert.equal(items[0].element,x);
});
test('limita a enumeração de comandos',()=>{
 const arr=Array.from({length:220},(_,i)=>element({id:'tool-'+i,title:'Tool '+i,tagName:'BUTTON'}));
 assert.equal(collectNativeActions({querySelectorAll:()=>arr}).length,150);
});
