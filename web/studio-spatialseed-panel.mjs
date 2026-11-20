// M2.1 floating SpatialSeed controls — one runtime, no second renderer.
// Native commands are invoked on the existing same-origin iframe.
const $$ = id => document.getElementById(id);
const stringify = el => (el.getAttribute('aria-label')||el.title||el.textContent||'').trim().replace(/\s+/g,' ').slice(0,110);
export function collectNativeActions(doc) {
  if (!doc || typeof doc.querySelectorAll !== 'function') return [];
  const out=[]; const ids=new Set();
  for (const el of doc.querySelectorAll('button, input[type="button"], input[type="submit"]')) {
    if (el.disabled || el.hidden || el.closest?.('[hidden]')) continue;
    const label=stringify(el)||el.value?.trim();
    if (!label || label.length>110) continue;
    const id=el.id||null;const key=id||`${label}:${out.length}`;
    if (ids.has(key)) continue;
    ids.add(key);
    out.push({id,label,element:el});
    if(out.length>=150)break;
  }
  return out;
}
// Input forwarding preserves native SpatialSeed event handlers and source state.
export function collectNativeFields(doc) {
  if(!doc||typeof doc.querySelectorAll!=='function')return [];
  const out=[];
  for(const el of doc.querySelectorAll('select, input, textarea')) {
    if(el.disabled||el.hidden||el.closest?.('[hidden]'))continue;
    const tag=el.tagName?.toLowerCase();const type=(el.type||'text').toLowerCase();
    if(tag==='input'&&!['text','number','range','checkbox','color'].includes(type))continue;
    if(tag==='textarea'&&(el.value||'').length>25000)continue;
    const ident=(el.id||el.name||'').toLowerCase();
    if(/password|secret|token|credential|private.?key/.test(ident))continue;
    const label=el.getAttribute('aria-label')||el.getAttribute('title')||el.labels?.[0]?.textContent?.trim()||el.name||el.id;
    if(!label)continue;
    out.push({label:String(label).trim().slice(0,110),element:el,tag,type});
    if(out.length>=150)break;
  }
  return out;
}
export function mountSpatialSeedPanel({getNative,showError=()=>{}}) {
  const panel=$$('ssFloatingPanel'),toggle=$$('ssViewportTools'),list=$$('ssNativeActions'),fieldsHost=$$('ssNativeFields'),search=$$('ssNativeFilter');
  if(!panel||!toggle||!list||!fieldsHost||!search)throw Error('Painel SpatialSeed incompleto');
  let actions=[],fields=[];
  function update() {
    const query=search.value.trim().toLocaleLowerCase('pt-BR');
    list.replaceChildren();fieldsHost.replaceChildren();
    let shown=0;
    for(const item of actions) {
      if(query&&!item.label.toLocaleLowerCase('pt-BR').includes(query))continue;
      const button=document.createElement('button');
      button.type='button';button.textContent=item.label;
      button.title=item.id||item.label;
      button.addEventListener('click',()=>{
        try { const native=getNative(); if(item.element.ownerDocument!==native.document)throw Error('Comando desatualizado: recarregue ferramentas.');
          item.element.click(); setTimeout(refresh,100); }
        catch(error){showError(error.message);}
      });
      list.append(button);if(++shown>=60)break;
    }
    let inputsShown=0;
    for(const item of fields){
      if(query&&!item.label.toLocaleLowerCase('pt-BR').includes(query))continue;
      if(inputsShown++>=30)break;
      const row=document.createElement('label');row.textContent=item.label;
      const original=item.element;
      const input=document.createElement(item.tag==='select'?'select':item.tag==='textarea'?'textarea':'input');
      if(input.tagName==='INPUT')input.type=item.type;
      if(input.tagName==='SELECT')for(const opt of original.options){const child=document.createElement('option');child.value=opt.value;child.textContent=opt.textContent;input.add(child);}
      if(item.type==='checkbox')input.checked=original.checked;
      else input.value=original.value;
      for(const attr of ['min','max','step'])if(original.hasAttribute?.(attr))input.setAttribute(attr,original.getAttribute(attr));
      const evt=item.type==='range'||item.type==='color'?'input':'change';
      input.addEventListener(evt,()=>{
        try{const native=getNative();if(original.ownerDocument!==native.document)throw Error('Campo desatualizado; atualize ferramentas.');
          if(item.type==='checkbox')original.checked=input.checked;else original.value=input.value;
          const E=native.document.defaultView.Event;
          original.dispatchEvent(new E('input',{bubbles:true}));
          original.dispatchEvent(new E('change',{bubbles:true}));
        }catch(error){showError(error.message);}
      });
      row.append(input);fieldsHost.append(row);
    }
    $$('ssNativeCount').textContent=`${shown} comandos · ${Math.min(inputsShown,30)} controles`;
  }
  function refresh(){
    try{const doc=getNative().document;actions=collectNativeActions(doc);fields=collectNativeFields(doc);update();}
    catch(error){actions=[];fields=[];update();showError(error.message);}
  }
  function open(on){ panel.hidden=!on;toggle.setAttribute('aria-pressed',String(on));if(on)refresh(); }
  toggle.addEventListener('click',()=>open(panel.hidden));
  $$('ssFloatClose').addEventListener('click',()=>open(false));
  $$('ssNativeRefresh').addEventListener('click',refresh);
  search.addEventListener('input',update);
  // Mobile panel stays in document flow, safely outside stageShell.
  // Desktop floating panel may be dragged without altering viewport dimensions.
  let drag=null;const handle=$$('ssFloatHandle');
  handle.addEventListener('pointerdown',e=>{
    if(e.target.closest('button')||matchMedia('(max-width:700px)').matches)return;
    drag={x:e.clientX,y:e.clientY,left:panel.offsetLeft,top:panel.offsetTop};
    handle.setPointerCapture(e.pointerId);
  });
  handle.addEventListener('pointermove',e=>{
    if(!drag)return;
    panel.style.left=Math.max(0,Math.min(window.innerWidth-panel.offsetWidth,drag.left+e.clientX-drag.x))+'px';
    panel.style.top=Math.max(0,Math.min(window.innerHeight-panel.offsetHeight,drag.top+e.clientY-drag.y))+'px';
  });
  handle.addEventListener('pointerup',()=>{drag=null;});
  handle.addEventListener('pointercancel',()=>{drag=null;});
  return {refresh,open};
}
