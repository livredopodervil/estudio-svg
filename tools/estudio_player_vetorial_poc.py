#!/usr/bin/env python3
"""Estúdio SVG V3 — player vetorial experimental no stage (sem Git, sem push)."""
from __future__ import annotations
import argparse, base64, copy, html, importlib, inspect, json, mimetypes, re, shutil, subprocess, sys
from pathlib import Path
from urllib.parse import unquote, urlsplit

MARK='<!-- ESTUDIO_SVG_PLAYER_VETORIAL_POC_V1 -->'
JS=r'''(() => {
'use strict';
const $=id=>document.getElementById(id), clamp=(x,a=0,b=1)=>Math.max(a,Math.min(b,x));
let project=null, durations=[], starts=[], total=0, index=-1, svg=null, bases=new Map();
let current=0, playing=false, origin=0, raf=0, voiceEl=null, voiceScene=-1, warning='';
const slug=document.documentElement.dataset.slug;
const out=s=>{$('status').textContent=s};
const sec=t=>`${Math.floor(t/60).toString().padStart(2,'0')}:${Math.floor(t%60).toString().padStart(2,'0')}`;
function pick(t){let i=0; while(i<durations.length-1 && t>=starts[i]+durations[i])i++;return i;}
function source(c){const x=c.audio||{};return (x.voice_file||'').trim();}
function voiceText(c){return String(c.audio?.voice_text || c.fala || '').trim();}
function stopVoice(){if(voiceEl){voiceEl.pause();voiceEl.src='';voiceEl=null;}if('speechSynthesis' in window) speechSynthesis.cancel();voiceScene=-1;}
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
}
function sanitize(root){
  root.querySelectorAll('script,foreignObject,iframe,object,embed').forEach(n=>n.remove());
  root.querySelectorAll('*').forEach(el=>{
    for(const a of [...el.attributes]){
      if(/^on/i.test(a.name))el.removeAttribute(a.name);
      if(/^(href|xlink:href)$/i.test(a.name) && /^\s*javascript:/i.test(a.value))el.removeAttribute(a.name);
    }
  });
  return root;
}
async function loadScene(i){
  if(i===index)return;
  stopVoice();index=i;bases.clear();svg=null;
  const url='./cenas/cena-'+String(i+1).padStart(3,'0')+'.svg';
  const res=await fetch(url,{cache:'no-store'});
  if(!res.ok)throw Error(url+' → HTTP '+res.status);
  const markup=await res.text();
  const parsed=new DOMParser().parseFromString(markup,'image/svg+xml');
  if(parsed.querySelector('parsererror'))throw Error('SVG inválido: cena '+(i+1));
  const root=sanitize(document.importNode(parsed.documentElement,true));
  if(root.localName!=='svg')throw Error('Documento não é SVG: cena '+(i+1));
  $('stage').replaceChildren(root);svg=root;
  svg.setAttribute('preserveAspectRatio','xMidYMid meet');svg.removeAttribute('width');svg.removeAttribute('height');
  $('scene').textContent=(i+1)+' / '+durations.length+' · '+String(project.cenas[i].titulo||'');
  for(const el of svg.querySelectorAll('[id]'))bases.set(el.id,{el,transform:el.getAttribute('transform')||'',opacity:el.getAttribute('opacity')||'1'});
  if(playing)nativeVoice(i);
}
function val(a,k,defaultValue=0){const n=Number(a[k]);return Number.isFinite(n)?n:defaultValue;}
function ease(t,mode){return mode==='linear'?t:t*t*(3-2*t);}
function pivot(el){try{const b=el.getBBox();return [b.x+b.width/2,b.y+b.height/2];}catch(_){return [640,360];}}
function apply(t){
  if(!project || !svg)return;
  const p=clamp((t-starts[index])/durations[index]);
  const tracks=new Map();
  for(const a of project.cenas[index].animacoes||[]){
    const dest=bases.get(String(a.alvo)); if(!dest)continue;
    const begin=val(a,'inicio'),end=val(a,'fim',1),k=ease(clamp((p-begin)/Math.max(0.000001,end-begin)),a.easing);
    const interp=(f,to)=>f+(to-f)*k;
    let tr=tracks.get(dest.el);if(!tr){tr={list:[],opacity:1};tracks.set(dest.el,tr);}
    if(a.tipo==='translacao')tr.list.push(`translate(${interp(val(a,'de_x'),val(a,'ate_x'))} ${interp(val(a,'de_y'),val(a,'ate_y'))})`);
    else if(a.tipo==='rotacao'){
      const [x,y]=pivot(dest.el);tr.list.push(`rotate(${interp(val(a,'de'),val(a,'ate'))} ${x} ${y})`);
    }else if(a.tipo==='escala'){
      const [x,y]=pivot(dest.el),s=interp(val(a,'de',1),val(a,'ate',1));
      tr.list.push(`translate(${x} ${y}) scale(${s}) translate(${-x} ${-y})`);
    }else if(a.tipo==='fade')tr.opacity*=clamp(interp(val(a,'de',1),val(a,'ate',1)));
  }
  for(const [id,b] of bases){
    const tr=tracks.get(b.el);
    if(tr){b.el.setAttribute('transform',[...tr.list,b.transform].filter(Boolean).join(' '));
      b.el.setAttribute('opacity',String(clamp(Number(b.opacity)*tr.opacity)));}
    else {if(b.transform)b.el.setAttribute('transform',b.transform);else b.el.removeAttribute('transform');b.el.setAttribute('opacity',b.opacity);}
  }
  // Animação de entrada via CSS, mantendo o mesmo SVG na memória durante a cena.
  svg.style.opacity=String(clamp(p/.06));
  $('seek').value=String(Math.round(1000*t/Math.max(total,.001)));
  $('clock').textContent=sec(t)+' / '+sec(total);
}
let loadToken=0;
async function show(t){
  if(!project)return;
  current=clamp(t,0,total);const i=pick(Math.min(current,Math.max(0,total-1e-6)));
  if(i!==index){const token=++loadToken;await loadScene(i);if(token!==loadToken)return;}
  apply(current);
}
function loop(now){
  if(!playing)return;
  if(voiceEl && voiceEl.error){out('Erro na narração.');stopVoice();}
  const t=(now-origin)/1000;
  if(t>=total){pause();show(total).catch(e=>out(e.message));return;}
  show(t).catch(e=>{pause();out('Erro: '+e.message);});
  raf=requestAnimationFrame(loop);
}
function pause(){playing=false;cancelAnimationFrame(raf);stopVoice();$('play').textContent='▶ Reproduzir';}
$('play').onclick=()=>{
  if(!project)return;
  if(playing){pause();return;}
  if(current>=total)current=0;
  playing=true;origin=performance.now()-current*1000;$('play').textContent='Ⅱ Pausar';
  if(index>=0)nativeVoice(index);
  raf=requestAnimationFrame(loop);
};
$('seek').oninput=()=>{const t=total*Number($('seek').value)/1000;
  if(playing){origin=performance.now()-t*1000;stopVoice();}else stopVoice();
  show(t).then(()=>{if(playing)nativeVoice(index)}).catch(e=>out(e.message));
};
$('rate').oninput=()=>{$('rateOut').textContent=Number($('rate').value).toFixed(2)+'×';
  if(voiceEl)voiceEl.playbackRate=Number($('rate').value);
};
$('lang').onchange=()=>{document.documentElement.lang=$('lang').value;};
$('full').onclick=()=>{if(document.fullscreenElement)document.exitFullscreen?.();else $('stageShell').requestFullscreen?.();};
window.addEventListener('pagehide',pause);
(async()=>{
  try{
    const r=await fetch('../apresentacoes/'+encodeURIComponent(slug)+'/projeto.json',{cache:'no-store'});
    if(!r.ok)throw Error('projeto.json HTTP '+r.status);
    project=await r.json();if(!Array.isArray(project.cenas)||!project.cenas.length)throw Error('Projeto sem cenas');
    starts=[];let sum=0;durations=project.cenas.map(c=>Math.max(.1,Number(c.duracao)||1));
    for(const d of durations){starts.push(sum);sum+=d;}total=sum;
    const lang=String(project.idioma||project.language||'pt-BR');
    $('lang').value=[...$('lang').options].some(o=>o.value===lang)?lang:'pt-BR';
    document.documentElement.lang=$('lang').value;
    await show(0);
    out('Motor vetorial independente · '+project.cenas.length+' cenas · sem PNGs e sem /api/preview. '+
      'Animações procedurais do gerador Python ainda não foram totalmente migradas.');
  }catch(e){out('Falha: '+e.message);console.error(e);}
})();
})();
'''

