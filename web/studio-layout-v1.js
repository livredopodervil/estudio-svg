/* RD Studio M1a: navigation and catalog presentation only.
 * Reuses existing panel nodes and handlers; no scene, timing or audio runtime. */
(function (g) {
 'use strict';
 const doc=g.document;
 if(!doc || doc.getElementById('rdComposeNav'))return;
 const by=id=>doc.getElementById(id);
 const body=doc.body;
 const preview=by('previewPanel');
 if(!preview||!by('videoTimelinePanel')||!by('workspaceLibrary'))return;
 body.classList.add('rdStudioUnified');
 const nav=doc.createElement('nav');nav.id='rdComposeNav';nav.className='rdComposeNav';nav.setAttribute('aria-label','Ferramentas de composição');
 const actions=[
  ['scenes','▤','Cenas'],['library','◈','Biblioteca'],['roteiro','☷','Roteiro'],['insert','＋','Inserir'],['undo','↶','Desfazer'],['redo','↷','Refazer'],
  ['properties','⚙','Propriedades'],['audio','♫','Áudio'],['production','⇩','Produzir'],['focus','⛶','Foco']
 ];
 const buttons=new Map();
 function button(key,icon,label){const b=doc.createElement('button');b.type='button';b.dataset.rdAction=key;const glyph=doc.createElement('span');glyph.className='rdNavGlyph';glyph.textContent=icon;const word=doc.createElement('span');word.className='rdNavLabel';word.textContent=label;b.append(glyph,word);b.title=label;b.setAttribute('aria-label',label);b.setAttribute('aria-expanded','false');buttons.set(key,b);nav.append(b);return b;}
 for(const [id,icon,label] of actions)button(id,icon,label);
 preview.querySelector('.panelHead').after(nav);
 // M1R2_INSPECTOR_AFTER_PLAYER: controls stay immediately after viewport on mobile.
 const inspector=by('objectInspector'),player=preview.querySelector('.player');
 if(inspector&&player&&player.nextElementSibling!==inspector){player.after(inspector);inspector.classList.add('rdObjectBelowPlayer');}
 // Keep legacy commands available, but not permanently in the composition canvas.
 const legacy=doc.createElement('details');legacy.id='rdLegacyTools';legacy.className='rdLegacyTools';
 const legacySummary=doc.createElement('summary');legacySummary.textContent='Ferramentas avançadas (SVG, imagem da cena, camadas)';legacy.append(legacySummary);
 const legacyContainer=doc.createElement('div');legacyContainer.className='rdLegacyToolsContent';legacy.append(legacyContainer);
 const oldToolbar=preview.querySelector('.viewportToolbar');
 const oldInline=preview.querySelector('.panelHead~.inline');
 for(const id of ['editSVG','quickImage','toggleClipEdit','nativeDemoPreview','openLayersV36']){
  const element=by(id);if(element)legacyContainer.append(element);
 }
 if(oldInline&&!oldInline.children.length)oldInline.remove();
 if(oldToolbar)oldToolbar.after(legacy);

 const headActions=doc.querySelector('.topactions');
 if(headActions){const more=doc.createElement('details');more.id='rdHeaderMore';more.className='rdHeaderMore';const summary=doc.createElement('summary');summary.textContent='Mais ▾';more.append(summary);const menu=doc.createElement('div');menu.className='rdHeaderMenu';more.append(menu);
  for(const id of ['openSvgFromTop','editJson','importButton','importBundle','relinkMissingImages','exportButton','exportBundle']){const el=by(id);if(el)menu.append(el);}
  headActions.prepend(more);
 }
 const drawers={scenes:'scenesPanel',properties:'editPanel',audio:'editPanel',production:'workPanel'};
 let drawer='none';
 function state(){body.dataset.rdDrawer=drawer;for(const [name,b] of buttons)b.setAttribute('aria-expanded',String(name===drawer));}
 function close(){drawer='none';state();}
 function toggle(which){if(drawer===which){close();return;}if(!by('workspaceLibrary').hidden)by('closeLibrary')?.click();drawer=which;state();}
 function editorTab(name){const b=doc.querySelector(`[data-edit="${name}"]`);if(b)b.click();}
 const closeButtons=[];
 for(const [key,id] of Object.entries({scenes:'scenesPanel',properties:'editPanel',production:'workPanel'})){
  const panel=by(id),head=panel?.querySelector('.panelHead');
  if(!panel||!head)continue;
  const b=doc.createElement('button');b.type='button';b.className='rdCloseSide';b.textContent='×';b.title='Fechar painel';b.setAttribute('aria-label','Fechar painel '+key);b.onclick=close;head.append(b);closeButtons.push(b);
 }
 for(const [name,b] of buttons){b.onclick=()=>{
  if(name==='undo'||name==='redo'){by(name==='undo'?'documentUndo':'documentRedo')?.click();return;}
  if(name==='scenes')return toggle('scenes');
  if(name==='library'){close();by('openLibrary')?.click();drawer='library';state();return;}
  if(name==='roteiro'){close();by('rdRoteiroButton')?.click();return;}
  if(name==='insert'){close();by('viewportInsert')?.click();return;}
  if(name==='properties'){
   const inspect=by('viewportInspector');
   if(inspect&&!inspect.disabled){if(by('objectInspector')?.hidden)inspect.click();close();by('objectInspector')?.scrollIntoView?.({block:'nearest'});return;}
   editorTab('scene');return toggle('properties');
  }
  if(name==='audio'){editorTab('audio');return toggle('audio');}
  if(name==='production')return toggle('production');
  if(name==='focus'){close();by('viewportFocus')?.click();return;}
 };}
 by('closeLibrary')?.addEventListener('click',()=>{if(drawer==='library')close();});
 by('closeProjects')?.addEventListener('click',close);
 for(const b of doc.querySelectorAll('.mobileTabs [data-pane]'))b.addEventListener('click',event=>{
  event.preventDefault();event.stopImmediatePropagation();
  const target=b.dataset.pane;
  if(target==='scenesPanel')toggle('scenes');
  else if(target==='editPanel'){editorTab('scene');toggle('properties');}
  else if(target==='workPanel')toggle('production');
  else close();
 },true);
 g.addEventListener('rd-studio-pane',e=>{const target=e.detail;if(target==='previewPanel')close();else {const next=target==='editPanel'?'properties':target==='scenesPanel'?'scenes':target==='workPanel'?'production':null;if(next){drawer=next;state();}}});
 doc.addEventListener('keydown',e=>{if(e.key==='Escape'&&drawer!=='none'&&!doc.querySelector('dialog[open]'))close();});
 // SVG buttons historically inserted immediately. Require an explicit preview and confirmation.
 const catalog=by('objectCatalog');let approve=false;
 if(catalog){const dialog=doc.createElement('dialog');dialog.id='rdSvgPreview';dialog.className='rdSvgPreview';
  dialog.innerHTML='<div class="rdSvgPreviewHead"><strong id="rdSvgPreviewTitle"></strong><button type="button" id="rdSvgPreviewClose">× Fechar</button></div><div id="rdSvgPreviewStage"></div><p id="rdSvgPreviewNote" class="info"></p><button type="button" id="rdSvgPreviewInsert" class="primary">Inserir objeto SVG</button>';
  doc.body.append(dialog);let selectedButton=null;
  function clear(){selectedButton=null;by('rdSvgPreviewStage').replaceChildren();}
  by('rdSvgPreviewClose').onclick=()=>dialog.close();dialog.addEventListener('close',clear);
  catalog.addEventListener('click',e=>{
   if(approve){approve=false;return;}
   const target=e.target.closest('[data-library-object]');if(!target)return;
   e.preventDefault();e.stopImmediatePropagation();
   const kind=target.dataset.libraryObject;
   const generator=g.StudioWorkspaceV38;
   if(!generator||!generator.catalog.some(([id])=>id===kind))return;
   try{
    const entry=generator.catalog.find(([id])=>id===kind);
    const obj=generator.object(kind,'obj_preview',720,8);
    const stage=by('rdSvgPreviewStage');stage.replaceChildren();
    const svg=doc.createElementNS('http://www.w3.org/2000/svg','svg');svg.setAttribute('viewBox','0 0 1280 720');svg.setAttribute('role','img');svg.setAttribute('aria-label','Prévia geométrica de '+entry[1]);
    const parsed=new DOMParser().parseFromString('<svg xmlns="http://www.w3.org/2000/svg">'+obj.markup+'</svg>','image/svg+xml');
    if(parsed.querySelector('parsererror'))throw Error('SVG inválido');
    for(const child of [...parsed.documentElement.children])svg.append(doc.importNode(child,true));
    stage.append(svg);selectedButton=target;
    by('rdSvgPreviewTitle').textContent=entry[1];
    by('rdSvgPreviewNote').textContent='Prévia da geometria. O movimento é aplicado pela timeline após a inserção. Em cenas que não são SVG, marque “Criar nova cena” na biblioteca.';
    dialog.showModal();
   }catch(err){g.console.warn('RD Studio: não foi possível preparar prévia SVG',err);}
  },true);
  by('rdSvgPreviewInsert').onclick=()=>{const target=selectedButton;if(!target)return;dialog.close();approve=true;try{target.click();}finally{approve=false;}};
 }
 // Same verified native GIL choices as the insertion dialog; both lead to its preview.
 const gilHost=by('workspaceLibrary');
 if(gilHost&&by('objectExamples')&&by('gilLibrarySelect')){
  const section=doc.createElement('section');section.className='rdUnifiedCatalog';
  const heading=doc.createElement('h4');heading.textContent='GIL nativa · biblioteca completa com prévia animada';section.append(heading);
  const grid=doc.createElement('div');grid.className='rdNativeCards';
  for(const o of by('gilLibrarySelect').options){const b=doc.createElement('button');b.type='button';b.dataset.example=o.value;b.textContent='◇ '+o.textContent;
   b.onclick=()=>{const select=by('gilLibrarySelect');const found=[...select.options].some(opt=>opt.value===o.value);
    if(!found){const opt=doc.createElement('option');opt.value=o.value;opt.textContent=o.textContent;select.append(opt);}
    select.value=o.value;by('gilLibraryInsert')?.click();
   };grid.append(b);}
  section.append(grid);const hint=doc.createElement('p');hint.className='smallNote';hint.textContent='Exemplos experimentais do catálogo anterior permanecem abaixo; podem exigir recursos GIL ainda não suportados.';section.append(hint);
  gilHost.insertBefore(section,by('gilLibrarySelect').closest('.inline').previousElementSibling);
 }
 state();
 g.RDStudioM1={open:toggle,close,mode:()=>drawer};
})(window);
