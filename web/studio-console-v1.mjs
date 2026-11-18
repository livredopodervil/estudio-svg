// M1i — console incremental reutilizando o MESMO plano 0.4 e commit do catálogo.
import {StudioCommandRegistry,parseStudioConsoleLine} from './studio-command-registry-v1.mjs';

export function createStudioConsoleRuntime({getProject,planInput,simulateButton,applyButton,report,validateProjectPlan}) {
  if (![getProject,validateProjectPlan].every(x=>typeof x==='function') ||
      !planInput || !simulateButton || !applyButton || !report)
    throw new Error('Adaptador do editor incompleto');
  const registry=new StudioCommandRegistry();
  const project=()=>{const p=getProject();if(!p || !Array.isArray(p.cenas))throw Error('Abra um projeto antes de usar o console');return p;};
  const expectation=()=>{const p=project();return {title:p.titulo,scene_ids:p.cenas.map(s=>s.id)};};
  const blank=()=>({format:'rd-studio-project-plan-0.4',expect:expectation(),operations:[]});
  const read=()=>planInput.value.trim()?validateProjectPlan(planInput.value):blank();
  const set=(plan)=>{const validated=validateProjectPlan(JSON.stringify(plan));planInput.value=JSON.stringify(validated,null,2);planInput.dispatchEvent(new Event('input',{bubbles:true}));return validated;};
  const checkArgs=(args,allowed)=>{for(const key of Object.keys(args))if(!allowed.includes(key))throw Error('Argumento não suportado: '+key);};
  const add=(op)=>{
    const plan=read();
    if(plan.format!=='rd-studio-project-plan-0.4')throw Error('Formato de plano diferente de 0.4');
    if(JSON.stringify(plan.expect)!==JSON.stringify(expectation()))throw Error('Plano associado a outra revisão de projeto; limpe-o ou revalide');
    const next={...plan,operations:[...plan.operations,op]};
    set(next);
    return {staged:next.operations.length,operation:op,mutated:false};
  };
  registry.register('studio.project',()=>{const p=project();return {title:p.titulo,scenes:p.cenas.length,format:p.versao||null};},{kind:'query',description:'Identificação do projeto atual'});
  registry.register('studio.scenes',()=>project().cenas.map((s,i)=>({index:i,id:s.id,title:s.titulo,duration:s.duracao,type:s.tipo})),{kind:'query',description:'Listar cenas e seus IDs'});
  registry.register('studio.scene',({id})=>{if(typeof id!=='string'||!id)throw Error('Informe id');const s=project().cenas.find(x=>x.id===id);if(!s)throw Error('Cena não encontrada: '+id);return {id:s.id,title:s.titulo,subtitle:s.subtitulo,duration:s.duracao,type:s.tipo};},{kind:'query',description:'Inspecionar cena por ID'});
  registry.register('studio.commands',()=>registry.list(),{kind:'query',description:'Listar capacidades do console'});
  registry.register('studio.plan',()=>({plan:read(),previewAvailable:!applyButton.disabled}),{kind:'query',description:'Ler plano incremental atual'});
  registry.register('studio.plan.add',(op)=>add(op),{kind:'command',description:'Adicionar operação JSON 0.4 ao plano (sem mutação)'});
  registry.register('studio.scene.text',(args)=>{checkArgs(args,['id','field','text']);return add({type:'scene.text',...args});},{kind:'command',description:'Propor alteração textual de uma cena'});
  registry.register('studio.scene.duration',(args)=>{checkArgs(args,['id','seconds']);return add({type:'scene.duration',...args});},{kind:'command',description:'Propor duração de cena'});
  registry.register('studio.plan.replace',(args)=>{const plan=set(args);return {staged:plan.operations.length,mutated:false};},{kind:'command',description:'Substituir plano por documento JSON 0.4 validado'});
  registry.register('studio.plan.clear',()=>{planInput.value='';planInput.dispatchEvent(new Event('input',{bubbles:true}));return {staged:0,mutated:false};},{kind:'command',description:'Descartar apenas operações ainda não aplicadas'});
  registry.register('studio.plan.preview',()=>{
    simulateButton.click();
    if(report.textContent.startsWith('Recusado:'))throw Error(report.textContent);
    return {report:report.textContent,previewAvailable:!applyButton.disabled,mutated:false};
  },{kind:'command',description:'Simular o plano no motor atual, sem alterar projeto'});
  registry.register('studio.plan.apply',()=>{
    if(applyButton.disabled)throw Error('Simule primeiro e obtenha um plano aplicável');
    // A UI já exige confirmação e verifica snapshot/plano antes do commit único.
    applyButton.click();
    return {report:report.textContent,applied:report.textContent.startsWith('Operações aplicadas'),note:'A confirmação, o histórico e o salvamento pertencem ao editor.'};
  },{kind:'command',description:'Solicitar confirmação e aplicar o plano pela UI existente'});
  return Object.freeze({registry,run(line){const parsed=parseStudioConsoleLine(line);return parsed.help?registry.list():registry.execute(parsed.kind,parsed.id,parsed.args);}});
}

