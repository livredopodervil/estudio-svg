#!/usr/bin/env python3
"""Patch incremental do Player Vetorial V1 no stage Termux.

Corrige: a) corte de locução na troca de cena, b) pivô de ponteiros SVG.
Somente stage/vetorial/{player.js,index.html}; nenhum arquivo do repo ou do projeto.
Uso: python ... --stage "$HOME/estudio_player_stage" [--apply|--restore]
"""
from __future__ import annotations
import argparse
import difflib
import os
import re
import sys
from pathlib import Path

MARKER = '/* ESTUDIO_SVG_VETORIAL_AUDIO_PIVO_V2 */'

PATCH_JS = [
('''let current=0, playing=false, origin=0, raf=0, voiceEl=null, voiceScene=-1, warning='';
const slug=document.documentElement.dataset.slug;''',
'''let current=0, playing=false, origin=0, raf=0, voiceEl=null, voiceScene=-1, warning='';
let voiceBusy=false, voiceEpoch=0, waitingVoice=false, calibration=false;
const slug=document.documentElement.dataset.slug;
const pivotStoreKey='estudio-svg-vetorial-pivos:'+slug;
let pivotOverrides={};
try { pivotOverrides=JSON.parse(localStorage.getItem(pivotStoreKey)||'{}')||{}; } catch (_) { pivotOverrides={}; }
'''+MARKER),
('''function stopVoice(){if(voiceEl){voiceEl.pause();voiceEl.src='';voiceEl=null;}if('speechSynthesis' in window) speechSynthesis.cancel();voiceScene=-1;}
function nativeVoice(scene){
  if(!$('narrate').checked || voiceScene===scene)return;
  stopVoice(); voiceScene=scene;
  const c=project.cenas[scene], path=source(c), rate=Number($('rate').value);
  const known=window.__voiceFiles||{};
  if(path && known[path]){
    voiceEl=new Audio(known[path]);voiceEl.playbackRate=rate;voiceEl.play().catch(e=>out('Narração bloqueada: '+e.message));return;
  }
  const txt=voiceText(c);
  if(txt && 'speechSynthesis' in window){
    const u=new SpeechSynthesisUtterance(txt);
    u.lang=$('lang').value;u.rate=rate;
    const voices=speechSynthesis.getVoices(), lang=u.lang.toLowerCase();
    u.voice=voices.find(v=>v.lang.toLowerCase()===lang) || voices.find(v=>v.lang.toLowerCase().startsWith(lang.split('-')[0])) || null;
    speechSynthesis.speak(u);
  }
}''',
'''function stopVoice(){
  ++voiceEpoch; voiceBusy=false; waitingVoice=false;
  if(voiceEl){voiceEl.pause();voiceEl.onended=null;voiceEl.onerror=null;voiceEl.removeAttribute('src');voiceEl.load();voiceEl=null;}
  if('speechSynthesis' in window) speechSynthesis.cancel();
  voiceScene=-1;
}
function nativeVoice(scene){
  if(!$('narrate').checked || voiceScene===scene)return;
  stopVoice(); voiceScene=scene;
  const c=project.cenas[scene];
  if(c.audio?.muted || c.audio?.voice_enabled===false)return;
  const path=source(c),rate=Number($('rate').value),known=window.__voiceFiles||{};
  const epoch=voiceEpoch;
  const done=()=>{if(epoch===voiceEpoch)voiceBusy=false;};
  if(path && known[path]){
    voiceEl=new Audio(known[path]); voiceEl.playbackRate=rate;
    voiceEl.onended=done;
    voiceEl.onerror=()=>{out('Arquivo de voz indisponível na cena '+(scene+1));done();};
    voiceBusy=true;
    voiceEl.play().catch(e=>{out('Narração bloqueada: '+e.message);done();});
    return;
  }
  const txt=voiceText(c);
  if(txt && 'speechSynthesis' in window){
    const u=new SpeechSynthesisUtterance(txt);
    u.lang=$('lang').value;u.rate=rate;
    const voices=speechSynthesis.getVoices(),lang=u.lang.toLowerCase();
    u.voice=voices.find(v=>v.lang.toLowerCase()===lang) ||
      voices.find(v=>v.lang.toLowerCase().startsWith(lang.split('-')[0])) || null;
    u.onend=done;
    u.onerror=e=>{if(e.error!=='interrupted' && e.error!=='canceled')out('Erro de síntese: '+e.error);done();};
    voiceBusy=true;
    try{speechSynthesis.speak(u);}catch(e){out('Falha na narração: '+e.message);done();}
  }
}'''),
('''async function loadScene(i){
  if(i===index)return;
  stopVoice();index=i;bases.clear();svg=null;''',
'''async function loadScene(i,token){
  if(i===index)return;
  stopVoice();index=i;bases.clear();svg=null;'''),
('''  const markup=await res.text();
  const parsed=new DOMParser()''',
'''  const markup=await res.text();
  if(token!==loadToken)return; // Ignora resposta de fetch anterior a uma busca na timeline.
  const parsed=new DOMParser()'''),
('''  for(const el of svg.querySelectorAll('[id]'))bases.set(el.id,{el,transform:el.getAttribute('transform')||'',opacity:el.getAttribute('opacity')||'1'});
  if(playing)nativeVoice(i);''',
'''  for(const el of svg.querySelectorAll('[id]'))bases.set(el.id,{el,transform:el.getAttribute('transform')||'',opacity:el.getAttribute('opacity')||'1'});
  const targets=[...new Set((project.cenas[i].animacoes||[]).filter(a=>a.tipo==='rotacao').map(a=>String(a.alvo)).filter(t=>bases.has(t)))];
  const picker=$('pivotTarget');
  picker.replaceChildren(...targets.map(t=>new Option(t,t)));
  picker.hidden=!targets.length;
  picker.value=targets.find(t=>/ponteiro|agulha|hand|segund|minut|hora/i.test(t))||targets[0]||'';
  calibration=false;$('calibrate').textContent='⊙ Ajustar eixo';
  if(playing)nativeVoice(i);'''),
('''function pivot(el){try{const b=el.getBBox();return [b.x+b.width/2,b.y+b.height/2];}catch(_){return [640,360];}}''',
'''function pivot(el,a){
  const key=index+':'+el.id,custom=pivotOverrides[key];
  if(Array.isArray(custom)&&custom.length===2&&custom.every(Number.isFinite))return custom;
  const explicit=[a?.pivo_x,a?.pivo_y];
  if(explicit.every(v=>v!==undefined&&v!==null&&Number.isFinite(Number(v))))return explicit.map(Number);
  const data=[el.getAttribute('data-pivot-x'),el.getAttribute('data-pivot-y')];
  if(data.every(v=>v!==null&&v!==''&&Number.isFinite(Number(v))))return data.map(Number);
  const line=el.localName==='line'?el:el.querySelector?.('line');
  if(line){const x=Number(line.getAttribute('x1')),y=Number(line.getAttribute('y1'));
    if(Number.isFinite(x)&&Number.isFinite(y))return [x,y];}
  try{
    const b=el.getBBox();
    // Para ponteiros desenhados como paths, procure o centro do mostrador.
    if(/ponteiro|agulha|hand|segund|minut|hora/i.test(el.id)&&svg){
      let best=null,score=Infinity;
      const length=Math.max(b.width,b.height,1);
      for(const c of svg.querySelectorAll('circle,ellipse')){
        if(el.contains(c))continue;
        const cx=Number(c.getAttribute('cx')),cy=Number(c.getAttribute('cy'));
        const r=Number(c.getAttribute('r')||c.getAttribute('rx'));
        if(!Number.isFinite(cx+cy+r)||r<length*.4||r>length*8)continue;
        const dx=Math.max(b.x-cx,0,cx-b.x-b.width);
        const dy=Math.max(b.y-cy,0,cy-b.y-b.height);
        const d=Math.hypot(dx,dy);
        if(d>length*.45)continue;
        const s=d+Math.abs(r-length)*.04;
        if(s<score){score=s;best=[cx,cy];}
      }
      if(best)return best;
    }
    return [b.x+b.width/2,b.y+b.height/2];
  }catch(_){return [640,360];}
}'''),
('''const [x,y]=pivot(dest.el);tr.list.push(`rotate''',
'''const [x,y]=pivot(dest.el,a);tr.list.push(`rotate'''),
('''const [x,y]=pivot(dest.el),s=interp''',
'''const [x,y]=pivot(dest.el,a),s=interp'''),
('''if(i!==index){const token=++loadToken;await loadScene(i);if(token!==loadToken)return;}''',
'''if(i!==index){const token=++loadToken;await loadScene(i,token);if(token!==loadToken)return;}'''),
('''function loop(now){
  if(!playing)return;
  if(voiceEl && voiceEl.error){out('Erro na narração.');stopVoice();}
  const t=(now-origin)/1000;
  if(t>=total){pause();show(total).catch(e=>out(e.message));return;}
  show(t).catch(e=>{pause();out('Erro: '+e.message);});
  raf=requestAnimationFrame(loop);
}
function pause(){playing=false;cancelAnimationFrame(raf);stopVoice();$('play').textContent='▶ Reproduzir';}''',
'''function loop(now){
  if(!playing)return;
  if(voiceEl && voiceEl.error){out('Erro na narração.');stopVoice();}
  let t=(now-origin)/1000;
  // Nunca troca de cena antes de concluir a voz da cena corrente.
  if(index>=0&&voiceBusy&&index<durations.length){
    const end=starts[index]+durations[index];
    if(t>=end){
      t=end-0.0005;
      origin=now-t*1000; // pausa apenas o relógio das imagens
      if(!waitingVoice){waitingVoice=true;out('Aguardando conclusão da narração da cena '+(index+1));}
    }
  }else if(waitingVoice){waitingVoice=false;out('Reprodução sincronizada.');}
  if(t>=total){pause();show(total).catch(e=>out(e.message));return;}
  show(t).catch(e=>{pause();out('Erro: '+e.message);});
  raf=requestAnimationFrame(loop);
}
function pause(){
  playing=false;cancelAnimationFrame(raf);
  if(voiceEl)voiceEl.pause();
  if('speechSynthesis' in window)speechSynthesis.pause();
  $('play').textContent='▶ Reproduzir';
}'''),
('''  if(current>=total)current=0;
  playing=true;origin=performance.now()-current*1000;$('play').textContent='Ⅱ Pausar';
  if(index>=0)nativeVoice(index);
  raf=requestAnimationFrame(loop);''',
'''  if(current>=total){current=0;stopVoice();}
  playing=true;origin=performance.now()-current*1000;$('play').textContent='Ⅱ Pausar';
  if(index>=0&&index===pick(current)){
    if(voiceBusy&&voiceScene===index){
      if(voiceEl)voiceEl.play().catch(e=>out('Áudio não retomado: '+e.message));
      if('speechSynthesis' in window)speechSynthesis.resume();
    }else nativeVoice(index);
  }
  raf=requestAnimationFrame(loop);'''),
('''  if(playing){origin=performance.now()-t*1000;stopVoice();}else stopVoice();
  show(t).then(()=>{if(playing)nativeVoice(index)}).catch(e=>out(e.message));''',
'''  if(playing)origin=performance.now()-t*1000;
  stopVoice();
  show(t).then(()=>{if(playing)nativeVoice(index)}).catch(e=>out(e.message));'''),
('''$('rate').oninput=()=>{$('rateOut').textContent=Number($('rate').value).toFixed(2)+'×';
  if(voiceEl)voiceEl.playbackRate=Number($('rate').value);
};''',
'''$('rate').oninput=()=>{$('rateOut').textContent=Number($('rate').value).toFixed(2)+'×';
  if(voiceEl)voiceEl.playbackRate=Number($('rate').value);
  // Web Speech API não permite alterar a velocidade durante uma fala em curso.
};
$('narrate').onchange=()=>{if(!$('narrate').checked)stopVoice();else if(playing&&index>=0)nativeVoice(index);};
$('calibrate').onclick=()=>{
  if(!$('pivotTarget').value){out('Cena sem alvos de rotação configurados.');return;}
  calibration=!calibration;
  $('calibrate').textContent=calibration?'Cancelar ajuste':'⊙ Ajustar eixo';
  if(calibration)out('Toque no centro do mostrador para ajustar o eixo de '+$('pivotTarget').value+'.');
};
$('stage').addEventListener('click',e=>{
  if(!calibration||!svg||!svg.contains(e.target))return;
  const target=$('pivotTarget').value,el=bases.get(target)?.el;
  if(!el)return;
  try{
    const parent=el.parentNode?.getScreenCTM?el.parentNode:svg;
    const matrix=parent.getScreenCTM().inverse(),p=svg.createSVGPoint();
    p.x=e.clientX;p.y=e.clientY;
    const at=p.matrixTransform(matrix);
    pivotOverrides[index+':'+target]=[at.x,at.y];
    try{localStorage.setItem(pivotStoreKey,JSON.stringify(pivotOverrides));}
    catch(_){out('Eixo ajustado nesta sessão; armazenamento local bloqueado.');}
    calibration=false;$('calibrate').textContent='⊙ Ajustar eixo';
    apply(current);
    out('Eixo de '+target+' definido em ('+at.x.toFixed(1)+', '+at.y.toFixed(1)+').');
  }catch(err){out('Não foi possível definir o eixo: '+err.message);}
});'''),
('''window.addEventListener('pagehide',pause);''',
'''window.addEventListener('pagehide',()=>{pause();stopVoice();});'''),
]