CSS='''*{box-sizing:border-box}html{color-scheme:dark;font:15px system-ui,sans-serif}body{margin:0;background:#0b1017;color:#e9f1f6}header{padding:10px 14px;background:#1e2936;display:flex;gap:12px;flex-wrap:wrap;justify-content:space-between}a{color:#b4e2ff}main{max-width:1400px;margin:auto;padding:12px}.toolbar{display:flex;align-items:center;gap:9px;flex-wrap:wrap;margin-bottom:9px}button,select{font:inherit;background:#304254;color:white;border:1px solid #758b9e;padding:7px 10px;border-radius:6px}input[type=range]{accent-color:#e0b766}.screen{height:min(72dvh,780px);border:1px solid #3d4b5b;background:black;display:flex;align-items:center;justify-content:center;overflow:hidden;border-radius:8px}#stage{height:100%;width:100%;display:flex;align-items:center;justify-content:center}#stage svg{max-width:100%;max-height:100%;height:100%;width:100%}#seek{width:100%}#status{color:#bbcedb}#stageShell:fullscreen{height:100dvh;width:100vw;border:0;border-radius:0}@media(max-width:650px){.screen{height:58dvh}header,main{padding:8px}}'''

def page(slug, voice_files):
    data=json.dumps(voice_files,ensure_ascii=False).replace('</','<\\/')
    return (f'''<!doctype html>\n{MARK}\n<html lang="pt-BR" data-slug="{html.escape(slug,quote=True)}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Estúdio SVG — Player vetorial</title><style>{CSS}</style></head><body>
<header><strong>Estúdio SVG · Player vetorial experimental</strong><a href="../portal/">Voltar ao portal</a></header>
<main><div class="toolbar"><button id="play">▶ Reproduzir</button><button id="full">⛶ Tela cheia</button><label><input id="narrate" type="checkbox" checked> Narrar</label><label>Voz <input id="rate" type="range" min="0.8" max="1.6" value="1.15" step="0.05"><output id="rateOut">1.15×</output></label><label>Idioma da voz <select id="lang"><option value="pt-BR">Português (Brasil)</option><option value="en-US">English</option><option value="es-ES">Español</option><option value="fr-FR">Français</option></select></label></div>
<div id="stageShell" class="screen"><div id="stage" aria-label="Apresentação"></div></div>
<input id="seek" type="range" min="0" max="1000" value="0" aria-label="Posição"><div><span id="clock">00:00</span> · <span id="scene"></span></div><p id="status" role="status">Carregando…</p></main>
<script>window.__voiceFiles={data};</script><script src="./player.js"></script></body></html>''')

