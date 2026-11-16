'use strict';
/* RD Studio 4: editor de projeto espacial e publicação. Nenhum segredo no front. */
(() => {
 const el = id=>document.getElementById(id);
 const API = async(path,body)=>{
   const res=await fetch(path,body===undefined?{}:{method:'POST',headers:{'Content-Type':'application/json','X-RD-Token':window.STUDIO_TOKEN},body:JSON.stringify(body)});
   const data=await res.json();if(!res.ok)throw Error(data.error||`HTTP ${res.status}`);return data;
 };
 const status=(message,error=false)=>{const box=el('space-expose-state');if(box){box.textContent=message;box.style.color=error?'#a22929':'#24795e';}};
 let state=null, selected=null,edges=[],moving=null,plan=null,restore=null,projectIDs=[];
 const svgNS='http://www.w3.org/2000/svg';
 const svgEl=(tag,props={})=>{const e=document.createElementNS(svgNS,tag);for(const [k,v] of Object.entries(props))e.setAttribute(k,v);return e;};
 const textOpt=(select,value,label)=>{const o=document.createElement('option');o.value=value;o.textContent=label;select.append(o);};
 function showProject(){
   const id=el('space-project').value,p=state?.projects.find(x=>x.id===id),url=p?.url;
   el('space-project-info').textContent=p?`${p.title} · ${p.status} · ${p.summary||'Sem descrição'} · ${url||'sem URL'}`:'Cadastre o projeto na aba Catálogo ou importe em Descobrir apps.';
   el('space-open-app').hidden=!url;
   if(url)el('space-open-app').href=url.startsWith('/')?`http://127.0.0.1:${window.PREVIEW_PORT}${url}`:url;
 }
 function linksUI(){
  const box=el('space-links');box.replaceChildren();
  for(const [a,b] of edges){const btn=document.createElement('button');btn.type='button';btn.textContent=`${a} ↔ ${b}   × Remover`;
   btn.addEventListener('click',()=>{edges=edges.filter(x=>!(new Set(x).has(a)&&new Set(x).has(b)));linksUI();mapUI();});box.append(btn);}
  if(!edges.length)box.textContent='Nenhuma conexão.';
 }
 function selectNode(id, redraw=true){
  selected=state?.nodes.find(n=>n.id===id)||null;
  el('space-selected-label').textContent=selected?`Dodecaedro: ${selected.id}`:'Selecione um dodecaedro';
  for(let i=0;i<3;i++)el(['space-x','space-y','space-z'][i]).value=selected?.position?.[i]??'';
  el('space-save-position').disabled=!selected?.editable;
  if(redraw)mapUI();else document.querySelectorAll('.space-map-node').forEach(g=>g.classList.toggle('active',g.dataset.id===id));
 }
 function mapUI(){
  const svg=el('space-map');svg.replaceChildren();if(!state)return;
  // Projeção ortográfica XY, Z continua editável por campo numérico.
  const nodes=state.nodes,coords=new Map();
  const toX=v=>390+v*13,toY=v=>245-v*13;
  for(const n of nodes){const p=n.position||[0,0,0];coords.set(n.id,{x:toX(p[0]),y:toY(p[1])});}
  for(const [a,b] of edges){const pa=coords.get(a),pb=coords.get(b);if(!pa||!pb)continue;
   svg.append(svgEl('line',{x1:pa.x,y1:pa.y,x2:pb.x,y2:pb.y,class:'space-map-edge'}));}
  // Grid com eixos para a manipulação de posição.
  for(let n=-25;n<=25;n+=5){const x=toX(n),y=toY(n);
   svg.insertBefore(svgEl('line',{x1:x,y1:0,x2:x,y2:500,stroke:'#b9e1e3','stroke-width':'1'}),svg.firstChild);
   svg.insertBefore(svgEl('line',{x1:0,y1:y,x2:780,y2:y,stroke:'#b9e1e3','stroke-width':'1'}),svg.firstChild);}
  for(const n of nodes){const p=coords.get(n.id);if(!p)continue;const g=svgEl('g',{class:'space-map-node'+(selected?.id===n.id?' active':''),'data-id':n.id,tabindex:'0',role:'button'});
   g.append(svgEl('rect',{x:p.x-62,y:p.y-22,width:124,height:44}));const label=svgEl('text',{x:p.x,y:p.y+5,'text-anchor':'middle'});
   label.textContent=n.id.length>16?n.id.slice(0,15)+'…':n.id;g.append(label);
   g.addEventListener('pointerdown',ev=>{ev.preventDefault();selectNode(n.id,false);moving={id:n.id,start:[...n.position],pointerId:ev.pointerId};g.setPointerCapture(ev.pointerId);});
   g.addEventListener('pointermove',ev=>{if(!moving||moving.id!==n.id||!n.editable)return;
    const rect=svg.getBoundingClientRect(),px=(ev.clientX-rect.left)*780/rect.width,py=(ev.clientY-rect.top)*500/rect.height;
    // Snap a 0,5 unidade para evitar posições flutuantes.
    const x=Math.round(((px-390)/13)*2)/2,y=Math.round(((245-py)/13)*2)/2;
    n.position[0]=Math.max(-300,Math.min(300,x));n.position[1]=Math.max(-300,Math.min(300,y));
    el('space-x').value=n.position[0];el('space-y').value=n.position[1];
    g.querySelector('rect').setAttribute('x',px-62);g.querySelector('rect').setAttribute('y',py-22);
    const text=g.querySelector('text');text.setAttribute('x',px);text.setAttribute('y',py+5);
   });
   g.addEventListener('pointerup',()=>{moving=null;mapUI();});
   g.addEventListener('pointercancel',()=>{moving=null;mapUI();});
   g.addEventListener('keydown',ev=>{if(ev.key==='Enter'||ev.key===' '){ev.preventDefault();selectNode(n.id);}});
   svg.append(g);
  }
 }
 const inputKeys=[['cameraDistance','Distância de câmera',8,30,.1],['initialZoom','Zoom inicial',.5,2,.05],['zoomMin','Zoom mínimo',.4,1.3,.05],['zoomMax','Zoom máximo',1.1,3,.05],['zoomStep','Passo de zoom',.02,.25,.01],['rotationFocus','Rotação do nó ativo',0,.8,.005],['rotationNeighbors','Rotação dos vizinhos',0,.5,.005],['rotationTilt','Inclinação da rotação',0,.3,.005],['dragSensitivity','Sensibilidade ao arraste',.002,.03,.001]];
 function settingsUI(){const div=el('space-settings');div.replaceChildren();
  for(const [id,label,min,max,step] of inputKeys){const wrap=document.createElement('label');wrap.textContent=label;const input=document.createElement('input');input.type='number';input.dataset.sceneKey=id;input.min=min;input.max=max;input.step=step;input.value=state.settings[id]??(id==='initialZoom'?1:'');wrap.append(input);div.append(wrap);}
  const wrap=document.createElement('label');wrap.textContent='Rotação automática';const cb=document.createElement('input');cb.type='checkbox';cb.dataset.sceneKey='autoplay';cb.checked=!!state.settings.autoplay;wrap.append(cb);div.append(wrap);
  el('space-adapter-state').textContent=state.adapter_installed?'Adaptador configurável instalado':state.adapter_supported?'Adaptador compatível; será instalado no primeiro salvamento':'Motor desconhecido; salvar parâmetros não será permitido';
  if(state.mini_sync_installed)el('space-adapter-state').textContent+=' · Miniatura sincronizada: arrasto e pinça controlam a cena';
  else el('space-adapter-state').textContent+=' · ATENÇÃO: miniatura ainda não está sincronizada';
  el('space-repair-mini').disabled=state.mini_sync_installed;
  el('space-save-settings').disabled=!state.adapter_supported;
 }
 async function refresh(){try{
   state=await API('/api/spatial');edges=state.links.map(x=>[...x]);
   projectIDs=state.projects.map(x=>x.id);
   const projects=el('space-project');const old=projects.value;projects.replaceChildren();
   for(const p of state.projects)textOpt(projects,p.id,`${p.title||p.id} · ${p.status}`);
   if(projectIDs.includes(old))projects.value=old;
   for(const box of ['space-edge-a','space-edge-b']){
      const target=el(box),v=target.value;target.replaceChildren();for(const n of state.nodes)textOpt(target,n.id,n.id);
      if(state.nodes.some(n=>n.id===v))target.value=v;
   }
   el('space-open-lab').href=state.preview;
   el('space-open-portfolio').href=`http://127.0.0.1:${window.PREVIEW_PORT}/projetos/`;
   showProject();linksUI();selectNode(state.nodes.find(n=>n.id===selected?.id)?.id||state.nodes[0]?.id);settingsUI();
   if(el("tab-spatial").classList.contains("active")&&!el("space-live-preview").getAttribute("src"))updatePreview();
  }catch(e){status(e.message,true);}}
 el('space-refresh').addEventListener('click',refresh);
 el('space-project').addEventListener('change',showProject);
 el('space-expose').addEventListener('click',async()=>{
   if(el('space-destination').value==='spatial'&&!confirm('Gerar dodecaedro Projetos e conectar ao Núcleo/Sistemas, mantendo os demais módulos?'))return;
   try{const r=await API('/api/spatial/expose',{destination:el('space-destination').value,project:el('space-project').value,confirm:'INTEGRAR'});
     status(r.message);await refresh();if(el('space-live-preview').getAttribute('src'))updatePreview();}catch(e){status(e.message,true);}
 });
 el('space-add-edge').addEventListener('click',()=>{const a=el('space-edge-a').value,b=el('space-edge-b').value;
  if(!a||!b||a===b)return status('Selecione dois dodecaedros diferentes.',true);
  if(edges.some(x=>x.includes(a)&&x.includes(b)))return status('Esses dodecaedros já estão conectados.',true);
  edges.push([a,b]);linksUI();mapUI();});
 el('space-save-links').addEventListener('click',async()=>{if(!state)return;
  if(!confirm('Salvar estas conexões no manifesto do laboratório 3D?'))return;
  try{const r=await API('/api/spatial/links',{links:edges,expected_sha256:state.manifest_sha,confirm:'SALVAR GRAFO'});
   status(r.message);await refresh();if(el('space-live-preview').getAttribute('src'))updatePreview();}catch(e){status(e.message,true);}});
 el('space-save-position').addEventListener('click',async()=>{
  if(!selected)return;
  const pos=['space-x','space-y','space-z'].map(x=>Number(el(x).value));
  if(pos.some(x=>!Number.isFinite(x)))return status('Informe três coordenadas numéricas.',true);
  try{const data=await API(`/api/file?path=${encodeURIComponent(selected.source)}`);
   const result=await API('/api/spatial/position',{id:selected.id,position:pos,expected_sha256:data.sha256});
   status(result.message);await refresh();if(el('space-live-preview').getAttribute('src'))updatePreview();}catch(e){status(e.message,true);}
 });
 el('space-save-settings').addEventListener('click',async()=>{
  if(!state)return;
  const settings={};for(const x of document.querySelectorAll('[data-scene-key]'))settings[x.dataset.sceneKey]=x.type==='checkbox'?x.checked:Number(x.value);
  if(!confirm('Salvar os parâmetros de cena? Na primeira vez, o adaptador alterará somente js/site-v10.js e criará backup.'))return;
  try{const r=await API('/api/spatial/settings',{settings,expected_sha256:state.settings_sha,confirm:'APLICAR CENA'});status(r.message);await refresh();if(el('space-live-preview').getAttribute('src'))updatePreview();}catch(e){status(e.message,true);}
 });
 function updatePreview(){const url=new URL(state?.preview||`http://127.0.0.1:${window.PREVIEW_PORT}/laboratorio/`);if(url.origin!==`http://127.0.0.1:${window.PREVIEW_PORT}`){status('Origem inesperada da prévia',true);return;}url.searchParams.set('t',Date.now());const frame=el('space-live-preview');el('space-preview-status').textContent='Carregando '+url.pathname+'… Se ficar em branco, abra o laboratório em nova aba.';frame.src=url.href;}
 el('space-live-preview').addEventListener('load',()=>{if(el('space-live-preview').getAttribute('src'))el('space-preview-status').textContent='Documento carregado. Se o 3D não aparecer, abra em nova aba e verifique WebGL/CDN no navegador.';});
 el('space-reload-preview').addEventListener('click',updatePreview);
 el('space-repair-mini').addEventListener('click',async()=>{
  if(!confirm('Conectar a miniatura 3D à cena principal neste worktree?\nÉ criado backup e não há push.'))return;
  try{
   const r=await API('/api/spatial/mini/repair',{confirm:'REPARAR MINIATURA'});
   status(r.message);await refresh();if(el('space-live-preview').getAttribute('src'))updatePreview();
  }catch(e){status('Reparo bloqueado: '+e.message,true);}
 });
 function countSelected(){
  const controls=el('space-publish-list').querySelectorAll('input[type=checkbox]');
  el('space-selected-count').textContent=Array.from(controls).filter(c=>c.checked).length+' / '+controls.length+' arquivos selecionados';
 }
 el('space-select-all').addEventListener('click',()=>{el('space-publish-list').querySelectorAll('input[type=checkbox]').forEach(c=>c.checked=true);countSelected();});
 el('space-select-none').addEventListener('click',()=>{el('space-publish-list').querySelectorAll('input[type=checkbox]').forEach(c=>c.checked=false);countSelected();});
 el('space-publish-list').addEventListener('change',countSelected);
 el('space-publish-plan').addEventListener('click',async()=>{
  plan=null;el('space-publish-apply').disabled=true;el('space-publish-list').replaceChildren();
  try{const r=await API('/api/publish/plan',{});plan=r;
   el('space-publish-summary').textContent=`Destino: ${r.status.origin} · ${r.status.ahead} commit(s) locais · ${r.files.length} arquivo(s) pendente(s). Revise cuidadosamente antes de publicar.`;
   for(const x of r.files){const label=document.createElement('label'),cb=document.createElement('input');cb.type='checkbox';cb.value=x.path;cb.checked=true;label.append(cb,document.createTextNode(` ${x.state} ${x.path}`));el('space-publish-list').append(label);}
   countSelected();
   el('space-publish-apply').disabled=!(r.files.length||r.status.ahead);
  }catch(e){el('space-publish-summary').textContent='Não foi possível preparar: '+e.message;}
 });
 el('space-publish-apply').addEventListener('click',async()=>{
  if(!plan)return;
  const paths=[...el('space-publish-list').querySelectorAll('input:checked')].map(x=>x.value);
  const msg=el('space-publish-message').value.trim();
  if(!confirm(`Enviar alterações para ${plan.status.origin} (main)?\nArquivos escolhidos: ${paths.length}.\nMensagem: ${msg}\nSerá criada uma tag remota de backup.`))return;
  if(prompt('Digite PUBLICAR para confirmar o envio ao GitHub:')!=='PUBLICAR')return;
  el('space-publish-apply').disabled=true;
  try{const r=await API('/api/publish/apply',{confirm:'PUBLICAR',expected_head:plan.head,expected_remote:plan.remote,expected_fingerprint:plan.fingerprint,paths,message:msg});
   el('space-publish-summary').textContent=r.message;plan=null;await refresh();}catch(e){el('space-publish-summary').textContent='Publicação interrompida: '+e.message;}
 });
 el('space-recovery-refresh').addEventListener('click',async()=>{
  try{restore=await API('/api/recovery/fetch',{});const select=el('space-recovery-tags');select.replaceChildren();
    for(const tag of restore.tags)textOpt(select,tag.tag,`${tag.tag} · ${tag.sha.slice(0,10)}`);
    el('space-recovery-summary').textContent=`${restore.tags.length} backups locais disponíveis. Se não aparecerem, sincronize tags pelo Git no terminal.`;
  }catch(e){el('space-recovery-summary').textContent=e.message;}
 });
 el('space-recovery-apply').addEventListener('click',async()=>{
  const tag=el('space-recovery-tags').value;
  if(!tag||!restore)return;
  if(!confirm(`RESTAURAR o estado do site registrado em ${tag} e publicar um NOVO commit?\n\nIsso pode remover alterações posteriores do site. Não altera projetos externos ao repositório.`))return;
  if(prompt('Para criar o commit de reversão e publicar, digite REVERTER:')!=='REVERTER')return;
  try{const r=await API('/api/recovery/apply',{tag,expected_remote:restore.status.remote,confirm:'REVERTER'});
    el('space-recovery-summary').textContent=r.message;await refresh();}catch(e){el('space-recovery-summary').textContent=e.message;}
 });
 setTimeout(refresh,400);
})();