export function installStudioConsole({dlg,getProject,validateProjectPlan}) {
  if(dlg.querySelector('#rdConsoleM1i'))return;
  const q=x=>dlg.querySelector(`[data-${x}]`);
  const runtime=createStudioConsoleRuntime({getProject,validateProjectPlan,planInput:q('plan'),simulateButton:q('simulate'),applyButton:q('apply'),report:q('report')});
  const section=document.createElement('section');section.id='rdConsoleM1i';
  const heading=document.createElement('h3');heading.textContent='Console incremental · M1i';
  const tip=document.createElement('p');tip.textContent='Mesmo plano 0.4 do Catálogo + Agente. Consulte o projeto; prepare, simule e confirme alterações. Nenhum comando executa JavaScript ou shell.';
  const bar=document.createElement('div');bar.style.cssText='display:flex;flex-wrap:wrap;gap:8px;align-items:center';
  const input=document.createElement('input');input.type='text';input.autocomplete='off';input.spellcheck=false;
  input.setAttribute('aria-label','Comando incremental');input.placeholder='runtime query studio.scenes';
  input.style.cssText='flex:1 1 260px;min-width:0;font:13px ui-monospace,monospace';
  const execute=document.createElement('button');execute.type='button';execute.textContent='Executar';
  const help=document.createElement('button');help.type='button';help.textContent='Ajuda';
  const output=document.createElement('pre');output.setAttribute('role','status');output.setAttribute('aria-live','polite');
  output.style.cssText='max-height:220px;overflow:auto;white-space:pre-wrap;overflow-wrap:anywhere;background:#0b161b;padding:10px;border:1px solid #54706e;border-radius:6px;font:12px ui-monospace,monospace';
  bar.append(input,execute,help);section.append(heading,tip,bar,output);dlg.append(section);
  const history=[];let cursor=0;
  const run=()=>{const line=input.value.trim();if(!line)return;history.push(line);if(history.length>40)history.shift();cursor=history.length;
    try{output.textContent=JSON.stringify(runtime.run(line),null,2);}catch(e){output.textContent='ERRO: '+e.message;}
    output.scrollTop=0;
  };
  execute.onclick=run;help.onclick=()=>{input.value='help';run();};
  input.addEventListener('keydown',e=>{if(e.key==='Enter'){e.preventDefault();run();}
    else if(e.key==='ArrowUp'&&history.length){e.preventDefault();cursor=Math.max(0,cursor-1);input.value=history[cursor];}
    else if(e.key==='ArrowDown'&&history.length){e.preventDefault();cursor=Math.min(history.length,cursor+1);input.value=history[cursor]||'';}});
  output.textContent='Digite help para listar comandos. Exemplos: runtime query studio.scenes · runtime query studio.plan';
  return runtime;
}