def inline_image_refs(markup, repo, stage, pub, scene_num, warnings):
    """Converte imagens SVG relativas em data URIs, sem pré-renderizar PNGs."""
    image_tag=re.compile(r'<image\b[^>]*>',re.I|re.S)
    href_attr=re.compile(r'((?:xlink:)?href\s*=\s*)(["\'])(.*?)\2',re.I|re.S)
    def tag_replace(m):
        tag=m.group(0)
        def ref_replace(h):
            raw=html.unescape(h.group(3)).strip()
            if not raw or raw.startswith(('data:','blob:','#')):return h.group(0)
            parsed=urlsplit(raw)
            if parsed.scheme or raw.startswith(('//','/')):
                warnings.append(f'Cena {scene_num}: imagem SVG externa/não portátil: {raw[:100]}')
                return h.group(0)
            candidate=unquote(parsed.path).replace('\\','/')
            if candidate.startswith('./'):candidate=candidate[2:]
            if candidate.startswith('midia/'):candidate=candidate[6:]
            src=source_asset(repo,stage,pub,candidate)
            if not src or src.stat().st_size>20*1024*1024:
                warnings.append(f'Cena {scene_num}: referência SVG não incorporada: {raw[:100]}')
                return h.group(0)
            mime=mimetypes.guess_type(src.name)[0] or 'application/octet-stream'
            if not mime.startswith('image/'):
                warnings.append(f'Cena {scene_num}: mídia SVG não é imagem: {raw[:100]}')
                return h.group(0)
            uri='data:'+mime+';base64,'+base64.b64encode(src.read_bytes()).decode('ascii')
            return h.group(1)+h.group(2)+uri+h.group(2)
        return href_attr.sub(ref_replace,tag)
    return image_tag.sub(tag_replace,markup)