PATCH_HTML = [
('''<button id="full">⛶ Tela cheia</button>''',
'''<button id="full">⛶ Tela cheia</button><select id="pivotTarget" aria-label="Objeto cujo eixo será ajustado" hidden></select><button id="calibrate" type="button">⊙ Ajustar eixo</button>'''),
('''<script src="./player.js"></script>''',
'''<script src="./player.js?v=2"></script>'''),
('''min="0.8" max="1.6" value="1.15" step="0.05"><output id="rateOut">1.15×''',
'''min="0.8" max="2.0" value="1.40" step="0.05"><output id="rateOut">1.40×'''),
]


def apply_exact(content: str, patches: list[tuple[str,str]], name: str) -> str:
    for i,(old,new) in enumerate(patches,1):
        count=content.count(old)
        if count!=1:
            raise RuntimeError(f'{name}: esperado um trecho #{i}, encontrados {count}; arquivo desconhecido, preservado')
        content=content.replace(old,new,1)
    return content


def make_backup(path: Path, suffix: str, original: str):
    dest=path.with_name(path.name+suffix)
    if dest.exists():
        if dest.read_text('utf-8')!=original:
            raise RuntimeError(f'Backup existente difere da versão atual: {dest}; não sobrescrever')
    else:dest.write_text(original,'utf-8')


