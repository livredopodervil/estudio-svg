// RD Studio — editor de roteiro de alto nível no mesmo workspace.
// Usa exclusivamente compile/Timeline/renderSVG existentes (GIL); nunca executa código do usuário.
import {compileRoteiro} from './roteiro-v02.mjs';
import {STYLES,styleById,createStyleBase,createStyleScript} from './roteiro-styles.mjs';
import {compile} from './gil-runtime/src/model.mjs';
import {serialize} from './gil-runtime/src/language.mjs';
import {prepare} from './gil-native.mjs';
import {parseFrame,motionProgram} from './scene-objects.mjs';
import {splitRoteiro03,parseAgentPlan,previewScenePlan} from './roteiro-plan-v03.mjs';
const $=s=>document.querySelector(s);
const fileDownload=(name,source)=>{const url=URL.createObjectURL(new Blob([source],{type:'text/plain;charset=utf-8'})),link=document.createElement('a');link.href=url;link.download=name;link.click();setTimeout(()=>URL.revokeObjectURL(url),2500);};
export function installRoteiroEditor({scene,selected,openSource,stop,seek:seekScene,local,notify,changed,refresh}){
 if($('#rdRoteiroButton'))return;
 const head=$('.workspaceTools')||$('.topactions');if(!head)return;
 const button=document.createElement('button');button.id='rdRoteiroButton';button.type='button';button.textContent='▤ Roteiro';button.title='Editor Roteiro 0.3: GIL, clipes, transições, áudio e planos de agentes';head.append(button);
 const dialog=document.createElement('dialog');dialog.className='rdRoteiroDialog';dialog.setAttribute('aria-label','Editor de roteiro GIL 0.3');
 dialog.innerHTML=`<div class="rdRoteiroHeader"><strong>Roteiro 0.3 · composição e automação</strong><button type="button" data-quit>× Fechar</button></div>
 <p class="rdRoteiroNote">Animação GIL e operações tipadas sobre a cena. Use clipes já importados/convertidos em camadas. Simule antes de aplicar; sem outro player ou execução arbitrária.</p>
 <div class="rdRoteiroInputs"><label>Estilo visual<select data-style></select></label><label>Duração (s)<input data-duration type="number" min="3" max="60" step=".5" value="8"></label>
 <label class="rdWide">Título<input data-title maxlength="100" value="UMA IDEIA GANHA MOVIMENTO"></label>
 <label class="rdWide">Subtítulo<input data-sub maxlength="90" value="ROTEIRO · GIL · RD STUDIO"></label></div>
 <div class="rdRoteiroGallery" data-gallery aria-label="Biblioteca de estilos"></div>
 <div class="rdRoteiroActions"><button type="button" data-template>Gerar base + roteiro do estilo</button><button type="button" data-current>Usar GIL selecionada como base</button><button type="button" data-scriptfile>Importar .roteiro</button><button type="button" data-download>↓ Salvar .roteiro</button></div>
 <div class="rdRoteiroEditors"><label>Fonte base GIL<textarea data-base spellcheck="false" aria-label="Fonte base GIL"></textarea></label>
 <label>Roteiro 0.3 (compatível com 0.1 e 0.2)<textarea data-script spellcheck="false" aria-label="Roteiro 0.3"></textarea></label></div>
 <div class="rdRoteiroActions"><button type="button" class="primary" data-compile>Compilar e visualizar</button><label>Tempo<input data-seek type="range" min="0" max="8" step=".05" value="0"></label><output data-clock>0.00 s</output></div>
 <div class="rdRoteiroFrame" data-frame role="img" aria-label="Prévia GIL compilada"></div><p role="status" data-status class="rdRoteiroNote"></p>
 <div class="rdRoteiroActions"><button type="button" data-compiledownload disabled>↓ Baixar GIL</button><button type="button" class="primary" data-insert disabled>Inserir GIL na cena atual</button></div><details class="rdRoteiroAgent" open><summary><strong>Plano de edição · clipes, transições e áudio</strong></summary>
 <p class="rdRoteiroNote">As diretivas 0.3 no roteiro e o plano JSON abaixo são alternativas: um JSON preenchido tem prioridade. As operações agem na cena atual e exigem IDs existentes. O áudio continua no mixer compartilhado.</p>
 <label>Plano JSON para um agente (opcional)<textarea data-agent-plan spellcheck="false" rows="7" placeholder='{"format":"rd-studio-plan-0.3","operations":[]}'></textarea></label>
 <div class="rdRoteiroActions"><button type="button" data-agent-example>Exemplo seguro</button><button type="button" data-agent-analyze>Simular alterações</button><button type="button" data-agent-download>↓ Exportar JSON</button><button type="button" data-agent-import>Importar JSON</button></div>
 <pre data-agent-report class="rdRoteiroNote" aria-live="polite"></pre>
 <div class="rdRoteiroActions"><button type="button" class="primary" data-agent-apply disabled>Aplicar alterações à cena (confirmar)</button></div>
 </details><input hidden data-file type="file" accept=".roteiro,.txt,text/plain"><input hidden data-agent-file type="file" accept=".json,application/json">`;
 document.body.append(dialog);
 const get=sel=>dialog.querySelector('[data-'+sel+']'),style=get('style'),duration=get('duration'),title=get('title'),sub=get('sub'),base=get('base'),script=get('script'),gallery=get('gallery'),frame=get('frame'),seekSlider=get('seek'),clock=get('clock'),status=get('status');
 style.replaceChildren(...STYLES.map(p=>new Option(p.name,p.id)));
 for(const p of STYLES){const tile=document.createElement('button');tile.type='button';tile.className='rdRoteiroTile';tile.dataset.style=p.id;tile.title=p.note;
  const thumb=document.createElement('div');thumb.className='rdRoteiroThumb';thumb.style.backgroundColor=p.bg;thumb.style.color=p.fg;
  const accent=document.createElement('i');accent.style.backgroundColor=p.accent;const word=document.createElement('b');word.textContent=p.name;thumb.append(accent,word);
  const label=document.createElement('span');label.textContent=p.note;tile.append(thumb,label);tile.onclick=()=>{style.value=p.id;drawTiles();status.textContent=p.note;};gallery.append(tile);
 }
 const drawTiles=()=>{for(const tile of gallery.children)tile.classList.toggle('selected',tile.dataset.style===style.value);};
 const invalid=()=>{result=null;get('insert').disabled=true;get('compiledownload').disabled=true;frame.replaceChildren();};
 let result=null,compiled=null;
 for(const el of [base,script])el.addEventListener('input',()=>{invalid();status.textContent='Fonte alterada: compile novamente antes de inserir.';});
 function template(){
  if((base.value.trim()||script.value.trim())&&!confirm('Substituir apenas o texto deste editor? O projeto atual não será alterado.'))return;
  const d=Number(duration.value);try{base.value=createStyleBase({style:style.value,text:title.value,subtitle:sub.value,duration:d});script.value=createStyleScript({style:style.value,duration:d}).replace(/^roteiro 0\.2/, 'roteiro 0.3');invalid();status.textContent='Modelo carregado. Clique Compilar e visualizar.';}catch(e){status.textContent=e.message;}
 }
 function inspect(){try{
  invalid();if(new TextEncoder().encode(base.value).length>250000)throw Error('Base GIL maior que 250 kB.');
  const split=script.value.trim().startsWith('roteiro 0.3')?splitRoteiro03(script.value):{gilScript:script.value};
  const compiledR=compileRoteiro(base.value,split.gilScript,{compile,serialize}),p=prepare(compiledR.source);
  if(p.cues)throw Error('Cues GIL não são suportados na camada de composição. Use as trilhas de áudio do Estúdio.');
  compiled=p;result={source:compiledR.source,base:base.value,script:script.value,events:compiledR.events};
  seekSlider.max=String(p.duration);seekSlider.value='0';get('insert').disabled=false;get('compiledownload').disabled=false;
  render();status.textContent=`GIL validada: ${compiledR.doc.nodes.length} objetos, ${compiledR.doc.tracks.length} faixas, ${compiledR.events.length} ações. Original preservado.`;
 }catch(e){compiled=null;status.textContent='Erro: '+e.message;}}
 function render(){if(!compiled)return;try{const t=Math.min(compiled.duration,Math.max(0,Number(seekSlider.value)||0));const el=parseFrame(compiled.frame(t),true);el.style.cssText='width:100%;height:100%;display:block';frame.replaceChildren(el);clock.textContent=t.toFixed(2)+' s';}catch(e){status.textContent=e.message;}}
 const checked=()=>{if(!result||result.base!==base.value||result.script!==script.value)throw Error('Recompile o roteiro alterado.');return result.source;};
 button.onclick=()=>{if(!scene())return notify('Abra uma cena antes de editar um roteiro.',true);stop?.();drawTiles();dialog.showModal();if(!base.value.trim()&&!script.value.trim()){base.value=createStyleBase({style:style.value,text:title.value,subtitle:sub.value,duration:Number(duration.value)});script.value=createStyleScript({style:style.value,duration:Number(duration.value)}).replace(/^roteiro 0\.2/, 'roteiro 0.3');status.textContent='Modelo inicial carregado. Compile antes de inserir.';}};
 get('quit').onclick=()=>dialog.close();get('template').onclick=template;get('compile').onclick=inspect;seekSlider.oninput=render;style.onchange=drawTiles;
 get('current').onclick=()=>{const o=selected();const src=o?.kind==='gil'&&o.gil?.source;if(!src)return status.textContent='Selecione primeiro uma camada GIL na timeline.';
  if(base.value.trim()&&base.value!==src&&!confirm('Trocar apenas a fonte base do painel?'))return;base.value=src;invalid();status.textContent='Base importada da camada selecionada. Atenção a IDs e faixas já existentes.';};
 get('download').onclick=()=>fileDownload('rd-studio.roteiro',script.value);
 get('compiledownload').onclick=()=>{try{fileDownload('rd-studio-compilado.gil',checked());}catch(e){status.textContent=e.message;}};
 get('scriptfile').onclick=()=>get('file').click();get('file').onchange=async()=>{const file=get('file').files[0];if(!file)return;if(file.size>100000)return status.textContent='Arquivo de roteiro acima do limite.';
  if(script.value.trim()&&!confirm('Substituir o roteiro digitado?'))return;script.value=await file.text();invalid();status.textContent='Roteiro importado; compile para validar.';get('file').value='';};
 get('insert').onclick=()=>{try{const source=checked();if(!scene())throw Error('A cena atual não existe.');if(Number(scene().duracao)<compiled.duration)throw Error('GIL maior que a duração desta cena. Ajuste a duração ou gere roteiro menor.');if(Number(scene().duracao)-(local?.()||0)<compiled.duration){if(!confirm('O cursor está no meio da cena. Voltar ao início para inserir o roteiro completo?'))return;seekScene?.(0);}dialog.close();openSource(source,'Roteiro '+styleById(style.value).name);}catch(e){status.textContent=e.message;}};
 const agentText=get('agent-plan'),agentReport=get('agent-report'),agentApply=get('agent-apply');
 let proposal=null;
 const revokePlan=()=>{proposal=null;agentApply.disabled=true;agentReport.textContent='Plano alterado: simule novamente.';};
 script.addEventListener('input',revokePlan);agentText.addEventListener('input',revokePlan);
 function extractPlan(){
  if(agentText.value.trim())return parseAgentPlan(agentText.value);
  if(script.value.trim().startsWith('roteiro 0.3'))return splitRoteiro03(script.value).plan;
  return {format:'rd-studio-plan-0.3',operations:[]};
 }
 get('agent-example').onclick=()=>{
  const video=(scene()?.objetos_midia||[]).find(o=>o.kind==='video');
  const ops=[{type:'audio.scene',fade_in:.3,fade_out:.4}];
  if(video)ops.push({type:'clip.audio',id:video.id,volume:.8,fade_in:.3,fade_out:.4});
  agentText.value=JSON.stringify({format:'rd-studio-plan-0.3',operations:ops},null,2);
  revokePlan();agentReport.textContent=video?'Plano exemplo: áudio da cena e do clipe selecionável.':'Plano exemplo: áudio da cena. Converta um vídeo em camada para operações sobre clipes.';
 };
 get('agent-analyze').onclick=()=>{try{
  if(!scene())throw Error('Nenhuma cena aberta.');
  const raw=extractPlan();const res=previewScenePlan(scene(),raw,{validateMotion:motionProgram});
  proposal={reference:scene(),snapshot:JSON.stringify(scene()),plan:JSON.stringify(raw),res};
  agentApply.disabled=!res.changes.length;
  agentReport.textContent=res.changes.length?res.changes.map(c=>`Operação ${c.index+1}: ${c.type}${c.id?' · '+c.id:''}`).join('\n')+'\nNenhuma alteração aplicada.':'Nenhuma operação: projeto inalterado.';
 }catch(e){proposal=null;agentApply.disabled=true;agentReport.textContent='Recusado: '+e.message;}};
 agentApply.onclick=()=>{try{
  if(!proposal||scene()!==proposal.reference||JSON.stringify(scene())!==proposal.snapshot||JSON.stringify(extractPlan())!==proposal.plan)throw Error('Cena ou plano mudou: simule novamente.');
  const {res}=proposal;if(!confirm('Aplicar '+res.changes.length+' operações na cena atual? O histórico do Estúdio permite desfazer.'))return;
  Object.assign(scene(),res.scene);revokePlan();changed();refresh?.();notify('Plano aplicado na cena. Revise prévia e áudio antes de salvar.');
 }catch(e){agentReport.textContent='Não aplicado: '+e.message;agentApply.disabled=true;}};
 get('agent-download').onclick=()=>{try{fileDownload('rd-studio-plano-0.3.json',JSON.stringify(extractPlan(),null,2));}catch(e){agentReport.textContent=e.message;}};
 get('agent-import').onclick=()=>get('agent-file').click();
 get('agent-file').onchange=async()=>{const file=get('agent-file').files[0];if(!file)return;
  try{if(file.size>100000)throw Error('Plano acima de 100 kB');const source=await file.text();parseAgentPlan(source);
   if(agentText.value.trim()&&!confirm('Substituir o plano JSON do painel?'))return;
   agentText.value=JSON.stringify(parseAgentPlan(source),null,2);revokePlan();agentReport.textContent='Plano importado. Simule antes de aplicar.';
  }catch(e){agentReport.textContent='Arquivo recusado: '+e.message;}finally{get('agent-file').value='';}
 };
 return {open:()=>button.click()};
}