def git_info(repo):
    def git(*a):
        return subprocess.run(['git','-C',str(repo),*a],text=True,capture_output=True,check=True).stdout.strip()
    if Path(git('rev-parse','--show-toplevel')).resolve()!=repo:
        raise RuntimeError('Informe a raiz do repositório em --repo')
    print('Git branch:',git('branch','--show-current'),'HEAD:',git('rev-parse','--short','HEAD'))
    print('Alterações locais (somente leitura):\n'+(git('status','--short') or 'nenhuma'))

def source_asset(repo, stage, pub, filename):
    f=Path(filename)
    if f.is_absolute() or '..' in f.parts or '\\' in filename:return None
    for root in (repo/'midia',pub/'midia',stage/'midia'):
        p=root/f
        if p.is_file() and p.resolve().is_relative_to(root.resolve()):return p
    return None

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--repo',default='~/estudio_svg_v3_git')
    ap.add_argument('--stage',default='~/estudio_player_stage')
    ap.add_argument('--slug',default='higiene-do-sono')
    ap.add_argument('--apply',action='store_true')
    args=ap.parse_args(); repo=Path(args.repo).expanduser().resolve();stage=Path(args.stage).expanduser().resolve()
    if not re.fullmatch(r'[a-z0-9-]{1,80}',args.slug):raise RuntimeError('Slug inválido')
    git_info(repo)
    if stage.is_relative_to(repo) or repo.is_relative_to(stage):raise RuntimeError('Stage e repositório não podem estar contidos um no outro')
    pub=stage/'apresentacoes'/args.slug; path=pub/'projeto.json'
    if not path.is_file():raise FileNotFoundError(path)
    project=json.loads(path.read_text('utf-8')); scenes=project.get('cenas')
    if not isinstance(scenes,list) or not scenes:raise RuntimeError('Projeto sem cenas')
    sys.dont_write_bytecode=True
    sys.path.insert(0,str(repo));graphics=importlib.import_module('graphics')
    renderer=getattr(graphics,'visualize',None)
    if not callable(renderer):raise RuntimeError('graphics.visualize indisponível neste checkout')
    sig=inspect.signature(renderer)
    params=sig.parameters
    if 'media_dir' not in params or 'width' not in params or 'height' not in params:
        raise RuntimeError('Assinatura de graphics.visualize diferente: '+str(sig))
    media_roots=[repo/'midia',pub/'midia',stage/'midia']
    names=[c.get('imagem',{}).get('arquivo') for c in scenes if isinstance(c.get('imagem'),dict)]
    names=[n for n in names if isinstance(n,str) and n]
    counts=[sum(bool(source_asset(repo,stage,pub,n) and (root/n).is_file()) for n in names) for root in media_roots]
    media_dir=media_roots[counts.index(max(counts))]
    print('Mídia utilizada:',media_dir,'imagens locais:',max(counts),'/',len(names))
    dest=stage/'vetorial'; pagepath=dest/'index.html'
    if pagepath.exists() and MARK not in pagepath.read_text('utf-8',errors='replace'):
        raise RuntimeError('Destino vetorial/index.html preexistente e não pertencente ao integrador; preservado')
    video=project.get('video',{});width=int(video.get('width') or 1280);height=int(video.get('height') or 720)
    if width<1 or height<1:raise RuntimeError('Dimensões inválidas')
    result=[];warnings=[]
    for i,c in enumerate(scenes):
        clean=copy.deepcopy(c);clean['animacoes']=[]
        opts={'p':1.0,'idx':i,'total':len(scenes),'media_dir':media_dir,'width':width,'height':height}
        opts={k:v for k,v in opts.items() if k in params}
        generated=renderer(clean,**opts)
        if not isinstance(generated,str) or not generated.lstrip().startswith('<svg'):
            raise RuntimeError('Renderizador retornou conteúdo inesperado na cena '+str(i+1))
        generated=inline_image_refs(generated,repo,stage,pub,i+1,warnings)
        if re.search(r'\b(?:src|href)=["\']\s*/api/',generated):warnings.append('Cena '+str(i+1)+': recurso dependente de /api/')
        image=c.get('imagem') if isinstance(c.get('imagem'),dict) else {}
        filename=image.get('arquivo')
        if isinstance(filename,str) and filename:
            if source_asset(repo,stage,pub,filename) is None:
                warnings.append('Cena '+str(i+1)+': imagem original não encontrada: '+filename)
            elif 'data:image/' not in generated:
                warnings.append('Cena '+str(i+1)+': imagem referenciada mas não incorporada pelo gerador: '+filename)
        result.append(generated)
    voices={}; voice_copies=[]
    for c in scenes:
        a=c.get('audio') if isinstance(c.get('audio'),dict) else {}
        filename=a.get('voice_file') or ''
        if not isinstance(filename,str) or not filename:continue
        src=source_asset(repo,stage,pub,filename)
        if src:
            safe=Path(filename); target=dest/'midia'/safe
            voices[filename]='./midia/'+safe.as_posix();voice_copies.append((src,target))
        else:warnings.append('Narração não localizada: '+filename+' (fallback para síntese do navegador)')
    for src,target in voice_copies:
        if target.exists() and target.read_bytes()!=src.read_bytes():
            raise RuntimeError('Conflito de mídia preservado: '+str(target))
    print('Cenas:',len(result),'SVG gerados (um por cena); animação em tempo de execução JS')
    for w in warnings:print('AVISO:',w)
    if not args.apply:
        print('SIMULAÇÃO: não foi alterado nenhum arquivo. Para gravar, acrescente --apply.')
        return
    (dest/'cenas').mkdir(parents=True,exist_ok=True)
    for i,svg in enumerate(result,1):
        (dest/'cenas'/f'cena-{i:03d}.svg').write_text(svg,'utf-8')
    for src,target in voice_copies:
        target.parent.mkdir(parents=True,exist_ok=True)
        if not target.exists():shutil.copy2(src,target)
    pagepath.write_text(page(args.slug,voices),'utf-8')
    (dest/'player.js').write_text(JS,'utf-8')
    portal=stage/'portal'/'index.html'
    if portal.is_file():
        original=portal.read_text('utf-8')
        link='<a id="vetorial-poc-link" href="../vetorial/" style="color:#9feacb">Abrir motor vetorial (experimental)</a>'
        if 'id="vetorial-poc-link"' not in original:
            if '<!-- ESTUDIO_PLAYER_PORTAL_V1 -->' in original and '</header>' in original:
                backup=portal.with_name('index.html.antes_vetorial_poc.bak')
                if not backup.exists():backup.write_text(original,'utf-8')
                portal.write_text(original.replace('</header>',link+'</header>',1),'utf-8')
            else:print('Portal não reconhecido; preservado. O player pode ser aberto diretamente.')
    print('PRONTO:',dest/'index.html')
    print('URL: http://127.0.0.1:8877/vetorial/')
    print('Git: não modificado; publicação original preservada.')

if __name__=='__main__':
    try:main()
    except Exception as e:
        print('ERRO:',e,file=sys.stderr);sys.exit(2)