def save_atomic(path: Path, data: str):
    tmp=path.with_name('.'+path.name+'.v2tmp')
    if tmp.exists(): raise RuntimeError('Arquivo temporário preexistente: '+str(tmp))
    tmp.write_text(data,'utf-8')
    os.replace(tmp,path)


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--stage',default='~/estudio_player_stage')
    x=ap.add_mutually_exclusive_group()
    x.add_argument('--apply',action='store_true')
    x.add_argument('--restore',action='store_true')
    args=ap.parse_args()
    stage=Path(args.stage).expanduser().resolve()
    if stage==Path.home() or stage==Path('/'):
        raise RuntimeError('Stage inválido')
    js=stage/'vetorial'/'player.js';page=stage/'vetorial'/'index.html'
    for path in (js,page):
        if not path.is_file(): raise FileNotFoundError(path)
        if not path.resolve().is_relative_to(stage):raise RuntimeError('Destino fora do stage: '+str(path))
    backup_tag='.antes_audio_pivo_v2.bak'
    if args.restore:
        for path in (js,page):
            bak=path.with_name(path.name+backup_tag)
            if not bak.is_file():raise FileNotFoundError(bak)
        if MARKER not in js.read_text('utf-8'):raise RuntimeError('JS não corresponde à versão V2; abortado')
        for path in (js,page):
            bak=path.with_name(path.name+backup_tag)
            save_atomic(path,bak.read_text('utf-8'))
            print('RESTAURADO:',path)
        return
    old_js=js.read_text('utf-8');old_page=page.read_text('utf-8')
    if MARKER in old_js:
        print('V2 já aplicada; sem alterações.');return
    if 'const slug=document.documentElement.dataset.slug;' not in old_js or 'player vetorial experimental' not in old_page.lower():
        raise RuntimeError('Player desconhecido; preservado')
    new_js=apply_exact(old_js,PATCH_JS,'player.js')
    new_page=apply_exact(old_page,PATCH_HTML,'index.html')
    if not args.apply:
        print('SIMULAÇÃO: player.js e index.html reconhecidos; patch aplicável, nenhum arquivo modificado.')
        print('Mudanças: aguardar fim da voz; pausar sem reiniciar; eixo calibrável por toque; velocidade 1,40×.')
        print('Use --apply para gravar em',stage)
        return
    # O patch é restrito ao stage. Backup verificado antes de gravar qualquer modificação.
    for path,original in ((js,old_js),(page,old_page)):
        bak=path.with_name(path.name+backup_tag)
        if bak.exists() and bak.read_text('utf-8')!=original:
            raise RuntimeError(f'Backup já existe e diverge: {bak}; nada gravado')
    make_backup(js,backup_tag,old_js)
    make_backup(page,backup_tag,old_page)
    save_atomic(js,new_js);save_atomic(page,new_page)
    print('PATCH V2 APLICADO:',js,page,sep='\n  ')
    print('Reversão: python',Path(__file__).name,'--stage',stage,'--restore')
    print('URL: http://127.0.0.1:8877/vetorial/')

if __name__=='__main__':
    try:main()
    except Exception as exc:print('ERRO:',exc,file=sys.stderr);raise SystemExit(2)
