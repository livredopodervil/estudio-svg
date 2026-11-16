'use strict';
(() => {
  const $ = id => document.getElementById(id);
  const state = {preview: `http://127.0.0.1:${window.PREVIEW_PORT}/`, file: null, fileSHA: null,
    initial: '', dirty: false, catalogSHA: null, catalogID: '', git: null, tab: 'dashboard', map: null, selected: null, sync: null};
  const labels = {dashboard:'Visão geral',structure:'Mapa do site',discover:'Descobrir apps',spatial:'Editor 3D e publicação',patches:'Pacotes IA',multimedia:'Multimídia',files:'Arquivos',catalog:'Catálogo',preview:'Prévia',checks:'Vistoria',git:'Git',history:'Histórico'};
  const E = (tag, text='', css='') => {const el=document.createElement(tag);el.textContent=text;if(css)el.className=css;return el;};
  let toaster = null;
  function notify(message, fail=false){const el=$('toast');el.textContent=message;el.className='show'+(fail?' error':'');clearTimeout(toaster);toaster=setTimeout(()=>el.className='',5500);}
  async function api(path, body){
    const config = body===undefined ? {} : {method:'POST',headers:{'Content-Type':'application/json','X-RD-Token':window.STUDIO_TOKEN},body:JSON.stringify(body)};
    try{
      const r=await fetch(path,config);
      const result=await r.json();
      if(!r.ok)throw Error(result.error || `HTTP ${r.status}`);
      return result;
    }catch(e){notify(e.message,true);throw e;}
  }
  function go(tab){
    if(!labels[tab])return;
    state.tab=tab;
    document.querySelectorAll('.tab').forEach(el=>el.classList.toggle('active',el.id===`tab-${tab}`));
    document.querySelectorAll('[data-tab]').forEach(el=>el.classList.toggle('active',el.dataset.tab===tab));
    $('current-section').textContent=labels[tab];
    if(tab==='files')loadFiles();
    if(tab==='structure')loadStructure();
    if(tab==='spatial')$('space-refresh').click();
    if(tab==='catalog')loadCatalog();
    if(tab==='git'){loadGit();loadSync(false);}
    if(tab==='history' && state.file)$('history-path').value=state.file;
    if(tab==='preview' && !$('site-preview').src)loadPreview();
    window.scrollTo(0,0);
  }
  document.querySelectorAll('[data-tab]').forEach(b=>b.addEventListener('click',()=>go(b.dataset.tab)));
  document.querySelectorAll('[data-go]').forEach(b=>b.addEventListener('click',()=>go(b.dataset.go)));
  async function loadState(){
    const result=await api('/api/state');
    state.preview=result.preview;
    const git=result.git;
    $('git-branch').textContent=git.enabled ? (git.branch||'HEAD destacado'):'sem Git';
    $('metric-branch').textContent=git.enabled ? (git.branch||'detached'):'não Git';
    $('metric-changed').textContent=git.status.length;
    $('metric-projects').textContent=result.catalog.projects.length;
    $('info-root').textContent=result.root;
    $('info-preview').textContent=result.preview;
    $('info-head').textContent=git.head||'—';
    $('header-preview').href=result.preview;
    $('preview-newtab').href=result.preview;
    state.git=git;
  }
  const S = (tag,attrs={}) => {const el=document.createElementNS('http://www.w3.org/2000/svg',tag);for(const [k,v] of Object.entries(attrs))el.setAttribute(k,String(v));return el;};
  function selectMapNode(node){
    state.selected=node;
    $('structure-selected').textContent=node.label;
    $('structure-kind').textContent=({site:'PORTAL',page:'PÁGINA',module:'DODECAEDRO',project:'PROJETO',group:'SEÇÃO'})[node.kind]||node.kind;
    $('structure-desc').textContent=`Origem: ${node.path||'agrupamento virtual'} · Prévia: ${node.url||'não cadastrada'} · ID: ${node.id}`;
    $('structure-edit').disabled=!node.path;
    $('structure-preview').disabled=!node.url;
    document.querySelectorAll('.map-node').forEach(el=>el.classList.toggle('selected',el.dataset.nodeId===node.id));
  }
  function drawStructure(){
    const data=state.map;if(!data)return;
    const svg=$('structure-svg'),query=$('structure-search').value.toLowerCase().trim(),links=$('structure-spatial').checked;
    const nodes=data.nodes,byId=new Map(nodes.map(n=>[n.id,n]));
    const parents=new Map(data.edges.filter(e=>e.kind==='hierarchy').map(e=>[e.target,e.source]));
    const depthOf=(id,guard=0)=>!parents.has(id)||guard>8?0:1+depthOf(parents.get(id),guard+1);
    const layers=new Map();for(const n of nodes){const d=depthOf(n.id);if(!layers.has(d))layers.set(d,[]);layers.get(d).push(n);}
    const pos=new Map();let cursor=44;
    for(const [d,items] of [...layers].sort((a,b)=>a[0]-b[0])){
      const maxColumns=7,rows=Math.ceil(items.length/maxColumns);
      for(let i=0;i<items.length;i++){
        const row=Math.floor(i/maxColumns),rowItems=items.slice(row*maxColumns,(row+1)*maxColumns),col=i%maxColumns;
        const spacing=1100/(rowItems.length+1);
        pos.set(items[i].id,{x:50+(col+1)*spacing,y:cursor+row*92});
      }
      cursor+=Math.max(1,rows)*92+65;
    }
    svg.setAttribute('viewBox',`0 0 1200 ${Math.max(330,cursor)}`);
    svg.replaceChildren();
    for(const e of data.edges){
      if(e.kind!=='hierarchy'&&!links)continue;
      const a=pos.get(e.source),b=pos.get(e.target);if(!a||!b)continue;
      const path=S('path',{d:e.kind==='hierarchy'?`M ${a.x} ${a.y+22} Q ${(a.x+b.x)/2} ${(a.y+b.y)/2} ${b.x} ${b.y-22}`:`M ${a.x} ${a.y} Q ${(a.x+b.x)/2} ${Math.max(a.y,b.y)+55} ${b.x} ${b.y}`,'class':'map-edge '+(e.kind==='hierarchy'?'':e.kind)});
      svg.append(path);
    }
    for(const node of nodes){
      const p=pos.get(node.id),g=S('g',{'class':'map-node'+(query&&!`${node.label} ${node.path} ${node.kind}`.toLowerCase().includes(query)?' dimmed':''), 'data-node-id':node.id,tabindex:'0',role:'button','aria-label':`${node.label}. ${node.kind}`});
      g.append(S('rect',{x:p.x-76,y:p.y-24,width:152,height:48,rx:11}));
      const text=S('text',{x:p.x,y:p.y-3,'text-anchor':'middle'});text.textContent=(node.label||'').slice(0,22);g.append(text);
      const sub=S('text',{x:p.x,y:p.y+13,'text-anchor':'middle','class':'node-subtitle'});sub.textContent=({site:'SITE',page:'PÁGINA',group:'GRUPO',project:'PROJETO',module:'3D'})[node.kind]||'';g.append(sub);
      g.addEventListener('click',()=>selectMapNode(node));g.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();selectMapNode(node);}});
      svg.append(g);
    }
    if(state.selected){const current=byId.get(state.selected.id);if(current)selectMapNode(current);}
  }
  function treeStructure(files){
    const root={children:new Map()};
    for(const file of files){
      let dir=root;for(const part of file.path.split('/')){if(!dir.children.has(part))dir.children.set(part,{children:new Map(),file:null});dir=dir.children.get(part);}dir.file=file;
    }
    function render(node,depth=0){const container=document.createDocumentFragment();
      for(const [key,value] of [...node.children].sort((a,b)=>Number(!!b[1].children.size)-Number(!!a[1].children.size)||a[0].localeCompare(b[0]))){
        if(value.children.size){const el=E('details');if(depth<1)el.open=true;const head=E('summary','▸ '+key+'/');el.append(head,render(value,depth+1));container.append(el);}
        else {const button=E('button',(value.file?.type==='media'?'▧ ':'▤ ')+key);button.type='button';button.title=value.file.path;button.addEventListener('click',()=>{go('files');openFile(value.file);});container.append(button,E('div',''));}
      }
      return container;
    }
    $('structure-tree').replaceChildren(render(root));
  }
  async function loadStructure(){
    try{const r=await api('/api/structure');state.map=r;
      $('structure-counts').replaceChildren(...Object.entries(r.counts).map(([key,value])=>E('span',`${({files:'Arquivos',pages:'Páginas',modules:'Dodecaedros',projects:'Projetos',spatial_links:'Ligações 3D'})[key]||key}: ${value}`)));
      drawStructure();treeStructure(r.files);
    }catch(e){}
  }
  $('structure-refresh').addEventListener('click',loadStructure);
  $('structure-search').addEventListener('input',drawStructure);
  $('structure-spatial').addEventListener('change',drawStructure);
  $('structure-edit').addEventListener('click',()=>{
    if(!state.selected?.path)return;
    const file=state.map.files.find(f=>f.path===state.selected.path)||{path:state.selected.path,type:'text'};
    go('files');openFile(file);
  });
  $('structure-preview').addEventListener('click',()=>{
    const url=state.selected?.url;if(!url)return;
    if(url.startsWith('/')&&!url.startsWith('//')){$('preview-path').value=url;go('preview');loadPreview();}
    else if(url.startsWith('https://'))window.open(url,'_blank','noopener,noreferrer');
  });
  function displaySync(r){
    state.sync=r;
    $('sync-origin').textContent=r.origin||'—';
    $('sync-branch').textContent=r.branch||'—';
    $('sync-counter').textContent=`${r.ahead??'?'} à frente / ${r.behind??'?'} atrás`;
    $('sync-incoming').textContent=(r.incoming||[]).join('\n')||'Sem commits recebidos pendentes.';
    $('sync-outgoing').textContent=(r.outgoing||[]).join('\n')||'Sem commits locais pendentes.';
    $('sync-state').textContent=!r.clean?'EDIÇÕES LOCAIS':r.behind&&r.ahead?'DIVERGENTE':r.behind?'ATUALIZAÇÃO DISPONÍVEL':r.ahead?'COMMITS LOCAIS':'SINCRONIZADO (CACHE)';
    $('sync-update').disabled=!r.clean||!r.behind||!!r.ahead;
    $('sync-publish').disabled=!r.clean||!r.ahead||!!r.behind||!r.branch?.startsWith('studio/');
  }
  async function loadSync(fetch){try{const r=await api(fetch?'/api/git/fetch':'/api/git/sync',fetch?{}:undefined);displaySync(r);if(r.message&&fetch)notify(r.message);}catch{}}
  $('sync-fetch').addEventListener('click',()=>loadSync(true));
  $('sync-update').addEventListener('click',async()=>{
    if(!state.sync?.clean)return notify('Faça commit ou remova alterações pendentes antes de atualizar.',true);
    if(prompt('Para atualizar esta cópia, digite ATUALIZAR:')!=='ATUALIZAR')return;
    try{const r=await api('/api/git/update',{confirm:'ATUALIZAR'});displaySync(r);notify(r.message);await loadState();await loadStructure();await loadGit();}catch{}
  });
  $('sync-publish').addEventListener('click',async()=>{
    const r=state.sync;if(!r?.clean||r.behind||!r.ahead)return notify('Consulte o GitHub e revise as pendências.',true);
    if(!confirm(`Publicar ${r.ahead} commit(s) para a branch main de ${r.origin}?\n\nUm backup remoto será criado. Nenhum --force será utilizado.`))return;
    if(prompt('Para confirmar a publicação real, digite PUBLICAR:')!=='PUBLICAR')return;
    try{const next=await api('/api/git/publish',{confirm:'PUBLICAR',expected_head:r.local,expected_remote:r.remote,expected_origin:r.origin});notify(next.message);displaySync(next.status);await loadState();await loadGit();}catch{}
  });
  let importPlan=null;
  $('import-plan').addEventListener('click',async()=>{
    const source=$('import-source').value.trim(),id=$('import-id').value.trim();
    $('import-apply').disabled=true;importPlan=null;
    try{const r=await api('/api/import/plan',{source,id});importPlan=r;
      $('import-report').textContent=`Origem: ${r.source}\nDestino: ${r.dest}\nArquivos: ${r.files}\nTamanho: ${Math.round(r.bytes/1024)} KB\n\nExemplos:\n${r.sample.join('\n')}`;
      $('import-report').hidden=false;$('import-apply').disabled=false;
    }catch{}
  });
  $('import-apply').addEventListener('click',async()=>{
    if(!importPlan)return;
    if(prompt(`Copiar ${importPlan.files} arquivo(s) para ${importPlan.dest}? Digite IMPORTAR:`)!=='IMPORTAR')return;
    try{const r=await api('/api/import/apply',{source:importPlan.source,id:importPlan.id,fingerprint:importPlan.fingerprint,confirm:'IMPORTAR'});
      notify(r.message);$('import-apply').disabled=true;importPlan=null;
      await loadCatalog();await loadStructure();await loadState();
    }catch{}
  });
  function visibleFile(f){const btn=E('button',f.path,'file-item');btn.type='button';btn.dataset.file=f.path;const size=E('span',f.size>1024?`${Math.round(f.size/1024)} KB`:`${f.size} B`);btn.append(size);if(state.file===f.path)btn.classList.add('active');btn.addEventListener('click',()=>openFile(f));return btn;}
  async function loadFiles(){const q=$('file-search').value.trim();try{const res=await api(`/api/files?q=${encodeURIComponent(q)}`);$('file-list').replaceChildren(...res.files.map(visibleFile));}catch{}}
  let fileTimer;
  $('file-search').addEventListener('input',()=>{clearTimeout(fileTimer);fileTimer=setTimeout(loadFiles,200);});
  function editorState(){
    $('file-save').disabled=!state.file||!state.dirty;
    $('file-refresh').disabled=!state.file;
    $('file-diff').disabled=!state.file;
    $('editor-path').textContent=state.file||'Escolha um arquivo';
    $('editor-status').textContent=!state.file?'Sem arquivo aberto':state.dirty?'Alterações ainda não salvas':'Arquivo sincronizado';
  }
  async function openFile(f){
    if(state.dirty && !confirm(`Há alterações não salvas em ${state.file}. Descartá-las?`))return;
    if(f.type==='media'){
      $('preview-path').value='/'+f.path;
      go('preview');loadPreview();return;
    }
    try{const file=await api(`/api/file?path=${encodeURIComponent(f.path)}`);
      state.file=file.path;state.fileSHA=file.sha256;state.initial=file.content;state.dirty=false;
      $('code-editor').disabled=false;$('code-editor').value=file.content;
      $('diff-output').hidden=true;editorState();
      document.querySelectorAll('.file-item').forEach(x=>x.classList.toggle('active',x.dataset.file===f.path));
    }catch{}}
  $('code-editor').addEventListener('input',()=>{state.dirty=$('code-editor').value!==state.initial;editorState()});
  async function saveFile(){
    if(!state.file||!state.dirty)return;
    try{const result=await api('/api/file/save',{path:state.file,content:$('code-editor').value,expected_sha256:state.fileSHA});
      state.initial=$('code-editor').value;state.fileSHA=result.sha256;state.dirty=false;editorState();
      notify(`Salvo: ${state.file}. Histórico de segurança criado.`);
      loadFiles();loadState();
    }catch{}
  }
  $('file-save').addEventListener('click',saveFile);
  document.addEventListener('keydown',e=>{if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='s'&&state.tab==='files'){e.preventDefault();saveFile();}});
  $('file-refresh').addEventListener('click',()=>state.file&&openFile({path:state.file,type:'text'}));
  $('file-diff').addEventListener('click',async()=>{if(!state.file)return;try{const d=await api(`/api/git/diff?path=${encodeURIComponent(state.file)}`);$('diff-output').textContent=d.diff;$('diff-output').hidden=false;}catch{}});
  $('new-file').addEventListener('click',()=>{
    if(state.dirty&&!confirm('Descartar edição não salva?'))return;
    const p=prompt('Caminho do novo arquivo (ex.: projetos/novo/index.html ou catalog/projects/novo.json):');
    if(!p)return;
    state.file=p;state.fileSHA=null;state.initial='';state.dirty=true;
    $('code-editor').disabled=false;$('code-editor').value='';
    $('diff-output').hidden=true;editorState();$('code-editor').focus();
  });
  $('asset-upload').addEventListener('click',async()=>{
    const f=$('asset-file').files?.[0],path=$('asset-dest').value.trim();
    if(!f||!path)return notify('Escolha a imagem e o caminho de destino.',true);
    if(f.size>8_000_000)return notify('Imagem acima de 8 MB',true);
    try{
      const raw=await f.arrayBuffer(),bytes=new Uint8Array(raw);
      let binary='';for(let i=0;i<bytes.length;i+=16000)binary+=String.fromCharCode(...bytes.slice(i,i+16000));
      const info=await api('/api/media/info?path='+encodeURIComponent(path));
      if(info.exists && !confirm(`Substituir a imagem existente ${path}? Uma cópia de segurança será criada.`))return;
      const result=await api('/api/upload',{path,base64:btoa(binary),expected_sha256:info.sha256});
      notify(`Imagem enviada: ${result.path}`);$('asset-file').value='';loadFiles();
    }catch{}
  });
  function loadPreview(){
    let path=$('preview-path').value.trim()||'/';
    if(!path.startsWith('/')||path.startsWith('//'))return notify('Use caminho interno iniciado por /',true);
    const url=state.preview.replace(/\/$/,'')+path;
    $('site-preview').src=url;$('preview-newtab').href=url;
  }
  $('preview-load').addEventListener('click',loadPreview);
  $('preview-path').addEventListener('keydown',e=>{if(e.key==='Enter')loadPreview()});
  function fillCatalog(p){
    const form=$('catalog-form');
    for(const key of ['id','title','summary','status','category','url','preview','color'])form.elements.namedItem(key).value=p?.[key]??({status:'rascunho',color:'#07899d'}[key]||'');
    form.elements.namedItem('topics').value=(p?.topics||[]).join(', ');
    form.elements.namedItem('neighbors').value=(p?.neighbors||[]).join(', ');
    $('catalog-title').textContent=p?'Editar projeto':'Novo projeto';
    $('catalog-status').textContent=p?`Registro: ${p.id}.json`:'Registro novo';
    state.catalogID=p?.id||'';state.catalogSHA=null;
    form.elements.namedItem('id').readOnly=!!p;
    document.querySelectorAll('.project-item').forEach(b=>b.classList.toggle('active',b.dataset.id===state.catalogID));
  }
  async function selectProject(p){
    fillCatalog(p);
    try{const f=await api('/api/file?path='+encodeURIComponent(`catalog/projects/${p.id}.json`));state.catalogSHA=f.sha256;}catch{}
  }
  async function loadCatalog(){
    const c=await api('/api/catalog');
    $('catalog-missing').hidden=c.exists;$('catalog-present').hidden=!c.exists;
    if(!c.exists)return;
    const list=$('project-list');list.replaceChildren();
    for(const p of c.projects){const b=E('button','','project-item');b.type='button';b.dataset.id=p.id;
      b.append(E('strong',p.title||p.id),E('small',`${p.id} · ${p.status}`));b.addEventListener('click',()=>selectProject(p));list.append(b);}
    if(state.catalogID){const p=c.projects.find(p=>p.id===state.catalogID);if(p)await selectProject(p);}
    $('metric-projects').textContent=c.projects.length;
    if(c.errors.length)notify(c.errors.join('\n'),true);
  }
  $('catalog-init').addEventListener('click',async()=>{try{await api('/api/catalog/init',{});notify('Catálogo vazio inicializado; arquivos originais preservados.');loadCatalog();loadFiles();}catch{}});
  $('project-new').addEventListener('click',()=>fillCatalog(null));
  $('catalog-form').addEventListener('submit',async e=>{
    e.preventDefault();
    const f=e.currentTarget.elements;
    const record={};for(const key of ['id','title','summary','status','category','url','preview','color'])record[key]=f.namedItem(key).value;
    record.topics=f.namedItem('topics').value.split(',').map(x=>x.trim()).filter(Boolean);
    record.neighbors=f.namedItem('neighbors').value.split(',').map(x=>x.trim()).filter(Boolean);
    record.expected_sha256=state.catalogSHA;
    try{const r=await api('/api/catalog/save',record);state.catalogSHA=r.sha256;state.catalogID=record.id;notify(`Projeto ${record.id} salvo sem modificar os outros registros.`);await loadCatalog();await loadState();}catch{}
  });
  $('run-checks').addEventListener('click',async()=>{
    $('run-checks').disabled=true;$('run-checks').textContent='Validando…';
    try{const r=await api('/api/validate',{});$('check-errors').textContent=r.count.errors;$('check-warnings').textContent=r.count.warnings;$('check-passed').textContent=r.count.passed;
      $('check-state').textContent=r.errors.length?'ERROS IDENTIFICADOS':r.warnings.length?'APROVADO COM AVISOS':'APROVADO';
      const box=$('check-output');box.replaceChildren();
      for(const [name,cls] of [['errors','error'],['warnings','warning'],['ok','pass']])for(const line of r[name])box.append(E('div',(cls==='error'?'ERRO · ':cls==='warning'?'AVISO · ':'OK · ')+line,'line '+cls));
      if(r.errors.length)notify(`Vistoria encontrou ${r.errors.length} erro(s).`,true);else notify('Vistoria aprovada. Revise os avisos antes do commit.');
    }catch{}finally{$('run-checks').disabled=false;$('run-checks').textContent='Executar vistoria';}
  });
  async function loadGit(){
    const r=await api('/api/git');state.git=r;
    const box=$('git-changes');box.replaceChildren();
    $('git-file-count').textContent=`${r.status.length} ARQUIVO(S)`;
    if(!r.enabled){box.append(E('p','Não há Git neste diretório. O editor e a prévia continuam funcionando.','muted'));}
    else if(!r.status.length){box.append(E('p','Nenhuma alteração no repositório.','muted'));}
    for(const item of r.status){const row=E('label','','change-item');const input=document.createElement('input');input.type='checkbox';input.value=item.path;
      row.append(input,E('b',item.state),E('span',item.path));box.append(row);}
    $('git-log').textContent=(r.commits||[]).join('\n')||'Sem histórico.';
    loadState();
  }
  $('git-refresh').addEventListener('click',loadGit);
  $('stage-all').addEventListener('click',()=>document.querySelectorAll('#git-changes input[type=checkbox]').forEach(x=>x.checked=true));
  $('stage-selected').addEventListener('click',async()=>{
    const paths=[...document.querySelectorAll('#git-changes input:checked')].map(x=>x.value);
    if(!paths.length)return notify('Selecione arquivos para adicionar ao stage.',true);
    if(!confirm(`Adicionar ${paths.length} arquivo(s) ao stage do Git?`))return;
    try{const r=await api('/api/git/stage',{paths});notify(r.message);loadGit();}catch{}
  });
  $('do-commit').addEventListener('click',async()=>{
    const message=$('commit-message').value.trim(),confirmValue=$('commit-confirm').value.trim();
    if(confirmValue!=='COMMIT')return notify('Digite COMMIT para confirmar.',true);
    if(!confirm(`Criar somente um commit LOCAL com a mensagem:\n${message}\n\nNenhum push será feito.`))return;
    try{const r=await api('/api/git/commit',{message,confirm:confirmValue});notify(r.message);$('commit-confirm').value='';await loadGit();}catch{}
  });
  $('history-load').addEventListener('click',async()=>{
    const p=$('history-path').value.trim();if(!p)return;
    try{const r=await api('/api/history?path='+encodeURIComponent(p));const box=$('history-list');box.replaceChildren();
      if(!r.history.length){box.append(E('p','Sem versões salvas pelo RD Studio.','muted'));return;}
      for(const item of r.history){const row=E('div','','history-row');const d=E('div',item.id);d.append(E('small',`${item.bytes} bytes`));const b=E('button','Restaurar','button quiet');
        b.addEventListener('click',async()=>{
          if(!confirm(`Restaurar ${p} a partir da versão ${item.id}? Uma cópia do estado atual será salva.`))return;
          try{const current=await api('/api/file?path='+encodeURIComponent(p));
            const res=await api('/api/history/restore',{path:p,id:item.id,expected_sha256:current.sha256});
            notify(`Arquivo restaurado: ${res.path}`);if(state.file===p){state.dirty=false;await openFile({path:p,type:'text'});}loadState();}catch{}
        });row.append(d,b);box.append(row);}
    }catch{}
  });
  window.addEventListener('beforeunload',e=>{if(state.dirty){e.preventDefault();e.returnValue='';}});
  // Carregamento inicial: não cria nem altera arquivos.
  loadState().catch(()=>{});
  loadPreview();
})();

// Primary workspace navigation. Legacy direct entrypoints remain available.
if(window.parent!==window&&location.origin==='http://127.0.0.1:8875')document.addEventListener('click',e=>{const a=e.target.closest('a[href]');if(!a)return;const dest=new URL(a.href);const map={'http://127.0.0.1:8791':'gil','http://127.0.0.1:8784':'video'};if(map[dest.origin]){e.preventDefault();window.parent.postMessage({protocol:'rd-workspace-1',type:'navigate',to:map[dest.origin]},'http://127.0.0.1:8877');}});
