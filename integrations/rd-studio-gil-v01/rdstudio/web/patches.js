'use strict';
(() => {
  const $=id=>document.getElementById(id);
  let selectedName='',selectedId='',plan=null,removalPlan=null;
  const request=async(route,body)=>{
    const r=await fetch(route,body===undefined ? {cache:'no-store'} : {
      method:'POST',headers:{'Content-Type':'application/json','X-RD-Token':window.STUDIO_TOKEN},
      body:JSON.stringify(body)
    });
    const result=await r.json();if(!r.ok)throw Error(result.error||'Erro HTTP '+r.status);
    return result;
  };
  function report(message,error=false){$('patch-detail').textContent=message;$('patch-detail').style.color=error?'#b33b3b':'';}
  function entry(label,value){const o=document.createElement('option');o.value=value;o.textContent=label;return o;}
  async function refresh(){
    const r=await request('/api/patches');const sel=$('patch-available');
    sel.replaceChildren(entry('Selecione um pacote',''));
    r.available.forEach(p=>sel.append(entry(p.invalid?`${p.name} (inválido)`:`${p.title} · ${p.version} · ${p.files} arquivos`,p.name)));
    if(r.available.some(x=>x.name===selectedName))sel.value=selectedName;
    const list=$('patch-installed');list.replaceChildren();
    const select=document.createElement('select');select.id='patch-installed-select';select.style.width='100%';
    select.append(entry('Selecione o pacote instalado',''));
    r.installed.forEach(p=>select.append(entry(`${p.title} (${p.id})`,p.id)));
    select.value=selectedId;
    select.addEventListener('change',()=>{selectedId=select.value;removalPlan=null;$('patch-remove').disabled=true;$('patch-removal-report').textContent='';});
    list.replaceChildren(select);return r;
  }
  $('patch-refresh').addEventListener('click',()=>refresh().catch(e=>report(e.message,true)));
  $('patch-plan').addEventListener('click',async()=>{
    selectedName=$('patch-available').value;plan=null;$('patch-apply').disabled=true;
    if(!selectedName)return report('Escolha um pacote.');
    try{
      plan=await request('/api/patches/plan',{name:selectedName});
      report([`${plan.title} · ${plan.version}`, `Situação: ${plan.ready?'PRONTO PARA APLICAR':'CONFLITO OU INSTALADO'}`,
       ...plan.files.map(f=>`${f.state==='ready'?'✓':'×'} ${f.operation==='add'?'CRIAR':'SUBSTITUIR'} ${f.path} · ${f.state}`),
       '', ...(plan.warnings||[]).map(x=>'AVISO: '+x), '',plan.notes||'',
       '', '--- DIFF DE CADA ARQUIVO ---', ...plan.files.filter(x=>x.diff).map(x=>x.diff)
       ].join('\n'));
      $('patch-apply').disabled=!plan.ready;
    }catch(e){report(e.message,true);}
  });
  $('patch-apply').addEventListener('click',async()=>{
    if(!plan||!plan.ready)return;
    if(!confirm(`Aplicar ${plan.title} aos ${plan.files.length} arquivos listados? O site publicado não será modificado.`))return;
    try{const r=await request('/api/patches/apply',{name:plan.name,confirm:'APLICAR'});report(`${r.message}\n\n${r.files.join('\n')}`);$('patch-apply').disabled=true;await refresh();}
    catch(e){report(e.message,true);}
  });
  $('patch-remove-plan').addEventListener('click',async()=>{
    selectedId=$('patch-installed-select')?.value||'';$('patch-remove').disabled=true;removalPlan=null;
    if(!selectedId)return $('patch-removal-report').textContent='Selecione um pacote instalado.';
    try{removalPlan=await request('/api/patches/remove/plan?id='+encodeURIComponent(selectedId));
      $('patch-removal-report').textContent=(removalPlan.ready?'Remoção segura:\n':'Bloqueada por alterações posteriores:\n')+removalPlan.files.map(f=>`${f.state==='ready'?'✓':'×'} ${f.operation} ${f.path}`).join('\n');
      $('patch-remove').disabled=!removalPlan.ready;
    }catch(e){$('patch-removal-report').textContent=e.message;}
  });
  $('patch-remove').addEventListener('click',async()=>{
    if(!removalPlan?.ready)return;
    if(!confirm(`Remover ${removalPlan.title} e restaurar os arquivos anteriores? Essa ação é somente local.`))return;
    try{const r=await request('/api/patches/remove',{id:removalPlan.id,confirm:'REMOVER'});
      $('patch-removal-report').textContent=r.message;selectedId='';removalPlan=null;$('patch-remove').disabled=true;await refresh();}
    catch(e){$('patch-removal-report').textContent=e.message;}
  });
  document.querySelector('[data-tab="patches"]').addEventListener('click',()=>refresh().catch(e=>report(e.message,true)));
})();
