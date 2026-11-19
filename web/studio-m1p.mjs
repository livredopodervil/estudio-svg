// M1P Studio: project folders, batch captions, per-scene element inspector.
// Does not mutate a project without explicit user gesture.
export function gilTextObjects(source) {
  const result=[];
  for (const [index,line] of String(source||'').split('\n').entries()) {
    const m=/^\s*object\s+([A-Za-z_][\w-]*)\s+([\w.-]+)\s+(?:-|[\w-]+)\s+(\{.*\})\s*$/.exec(line);
    if (!m) continue;
    try { const props=JSON.parse(m[3]);if(typeof props.text==='string')result.push({index,id:m[1],text:props.text,resource:m[2]});}catch{}
  }
  return result;
}
export function changeGilText(source,index,value) {
  const lines=String(source).split('\n');
  if (!Number.isSafeInteger(index)||index<0||index>=lines.length) throw Error('Linha GIL inexistente');
  const old=lines[index], match=/^(\s*object\s+[A-Za-z_][\w-]*\s+[\w.-]+\s+(?:-|[\w-]+)\s+)(\{.*\})(\s*)$/.exec(old);
  if (!match)throw Error('Objeto GIL mudou');
  const props=JSON.parse(match[2]);if(typeof props.text!=='string')throw Error('Objeto não é texto');
  props.text=String(value).slice(0,250);
  lines[index]=match[1]+JSON.stringify(props)+match[3];
  return lines.join('\n');
}
export function applySubtitleStyleAll(project, index){
  if (!Array.isArray(project?.cenas)) throw Error('Projeto inválido');
  const source=project.cenas[index]?.legendas;
  if (!source) throw Error('Configure as legendas de uma cena primeiro');
  // Timings are unique to each scene and must never be duplicated.
  const allowed=['enabled','mode','effect','position','font_scale','max_words','text_color','highlight_color','background_color','background_opacity'];
  let changed=0;
  for(const s of project.cenas){
    const old=s.legendas||{};
    const next={...old};
    for(const key of allowed)if(Object.hasOwn(source,key))next[key]=source[key];
    next.enabled=true;
    if(JSON.stringify(old)!==JSON.stringify(next)){s.legendas=next;changed++;}
  }
  return changed;
}
export function svgItemList(source){
  if(typeof DOMParser==='undefined')throw Error('DOM SVG indisponível');
  const parser=new DOMParser(), xml=parser.parseFromString(`<svg xmlns="http://www.w3.org/2000/svg">${String(source||'')}</svg>`,'image/svg+xml');
  if(xml.querySelector('parsererror'))throw Error('SVG inválido: confira a fonte');
  const nodes=[...xml.documentElement.querySelectorAll('g,rect,circle,ellipse,line,path,polygon,polyline,text,image,use')];
  return nodes.map((el,index)=>({index,tag:el.localName,id:el.getAttribute('id')||'',text:(el.textContent||'').trim().slice(0,85)}));
}
export function modifySvgItem(source,index,op,value=''){
  const parser=new DOMParser(),xml=parser.parseFromString(`<svg xmlns="http://www.w3.org/2000/svg">${String(source||'')}</svg>`,'image/svg+xml');
  if(xml.querySelector('parsererror'))throw Error('SVG inválido');
  const nodes=[...xml.documentElement.querySelectorAll('g,rect,circle,ellipse,line,path,polygon,polyline,text,image,use')];
  const el=nodes[index];if(!el)throw Error('Elemento mudou ou desapareceu');
  if(op==='remove')el.remove();
  else if(op==='hide')el.setAttribute('display','none');
  else if(op==='show')el.removeAttribute('display');
  else if(op==='text'){
    if(el.localName!=='text')throw Error('Selecione um elemento de texto');
    el.textContent=String(value).slice(0,300);
  }else if(op==='attribute'){
    const [attr,attrvalue]=value;
    if(!/^(?:x|y|cx|cy|r|rx|ry|x1|y1|x2|y2|width|height|opacity|stroke-width|font-size|fill|stroke|transform)$/.test(attr))throw Error('Atributo não permitido');
    if(attr==='fill'||attr==='stroke'){
      if(!/^(?:#[0-9a-fA-F]{3,8}|[a-zA-Z]{2,20}|none)$/.test(attrvalue))throw Error('Cor inválida');
    }else if(attr==='transform'){
      if(!/^(?:(?:translate|scale|rotate)\(\s*[-\d., eE]+\s*\)\s*){1,4}$/.test(attrvalue))throw Error('Transformação inválida');
    }else if(!Number.isFinite(Number(attrvalue))||String(attrvalue).length>25)throw Error('Número inválido');
    el.setAttribute(attr,String(attrvalue));
  }else throw Error('Operação desconhecida');
  const s=new XMLSerializer();
  return [...xml.documentElement.childNodes].map(el=>s.serializeToString(el)).join('');
}

export function installStudioM1P(api){
  const {getProject,getSelected,getProjectName,getProjectCatalog,save,load,listProjects,dirtyNow,drawEverything,toast,begin,busy}=api;
  const css=document.createElement('style');css.textContent=`
  .m1pDialog{border:1px solid #756251;border-radius:16px;background:#211c20;color:#faf0e4;max-width:min(92vw,650px);max-height:85vh;overflow:auto;padding:16px}
  .m1pDialog::backdrop{background:#000a}.m1pGrid{display:grid;gap:10px}.m1pRow{display:flex;align-items:center;gap:6px;flex-wrap:wrap;padding:8px;border-bottom:1px solid #665647}
  .m1pRow span{flex:1;min-width:120px;overflow-wrap:anywhere}.m1pDialog button{font-size:14px;min-height:36px}
  .m1pDialog select{max-width:100%;background:#241f1c;color:#fff;padding:8px}.m1pActions{display:flex;gap:6px;flex-wrap:wrap}`;
  document.head.append(css);
  const dialog=document.createElement('dialog');dialog.className='m1pDialog';dialog.id='m1pInspector';document.body.append(dialog);
  const manager=document.createElement('dialog');manager.className='m1pDialog';manager.id='m1pProjectManager';document.body.append(manager);
  async function request(url,payload){const r=await fetch(url,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});const data=await r.json();if(!r.ok)throw Error(data.error||'Falha HTTP '+r.status);return data;}
  async function catalogue(){const r=await fetch('/api/projects');if(!r.ok)throw Error('Não foi possível consultar projetos');return r.json();}
  function selectScene(activeIndex){const select=document.createElement('select');getProject().cenas.forEach((c,i)=>select.add(new Option(`${i+1}. ${c.titulo||c.id}`,i)));select.value=String(activeIndex);select.onchange=()=>renderInspector(Number(select.value));return select;}
  function label(text){const s=document.createElement('span');s.textContent=text;return s;}
  function btn(text,fn){const b=document.createElement('button');b.type='button';b.textContent=text;b.onclick=async()=>{try{await fn();}catch(e){toast(e.message,true);}};return b;}
  function commitScene(){dirtyNow(true,'m1p-elements');renderInspector(sceneIndex);}
  let sceneIndex=0;
  function renderInspector(i){
    const pr=getProject();if(!pr)return;sceneIndex=i;
    const sc=pr.cenas[i],outer=document.createElement('div');outer.className='m1pGrid';
    const top=document.createElement('div');top.className='m1pRow';top.append(label('Cena'),selectScene(i),btn('Fechar',()=>dialog.close()));outer.append(top);
    const intro=document.createElement('p');intro.textContent='Os campos da cena, os elementos SVG e os títulos GIL são independentes. Remover um título não remove o projeto nem a narração.';outer.append(intro);
    for(const [key,description] of [['titulo','Título da cena'],['subtitulo','Subtítulo da cena'],['categoria','Selo'],['fonte','Fonte'],['valor','Valor'],['unidade','Unidade'],['destaque','Destaque']]){
      if(typeof sc[key]!=='string'||(!sc[key]&&!['titulo','subtitulo'].includes(key)))continue;
      const row=document.createElement('div');row.className='m1pRow';row.append(label(`${description}: ${sc[key].slice(0,80)||'(vazio)'}`),btn('Editar',()=>{const value=prompt(description,sc[key]);if(value===null)return;sc[key]=value.slice(0,400);commitScene();}),btn('Remover',()=>{sc[key]='';commitScene();}));outer.append(row);
    }
    const assets=[['imagem',sc.imagem?.arquivo],['vídeo',sc.video_clipe?.arquivo],['camada GIL nativa',!!sc.gil_nativo]];
    for(const [kind,value] of assets){if(!value)continue;const row=document.createElement('div');row.className='m1pRow';row.append(label(`${kind}: ${value===true?'presente':value}`),btn('Desvincular',()=>{if(!confirm('Desvincular '+kind+' desta cena? O arquivo original será preservado.'))return;if(kind==='imagem')sc.imagem.arquivo='';if(kind==='vídeo')sc.video_clipe.arquivo='';if(kind==='camada GIL nativa')delete sc.gil_nativo;commitScene();}));outer.append(row);}
    if(Array.isArray(sc.objetos_midia))for(const [i,obj] of sc.objetos_midia.entries()){
      const row=document.createElement('div');row.className='m1pRow';row.append(label(`Objeto ${obj.id}: ${obj.label||obj.kind}`),btn('Renomear',()=>{const value=prompt('Rótulo do objeto',obj.label||'');if(value!==null){obj.label=value.slice(0,100);commitScene();}}),btn('Remover',()=>{if(!confirm('Remover objeto da cena?'))return;sc.objetos_midia.splice(i,1);commitScene();}));outer.append(row);
    }
    try{for(const obj of svgItemList(sc.svg)){const row=document.createElement('div');row.className='m1pRow';row.append(label(`SVG <${obj.tag}> ${obj.id?('#'+obj.id):''} ${obj.text}`),btn('Editar',()=>{
      let op='text',value;if(obj.tag==='text'){value=prompt('Conteúdo do texto',obj.text);if(value===null)return;}else{
        const attr=prompt('Atributo (x, y, width, fill, opacity, transform, etc.)','opacity');if(attr===null)return;const val=prompt('Novo valor do atributo','1');if(val===null)return;op='attribute';value=[attr,val];
      }sc.svg=modifySvgItem(sc.svg,obj.index,op,value);commitScene();}),btn('Ocultar',()=>{sc.svg=modifySvgItem(sc.svg,obj.index,'hide');commitScene();}),btn('Remover',()=>{if(!confirm('Remover o elemento SVG desta cena?'))return;sc.svg=modifySvgItem(sc.svg,obj.index,'remove');commitScene();}));outer.append(row);}}
    catch(e){outer.append(label('SVG não pôde ser inspecionado: '+e.message));}
    const source=sc.gil_nativo?.source;
    if(source)for(const obj of gilTextObjects(source)){
      const row=document.createElement('div');row.className='m1pRow';row.append(label(`GIL ${obj.id}: ${obj.text||'(vazio)'}`),btn('Editar',async()=>{
        const value=prompt('Texto GIL',obj.text);if(value===null)return;
        const next=changeGilText(sc.gil_nativo.source,obj.index,value);
        const {compile}=await import('/gil-runtime/src/model.mjs');compile(next);
        const bytes=new TextEncoder().encode(next),hash=await crypto.subtle.digest('SHA-256',bytes);
        sc.gil_nativo.source=next;sc.gil_nativo.source_sha256=[...new Uint8Array(hash)].map(b=>b.toString(16).padStart(2,'0')).join('');commitScene();
      }),btn('Remover texto',async()=>{
        const next=changeGilText(sc.gil_nativo.source,obj.index,'');
        const {compile}=await import('/gil-runtime/src/model.mjs');compile(next);
        const digest=await crypto.subtle.digest('SHA-256',new TextEncoder().encode(next));
        sc.gil_nativo.source=next;sc.gil_nativo.source_sha256=[...new Uint8Array(digest)].map(b=>b.toString(16).padStart(2,'0')).join('');commitScene();
      }));outer.append(row);
    }
    dialog.replaceChildren(outer);
  }
  async function renderManager(){
    const data=await catalogue(),root=document.createElement('div');root.className='m1pGrid';
    const title=document.createElement('h3');title.textContent='Projetos e diretórios físicos';root.append(title);
    root.append(btn('Criar diretório',async()=>{const folder=prompt('Nome do novo diretório (letras, números, _ e -):');if(!folder)return;await request('/api/project/manage',{action:'mkdir',folder});await renderManager();}));
    const info=document.createElement('p');info.textContent='Renomear ou mover não altera as mídias compartilhadas. Excluir envia para a lixeira recuperável.';root.append(info);
    for(const name of data.projects){const row=document.createElement('div');row.className='m1pRow',folder=data.folders[name]||'';row.append(label(`${name} · ${folder||'Projetos'}`));
      row.append(btn('Abrir',async()=>{await load(name);manager.close();}),btn('Renomear',async()=>{
        const target=prompt('Novo identificador (sem espaços):',name);if(!target||target===name)return;if(!confirm(`Renomear ${name} para ${target}?`))return;
        if(name===getProjectName())await save();await request('/api/project/manage',{action:'rename',name,new_name:target,confirm:name});await listProjects();if(name===getProjectName())await load(target);await renderManager();
      }),btn('Mover',async()=>{
        const target=prompt('Diretório de destino (vazio = raiz):',folder);if(target===null)return;
        if(name===getProjectName())await save();await request('/api/project/manage',{action:'move',name,folder:target,confirm:name});await listProjects();await renderManager();
      }),btn('Lixeira',async()=>{
        if(!confirm('Mover '+name+' para a lixeira recuperável?'))return;
        if(name===getProjectName())await save();await request('/api/project/manage',{action:'trash',name,confirm:name});const names=await listProjects();if(name===getProjectName()&&names.length)await load(names[0]);await renderManager();
      }));root.append(row);
    }
    const trash=document.createElement('h4');trash.textContent='Lixeira';root.append(trash);
    for(const item of data.trash||[]){const row=document.createElement('div');row.className='m1pRow';row.append(label(`${item.name} · ${item.folder||'Projetos'}`),btn('Restaurar',async()=>{await request('/api/project/manage',{action:'restore',token:item.token});await listProjects();await renderManager();}));root.append(row);}
    root.append(btn('Fechar',()=>manager.close()));manager.replaceChildren(root);
  }
  const browser=document.getElementById('projectBrowser');if(browser){const b=btn('Gerenciar · renomear / mover / excluir',async()=>{await renderManager();manager.showModal();});browser.append(b);}
  const folderSelect=document.getElementById('projectBrowserFolder');if(folderSelect){folderSelect.onchange=async()=>{try{await save();await request('/api/project/manage',{action:'move',name:getProjectName(),folder:folderSelect.value,confirm:getProjectName()});await listProjects();toast('Projeto movido fisicamente para a pasta');}catch(e){toast(e.message,true);}};}
  const newFolder=document.getElementById('newProjectFolder');if(newFolder){newFolder.onclick=async()=>{const folder=prompt('Nome da pasta física (sem espaços):');if(!folder)return;try{await save();await request('/api/project/manage',{action:'mkdir',folder});await request('/api/project/manage',{action:'move',name:getProjectName(),folder,confirm:getProjectName()});await listProjects();toast('Diretório criado e projeto movido');}catch(e){toast(e.message,true);}};}
  document.addEventListener('click',e=>{
    const t=e.target;if(!(t instanceof Element))return;
    if(t.id==='m1pSceneInspector'){renderInspector(getSelected());dialog.showModal();}
    if(t.id==='m1pCaptionStyleAll'){
      if(busy()){toast('Conclua a tarefa em andamento.',true);return;}
      if(!confirm('Aplicar aparência/efeito das legendas desta cena a todas as cenas, preservando seus tempos individuais?'))return;
      const n=applySubtitleStyleAll(getProject(),getSelected());dirtyNow(true,'m1p-caption-batch');toast('Configurações aplicadas a '+n+' cenas. Salve o projeto.');
    }
    if(t.id==='m1pGenerateTimingsBatch'){
      if(busy()){toast('Já existe produção em andamento.',true);return;}
      if(!confirm('Gerar em lote a narração e os tempos por palavra de todas as cenas habilitadas? A locução em cache pode ser regenerada.'))return;
      begin('legendas-lote');
    }
  });
}
