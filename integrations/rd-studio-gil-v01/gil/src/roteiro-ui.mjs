import {compileRoteiro} from './roteiro.mjs';
import {compile} from './model.mjs';
import {serialize} from './language.mjs';
const $=id=>document.getElementById(id),base=$('roteiro-base'),script=$('roteiro-script'),status=$('roteiro-status'),out=$('roteiro-output');
let result=null;
function invalidate(){result=null;out.value='';$('roteiro-stage').disabled=true;$('roteiro-save').disabled=true;}
function reset(message){invalidate();status.textContent=message;}
for(const t of [base,script])t.addEventListener('input',()=>reset('Fonte ou roteiro alterado. Compile novamente.'));
async function loadDemo(path){const before=[base.value,script.value];if(before.some(s=>s.trim())&&!confirm('Substituir apenas a base e o roteiro deste painel? A composição ativa será preservada.'))return;try{
 const r=await fetch(path);if(!r.ok)throw Error('Exemplo indisponível');const v=await r.json();if(base.value!==before[0]||script.value!==before[1])throw Error('Texto editado durante o carregamento; preservado');base.value=v.base;script.value=v.script;reset('Exemplo carregado. Clique Compilar roteiro.');
}catch(e){status.textContent=e.message;}}
$('roteiro-demo').onclick=()=>loadDemo('examples/roteiro-demo.json');$('roteiro-datacenter').onclick=()=>loadDemo('examples/roteiro-datacenter.json');
$('roteiro-base-current').onclick=()=>{try{const snapshot=window.GILAuthoring?.snapshot();if(!snapshot||snapshot.dirty)throw Error('Valide a fonte atual primeiro.');if(base.value.trim()&&base.value!==snapshot.source&&!confirm('Substituir a fonte base deste painel?'))return;base.value=snapshot.source;reset('Base copiada da composição validada.');}catch(e){status.textContent=e.message;}};
$('roteiro-compile').onclick=()=>{invalidate();try{
 if(new TextEncoder().encode(base.value).length>250000)throw Error('Fonte base acima de 250 kB');
 const r=compileRoteiro(base.value,script.value,{compile,serialize});result={source:r.source,base:base.value,script:script.value};out.value=r.source;$('roteiro-stage').disabled=false;$('roteiro-save').disabled=false;
 status.textContent=`${r.doc.nodes.length} objetos · ${r.doc.tracks.length} faixas · ${r.doc.cues.length} efeitos · ${r.events.length} ações. Composição ativa preservada.`;
}catch(e){status.textContent='Erro: '+e.message;}};
function checked(){if(!result||result.base!==base.value||result.script!==script.value)throw Error('Compile novamente.');return result.source;}
$('roteiro-stage').onclick=()=>{try{const compiled=checked(),snap=window.GILAuthoring?.snapshot();if(!snap)throw Error('Aguarde a inicialização do editor.');if(snap.dirty&&!confirm('Substituir o código não aplicado no editor GIL?'))return;const target=$('source');target.value=compiled;target.dispatchEvent(new Event('input'));status.textContent='Saída enviada. Clique Validar e aplicar no Programa GIL. A base e o roteiro continuam neste painel.';target.scrollIntoView({block:'center'});target.focus();}catch(e){status.textContent=e.message;}};
$('roteiro-save').onclick=()=>{try{const url=URL.createObjectURL(new Blob([checked()],{type:'text/plain'})),a=document.createElement('a');a.href=url;a.download='roteiro-compilado.gil';a.click();setTimeout(()=>URL.revokeObjectURL(url),3000);}catch(e){status.textContent=e.message;}};
