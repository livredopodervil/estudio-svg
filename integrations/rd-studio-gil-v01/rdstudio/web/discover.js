'use strict';
(() => {
  const $=id=>document.getElementById(id);
  const E=(tag,text='',cls='')=>{const e=document.createElement(tag);e.textContent=text;if(cls)e.className=cls;return e;};
  const state={current:'',items:[],candidates:[],selected:null,compare:null,installed:[]};
  async function api(url,data){
    let opts={};
    if(data!==undefined)opts={method:'POST',headers:{'Content-Type':'application/json','X-RD-Token':window.STUDIO_TOKEN},body:JSON.stringify(data)};
    const r=await fetch(url,opts),result=await r.json();
    if(!r.ok)throw Error(result.error||('HTTP '+r.status));
    return result;
  }
  function feedback(text,error=false){$('discover-status').textContent=text;$('discover-status').className='discover-feedback'+(error?' danger':'');}
  async function task(fn){try{await fn();}catch(e){feedback(e.message,true);}}
  function fmt(n){return n==null?'':n<1024?`${n} B`:n<1048576?`${Math.round(n/1024)} KB`:`${(n/1048576).toFixed(1)} MB`;}
  function cardBtn(label,cb,cls='subtle'){const b=E('button',label,'button '+cls);b.type='button';b.onclick=cb;return b;}
  async function browse(path){
    const data=await api('/api/discover/browse?path='+encodeURIComponent(path||''));
    state.current=data.path;state.items=data.items;
    $('discover-path').textContent=data.path;
    $('discover-folder').value=data.path;
    const view=$('discover-folders');view.replaceChildren();
    if(data.parent)view.append(cardBtn('.. Diretório superior',()=>task(()=>browse(data.parent))));
    for(const item of data.items){
      const row=E('div','','discover-file');
      const symbol=item.dir?'▣ ':'▤ ';
      const button=E('button',symbol+item.name+(item.dir?'/':''));button.type='button';button.title=item.path;
      if(item.dir)button.onclick=()=>task(()=>browse(item.path));
      else button.onclick=()=>{feedback('Arquivo: '+item.path+' (somente leitura nesta área; edite via Arquivos após importar)');};
      const info=E('small',item.candidate?'HTML detectado':item.dir?'pasta':fmt(item.bytes));
      row.append(button,info);view.append(row);
    }
    if(!data.items.length)view.append(E('p','Nenhum diretório ou recurso publicável nesta pasta.','hint'));
    $('discover-counts').textContent=`${data.items.length} itens · navegação restrita a HOME`;
  }
  async function scan(){
    feedback('Analisando subdiretórios...');
    const root=$('discover-folder').value.trim()||state.current;
    const depth=Number($('discover-depth').value);
    const r=await api('/api/discover/scan',{root,depth});
    state.candidates=r.candidates;
    $('discover-results').replaceChildren();
    $('discover-summary').textContent=`${r.total} projetos detectados em ${r.visited_directories} diretórios · ${r.groups} grupos${r.truncated?' · busca limitada':''}`;
    for(const c of r.candidates){
      const row=E('div','','discover-candidate'+(c.path===state.selected?.path?' selected':''));
      const heading=E('strong',c.title);
      const meta=E('small',`${c.kind} · ${c.name} · grupo: ${c.group}${c.group_count>1?' ('+c.group_count+' versões)':''}`);
      const action=cardBtn('Selecionar',()=>select(c));
      row.append(heading,meta,action);$('discover-results').append(row);
    }
    if(!r.total)$('discover-results').append(E('p','Nenhum aplicativo identificado. Navegue até uma pasta mais específica ou aumente a profundidade.','hint'));
    refreshCompareSelectors();
    feedback(`Varredura concluída: ${r.total} candidatos. Nada foi alterado.`);
  }
  function refreshCompareSelectors(){
    for(const id of ['compare-a','compare-b']){
      const el=$(id),old=el.value;el.replaceChildren();
      for(const c of state.candidates){const o=E('option',`${c.name} — ${c.kind}`);o.value=c.path;el.append(o);}
      if([...el.options].some(o=>o.value===old))el.value=old;
    }
    if(state.candidates.length>=2){
      $('compare-a').value=state.candidates[0].path;
      $('compare-b').value=state.candidates[1].path;
    }
  }
  function select(c){
    state.selected=c;
    document.querySelectorAll('.discover-candidate').forEach(x=>x.classList.remove('selected'));
    $('discover-selected').textContent=c.title;
    $('discover-inspect').textContent=`${c.kind}\n${c.path}\n${c.description||'Sem descrição HTML'}\nGit: ${c.git?'sim':'não'} · versão: ${c.version_hint||'não identificada'}`;
    $('discover-id').value=c.id_suggested;
    $('discover-import').disabled=!c.static;
    $('discover-import-hint').textContent=c.static?'Contém index.html: importação possível.':'Sem index.html na raiz: precisa ser exportado como site estático antes de importar.';
    $('discover-source').value=c.path;
    feedback('Selecionado: '+c.name+'. Compare versões ou importe para o worktree de teste.');
  }
  async function compare(){
    const a=$('compare-a').value,b=$('compare-b').value;
    if(!a||!b||a===b)throw Error('Escolha duas pastas distintas');
    const r=await api('/api/discover/compare',{a,b});state.compare=r;
    $('discover-diff-summary').textContent=`A: ${r.total_a} arquivos · B: ${r.total_b} arquivos · ${r.added.length} novos · ${r.removed.length} removidos · ${r.changed.length} modificados · ${r.unchanged} iguais`;
    const report=`NOVOS EM B\n${r.added.join('\n')||'—'}\n\nREMOVIDOS EM B\n${r.removed.join('\n')||'—'}\n\nALTERADOS\n${r.changed.join('\n')||'—'}\n\nDIFF DE ${r.focus||'—'}\n${r.diff||'Sem diff textual'}`;
    $('discover-diff').textContent=report;
    feedback('Comparação concluída; nenhuma pasta foi modificada.');
  }
  async function importSelected(){
    const c=state.selected;if(!c||!c.static)throw Error('Escolha um projeto HTML');
    const id=$('discover-id').value.trim();
    const plan=await api('/api/import/plan',{source:c.path,id});
    if(!confirm(`Importar ${plan.files} arquivos (${fmt(plan.bytes)})${plan.review_warnings?.length?"\n\nAVISOS: "+plan.review_warnings.join("; "):""} de:\n${plan.source}\n\npara ${plan.dest}?\nSem alterar a origem ou publicar.`))return;
    if(prompt('Digite IMPORTAR para confirmar:')!=='IMPORTAR')return;
    const r=await api('/api/import/apply',{source:plan.source,id:plan.id,fingerprint:plan.fingerprint,confirm:'IMPORTAR'});
    feedback(r.message);$('discover-id').value=id;
    await loadInstalled();
    const v=await api('/api/discover/visual/plan?id='+encodeURIComponent(id));showVisualPlan(v);
  }
  async function loadInstalled(){
    const r=await api('/api/catalog');state.installed=r.projects;
    const select=$('discover-installed'),old=select.value;
    select.replaceChildren();
    for(const p of r.projects){
      const o=E('option',`${p.title} (${p.id})`);o.value=p.id;select.append(o);
    }
    if([...select.options].some(o=>o.value===old))select.value=old;
  }
  function showVisualPlan(r){
    $('discover-assets').replaceChildren();
    $('discover-visual-mode').textContent=r.method+' · '+(r.pillow?'Pillow ativo':'Pillow indisponível, SVG')+' · '+(r.screenshot_available?'navegador presente':'captura real indisponível');
    const select=$('discover-assets');
    const none=E('option','Criar arte tipográfica (sem screenshot)');none.value='';select.append(none);
    for(const candidate of r.candidates){const opt=E('option',candidate);opt.value=candidate;select.append(opt);}
    if(r.default)select.value=r.default;
    $('discover-visual-id').value=r.id;
    $('discover-visual-title').value=r.title;
    $('discover-generate').disabled=false;
  }
  async function visualPlan(){
    const id=$('discover-visual-id').value.trim()||$('discover-id').value.trim();
    const p=await api('/api/discover/visual/plan?id='+encodeURIComponent(id));showVisualPlan(p);
    feedback('Recursos identificados. Escolha uma imagem ou a arte tipográfica e gere os arquivos.');
  }
  let capturePlan=null;
  async function inspectCapture(){
    const id=$('discover-visual-id').value.trim();
    const r=await api('/api/discover/capture/plan?id='+encodeURIComponent(id));
    capturePlan=r;
    $('discover-capture').disabled=!r.available;
    feedback(r.available?`Chromium detectado: captura disponível em ${r.url}`:'Sem Chromium headless detectado; use imagem existente ou SVG.');
  }
  async function doCapture(){
    if(!capturePlan?.available)return;
    if(prompt(`Capturar ${capturePlan.url} usando Chromium local? Digite CAPTURAR:`)!=='CAPTURAR')return;
    const r=await api('/api/discover/capture/apply',{id:capturePlan.id,confirm:'CAPTURAR'});
    const target=$('discover-visual-result');target.replaceChildren();
    const a=E('a',r.path);a.href=`http://127.0.0.1:${window.PREVIEW_PORT}${r.path}`;a.target='_blank';a.rel='noopener';target.append(a);
    feedback(r.message);
  }
  async function visualApply(){
    const id=$('discover-visual-id').value.trim();if(!id)throw Error('Informe o ID');
    const source=$('discover-assets').value;
    if(!confirm(`Gerar miniatura e ícone de ${id} usando ${source||'arte tipográfica'}?\nOs arquivos existentes receberão backup.`))return;
    const result=await api('/api/discover/visual/apply',{id,source,title:$('discover-visual-title').value,confirm:'GERAR'});
    $('discover-visual-result').replaceChildren(E('p','Arquivos gerados no worktree:'));
    const list=E('ul');for(const path of result.generated){const li=E('li');const a=E('a',path);a.href=`http://127.0.0.1:${window.PREVIEW_PORT}${path}`;a.target='_blank';a.rel='noopener';li.append(a);list.append(li);}
    $('discover-visual-result').append(list);
    feedback('Miniatura e ícone criados e registrados no catálogo. Não houve publicação.');
  }
  let replacement=null;
  async function replacePlan(){
    const id=$('discover-installed').value;
    const source=state.selected?.path||$('discover-source').value.trim();
    if(!id||!source)throw Error('Selecione uma origem e um projeto instalado');
    const result=await api('/api/discover/replace/plan',{id,source});replacement=result;
    $('discover-replace-report').textContent=`ORIGEM ${result.source}\nDESTINO ${result.dest}\n${result.files} arquivos\n\nNOVOS (${result.added.length})\n${result.added.join('\n')||'—'}\n\nREMOVIDOS (${result.removed.length})\n${result.removed.join('\n')||'—'}\n\nALTERADOS (${result.changed.length})\n${result.changed.join('\n')||'—'}\n\nIGUAIS ${result.same}\n\nBackup externo obrigatório.`;
    $('discover-replace').disabled=false;
    feedback('Plano de substituição pronto; nenhuma alteração foi realizada.');
  }
  async function replaceApply(){
    if(!replacement)throw Error('Gere o plano primeiro');
    const p=replacement;
    if(prompt(`Esta ação substituirá ${p.dest} SOMENTE no worktree, preservando backup.\nDigite SUBSTITUIR ${p.id}:`)!==`SUBSTITUIR ${p.id}`)return;
    const r=await api('/api/discover/replace/apply',{source:p.source,id:p.id,fingerprint:p.fingerprint,confirm:`SUBSTITUIR ${p.id}`});
    feedback(r.message+' Backup: '+r.backup);$('discover-replace').disabled=true;replacement=null;
  }
  async function portfolio(){
    if(prompt('Gerar a página /projetos/ localmente? Digite GERAR PORTFOLIO:')!=='GERAR PORTFOLIO')return;
    const r=await api('/api/discover/portfolio/generate',{confirm:'GERAR PORTFOLIO',link_home:$('discover-link-home').checked});
    $('discover-portfolio-link').href=`http://127.0.0.1:${window.PREVIEW_PORT}/projetos/`;
    feedback(r.message+(r.linked_home?' Link incluído na home.':'')+(r.warning?' '+r.warning:''));
  }
  async function running(){
    const r=await api('/api/discover/running');const target=$('discover-running');target.replaceChildren();
    target.append(E('h3',`Portas TCP acessíveis: ${r.ports.length}`));
    for(const p of r.ports){const el=E('div','','discover-file'),a=E('a',p.url);a.href=p.url;a.target='_blank';a.rel='noopener';el.append(a,E('small',p.kind));target.append(el);}
    target.append(E('h3',`Processos de desenvolvimento identificados: ${r.processes.length}`));
    for(const p of r.processes){
      const el=E('div','','discover-file');el.append(E('span',`PID ${p.pid} · ${p.program}${p.port_hint?' · porta sugerida '+p.port_hint:''}`),E('small',p.paths.join(' · ')||'pasta não identificada'));target.append(el);
    }
    target.append(E('p',r.note,'hint'));
    feedback('Processos e portas inspecionados sem interrompê-los.');
  }
  for(const [id,fun] of Object.entries({
    'discover-up':()=>browse(state.current?state.current.replace(/\/[^/]+$/,''):'') ,
    'discover-home':()=>browse(''),
    'discover-scan':scan,'discover-compare':compare,'discover-import':importSelected,
    'discover-visual-plan':visualPlan,'discover-generate':visualApply,
    'discover-capture-plan':inspectCapture,'discover-capture':doCapture,
    'discover-replace-plan':replacePlan,'discover-replace':replaceApply,
    'discover-running-refresh':running,'discover-portfolio':portfolio,
  }))$(id).addEventListener('click',()=>task(fun));
  $('discover-folder').addEventListener('keydown',e=>{if(e.key==='Enter')task(()=>browse($('discover-folder').value.trim()));});
  $('discover-open-path').addEventListener('click',()=>task(()=>browse($('discover-folder').value.trim())));
  let begun=false;
  document.querySelectorAll('[data-tab="discover"]').forEach(b=>b.addEventListener('click',()=>{
    if(!begun){begun=true;task(async()=>{await browse('');await loadInstalled();await running();});}
  }));
})();
