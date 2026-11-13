#!/usr/bin/env python3
"""Integração experimental, reversível, da publicação Estúdio SVG V3 no Termux.
Não modifica o repositório, não executa git add/commit/push.
"""
from __future__ import annotations
import argparse
import hashlib
import html
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit

MARKER = '<!-- ESTUDIO_PLAYER_PORTAL_V1 -->'
IMAGE_EXT = {'.png', '.jpg', '.jpeg', '.webp', '.gif', '.bmp', '.svg', '.avif'}
AUDIO_EXT = {'.mp3', '.wav', '.ogg', '.m4a', '.aac', '.opus'}
MEDIA_EXT = IMAGE_EXT | AUDIO_EXT
MAX_COPY = 60 * 1024 * 1024
AUDIO_BRIDGE_NAME = 'estudio-voz-stage-v1.js'
AUDIO_BRIDGE_JS = r"""// Estúdio SVG · adaptação de áudio somente para a publicação experimental.
(() => {
  'use strict';
  if (window.__estudioVozStageV1) return;
  window.__estudioVozStageV1 = true;
  let rate = 1.15;
  const adjust = el => {
    if (!(el instanceof HTMLAudioElement)) return;
    try { el.defaultPlaybackRate = rate; el.playbackRate = rate; } catch (_) {}
  };
  const originalPlay = HTMLMediaElement.prototype.play;
  HTMLMediaElement.prototype.play = function (...args) {
    adjust(this); // inclui objetos de áudio criados por JS sem inserção no DOM
    return originalPlay.apply(this, args);
  };
  const refresh = () => document.querySelectorAll('audio').forEach(adjust);
  document.addEventListener('play', ev => adjust(ev.target), true);
  window.addEventListener('message', ev => {
    if (ev.origin !== location.origin || ev.data?.type !== 'estudio-stage-voice-rate') return;
    const next = Number(ev.data.rate);
    if (Number.isFinite(next) && next >= 0.75 && next <= 1.75) {
      rate = next;
      refresh();
    }
  });
  document.addEventListener('DOMContentLoaded', () => {
    refresh();
    new MutationObserver(refresh).observe(document.documentElement, {subtree:true,childList:true});
  });
  if ('speechSynthesis' in window && typeof speechSynthesis.speak === 'function') {
    const originalSpeak = speechSynthesis.speak.bind(speechSynthesis);
    try {
      speechSynthesis.speak = utterance => {
        if (utterance && 'rate' in utterance) utterance.rate = rate;
        return originalSpeak(utterance);
      };
    } catch (_) { /* implementação do navegador não permite a substituição */ }
  }
})();
"""


def inject_audio_bridge(pub: Path, stage: Path, dry_run: bool) -> None:
    htmlpath = pub / 'index.html'
    original = htmlpath.read_text(encoding='utf-8')
    bridge_path = stage/'assets'/'estudio-player'/AUDIO_BRIDGE_NAME
    if bridge_path.exists() and bridge_path.read_text(encoding='utf-8') != AUDIO_BRIDGE_JS:
        raise FileExistsError('Script de integração já existe e é diferente; preservado: '+str(bridge_path))
    snippet = '<script src="../../assets/estudio-player/'+AUDIO_BRIDGE_NAME+'"></script>'
    if snippet not in original:
        if not re.search(r'<head(?:\s[^>]*)?>', original, re.I):
            raise RuntimeError('HTML publicado sem <head>; não é seguro injetar o controle de voz')
        backup = pub/'index.html.antes_integracao_stage.bak'
        if backup.exists() and backup.read_text(encoding='utf-8') != original:
            raise RuntimeError('Backup da página original diverge da atual; nenhuma substituição realizada')
        if dry_run:
            print('  PROPOSTO: script de áudio antes do player em '+str(htmlpath))
        else:
            if not backup.exists(): backup.write_text(original,encoding='utf-8')
            updated = re.sub(r'(<head(?:\s[^>]*)?>)', lambda m:m.group(1)+'\n'+snippet, original, count=1, flags=re.I)
            # O script é testado como parte da página publicada, nunca no código-fonte do editor.
            htmlpath.write_text(updated,encoding='utf-8')
    if not dry_run:
        bridge_path.parent.mkdir(parents=True,exist_ok=True)
        bridge_path.write_text(AUDIO_BRIDGE_JS,encoding='utf-8')



def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for part in iter(lambda: f.read(1024 * 1024), b''):
            h.update(part)
    return h.hexdigest()


def media_ref(s: str) -> str | None:
    """Devolve caminho relativo confiável, sem ../../, URL ou data URI."""
    if not isinstance(s, str):
        return None
    s = s.strip()
    if re.match(r'^[a-z][a-z\d+.-]*:', s, re.I) or s.startswith(('/', '\\', '#', '//')):
        return None
    s = unquote(urlsplit(s).path).replace('\\', '/')
    parts = s.split('/')
    if not s or any(p in ('', '.', '..') for p in parts):
        return None
    if Path(s).suffix.lower() not in MEDIA_EXT:
        return None
    return s


def refs_from_json(value) -> set[str]:
    found = set()
    if isinstance(value, dict):
        for v in value.values():
            found.update(refs_from_json(v))
    elif isinstance(value, list):
        for v in value:
            found.update(refs_from_json(v))
    elif isinstance(value, str):
        ref = media_ref(value)
        if ref:
            found.add(ref)
        if '<' in value and ('href=' in value or 'src=' in value):
            for link in re.findall(r'''(?:href|src)\s*=\s*["']([^"']+)["']''', value, flags=re.I):
                ref = media_ref(link)
                if ref:
                    found.add(ref)
    return found


def safe_slug(slug: str) -> bool:
    return bool(re.fullmatch(r'[a-z0-9](?:[a-z0-9-]{0,78}[a-z0-9])?', slug))


def save_if_unchanged_or_absent(src: Path, dest: Path) -> str:
    if dest.exists():
        if digest(src) == digest(dest):
            return 'existente'
        return 'CONFLITO (preservado)'
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)
    return 'copiado'


def source_file(repo: Path, ref: str) -> Path | None:
    rel = Path(ref)
    options = [repo / 'midia' / rel, repo / 'midia' / rel.name]
    if rel.parts and rel.parts[0] in ('midia', 'media', 'assets'):
        options.append(repo / 'midia' / Path(*rel.parts[1:]))
    for file in options:
        # Resolve fisicamente para evitar seguir symlinks externos ao repo/midia.
        if file.is_file() and file.resolve().is_relative_to((repo / 'midia').resolve()):
            return file
    return None


def public_targets(stage: Path, pub: Path, ref: str) -> list[Path]:
    p = Path(ref)
    if p.parts[0] in ('midia', 'media') and len(p.parts) > 1:
        p = Path(*p.parts[1:])
    elif p.parts[0] == 'assets' and len(p.parts) > 1:
        return [pub / ref]
    # Dois locais comuns para publicações servidas na raiz e em subpastas.
    return [pub / 'midia' / p, stage / 'midia' / p]


def list_media_map(stage: Path, pub: Path, slug: str) -> dict[str, str]:
    files = {}
    roots = [pub / 'midia', pub / 'assets', stage / 'midia']
    for root in roots:
        if not root.is_dir():
            continue
        for p in sorted(root.rglob('*')):
            if p.is_file() and p.suffix.lower() in IMAGE_EXT:
                name = p.name
                relative_url = '/' + p.relative_to(stage).as_posix()
                if name in files and files[name] != relative_url:
                    # Prefere a cópia específica da publicação à cópia global.
                    continue
                files[name] = relative_url
    return files


def lang_from_project(data: dict) -> str:
    for k in ('idioma', 'language', 'lang'):
        v = data.get(k)
        if isinstance(v, str) and re.fullmatch(r'[a-zA-Z]{2,3}(?:-[a-zA-Z]{2,4})?', v):
            return v.split('-')[0].lower()
    return 'pt'


def portal_html(slug: str, title: str, media: dict[str, str], source_lang: str) -> str:
    # O portal não usa rede externa, bibliotecas nem recursos de terceiros.
    name = html.escape(title)
    slug_js = json.dumps(slug, ensure_ascii=False)
    media_js = json.dumps(media, ensure_ascii=False).replace('</', '<\\/')
    lang_js = json.dumps(source_lang)
    return f'''<!doctype html>
{MARKER}
<html lang="pt-BR"><head><meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>Estúdio SVG · {name}</title>
<style>
:root {{color-scheme:dark;font:15px system-ui,sans-serif}}
* {{box-sizing:border-box}}body {{margin:0;background:#111820;color:#f4f6f8}}
header {{padding:12px 16px;display:flex;flex-wrap:wrap;gap:12px;align-items:center;justify-content:space-between;background:#23303c}}
header strong {{font-size:1.06rem}}main {{max-width:1320px;margin:0 auto;padding:12px}}
.toolbar {{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:10px}}
label {{display:inline-flex;align-items:center;gap:8px}}
input,select,button,a {{font:inherit}} select,button {{background:#334453;color:white;border:1px solid #8794a0;border-radius:7px;padding:8px}}
button {{cursor:pointer}} button:focus-visible,select:focus-visible {{outline:2px solid #f6d279}}
input[type=range] {{accent-color:#f1ce70;min-width:90px}}
.frame {{border:1px solid #4b6479;border-radius:9px;overflow:hidden;background:black}}
iframe {{display:block;width:100%;height:min(70dvh,730px);border:0;background:#090909}}
#status {{font-size:.9rem;min-height:1.5em;color:#d5dfe8;margin:8px 0}}
small {{color:#c5d1d9}} a {{color:#d2e8ff}}
@media(max-width:620px) {{iframe {{height:58dvh}}.toolbar label {{flex:1}}.toolbar button {{flex:auto}}}}
</style></head><body>
<header><strong>Estúdio SVG — apresentação: {name}</strong>
<span><a href="../apresentacoes/{html.escape(slug, quote=True)}/" target="_blank" rel="noopener">Abrir apresentação</a> · <a href="../apresentacoes/catalog.json" target="_blank" rel="noopener">Catálogo JSON</a></span></header>
<main><section class="toolbar" aria-label="Controles da apresentação">
<label>Voz <input id="rate" type="range" min="1" max="1.5" step="0.05" value="1.15"><output id="rateout">1,15×</output></label>
<label>Idioma <select id="lang"><option value="auto">Automático (navegador)</option>
<option value="pt">Português</option><option value="en">English</option><option value="es">Español</option>
<option value="fr">Français</option><option value="de">Deutsch</option></select></label>
<button id="translate" type="button">Traduzir texto, se disponível</button>
<button id="reload" type="button">Recarregar</button></section>
<div class="frame"><iframe id="player" title="Apresentação {name}" src="../apresentacoes/{html.escape(slug, quote=True)}/" allow="autoplay; fullscreen" allowfullscreen></iframe></div>
<p id="status" role="status" aria-live="polite">Carregando apresentação...</p>
<small>Velocidade aplicada a elementos de áudio acessíveis. Se a locução estiver vinculada a outro motor, o controle pode não afetá-la. O idioma da narração gravada não muda com a tradução do texto. No Android, use também o menu do navegador → Traduzir.</small>
</main><script>
'use strict';
const SLUG={slug_js};
const FILES={media_js};
const SOURCE_LANG={lang_js};
const frame=document.getElementById('player');
const rate=document.getElementById('rate');
const lang=document.getElementById('lang');
const status=document.getElementById('status');
const rateout=document.getElementById('rateout');
let observer=null, scans=0, repaired=new WeakSet(), rebinds=0, seenAudio=new WeakSet();
const userLang=(navigator.languages && navigator.languages.length ? navigator.languages[0] : navigator.language || 'pt').split('-')[0];
function desiredLang() {{return lang.value==='auto' ? userLang : lang.value;}}
function show(s) {{status.textContent=s;}}
function getDoc() {{try {{return frame.contentDocument;}} catch (_) {{return null;}}}}
function rateAudio(el) {{
  if(!(el instanceof frame.contentWindow.HTMLAudioElement)) return;
  try {{el.defaultPlaybackRate=Number(rate.value);el.playbackRate=Number(rate.value);seenAudio.add(el);}} catch (_) {{}}
}}
function fileName(raw) {{
  if (!raw || /^data:|^blob:/i.test(raw)) return null;
  try {{return decodeURIComponent(new URL(raw, frame.contentWindow.location.href).pathname.split('/').pop());}}
  catch(_) {{return null;}}
}}
function repairImage(el) {{
  const svg=el.localName.toLowerCase()==='image';
  const attr=svg ? (el.getAttribute('href')??el.getAttribute('xlink:href')) : el.getAttribute('src');
  const name=fileName(attr);
  if (!name || !Object.prototype.hasOwnProperty.call(FILES,name)) return;
  const target=new URL(FILES[name], location.origin).href;
  if (attr && new URL(attr,frame.contentWindow.location.href).href===target) return;
  if (!svg && el.complete && el.naturalWidth>0) return;
  if (svg) {{el.setAttribute('href', target);}}
  else {{el.setAttribute('src', target);}}
  if(!repaired.has(el)) {{repaired.add(el);rebinds++;}}
}}
function scan() {{
  const doc=getDoc();if(!doc) return;
  try {{frame.contentWindow.postMessage({{type:'estudio-stage-voice-rate',rate:Number(rate.value)}},location.origin);}} catch (_) {{}}
  doc.querySelectorAll('audio').forEach(rateAudio);
  doc.querySelectorAll('img,svg image').forEach(repairImage);
  scans++;
  show('Navegador: '+(navigator.languages||[navigator.language]).join(', ')+
    ' · origem: '+SOURCE_LANG+' · destino: '+desiredLang()+
    ' · imagens com caminho ajustado: '+rebinds+
    ' · velocidade solicitada: '+Number(rate.value).toFixed(2)+'×');
}}
let queued=false;
function scheduleScan() {{if(queued)return;queued=true;requestAnimationFrame(()=>{{queued=false;scan();}});}}
frame.addEventListener('load',()=>{{
  observer?.disconnect();rebinds=0;repaired=new WeakSet();
  const doc=getDoc();if(!doc) {{show('Player fora da mesma origem: controles internos indisponíveis.');return;}}
  scan();
  observer=new MutationObserver(scheduleScan);
  observer.observe(doc.documentElement,{{subtree:true,childList:true}});
  doc.addEventListener('play',e=>{{if(e.target instanceof frame.contentWindow.HTMLAudioElement)rateAudio(e.target);}},true);
  doc.addEventListener('error',e=>{{if(e.target?.matches?.('img,svg image'))repairImage(e.target);}},true);
}});
rate.addEventListener('input',()=>{{rateout.value=Number(rate.value).toFixed(2).replace('.',',')+'×';scan();}});
lang.addEventListener('change',()=>{{document.documentElement.lang=desiredLang();scan();}});
document.getElementById('reload').addEventListener('click',()=>{{frame.contentWindow.location.reload();}});
async function translateText() {{
  const target=desiredLang(); const doc=getDoc();
  if(!doc) {{show('Player inacessível para tradução.');return;}}
  if(target===SOURCE_LANG) {{show('O idioma selecionado já é o original ('+SOURCE_LANG+').');return;}}
  if(!('Translator' in window)) {{show('Tradução por API indisponível neste navegador. No Android, use o menu ⋮ → Traduzir.');return;}}
  try {{
    const cfg={{sourceLanguage:SOURCE_LANG,targetLanguage:target}};
    const availability=await Translator.availability(cfg);
    if(availability==='unavailable') throw new Error('Par de idiomas indisponível');
    const translator=await Translator.create(cfg);
    const nodes=[];
    const root=doc.body || doc.documentElement;
    const walker=doc.createTreeWalker(root,NodeFilter.SHOW_TEXT);
    while(walker.nextNode() && nodes.length<75) {{
      const n=walker.currentNode;const parent=n.parentElement;
      if(!parent || parent.closest('script,style,button,input,select,textarea'))continue;
      if(n.nodeValue.trim().length<3 || n.nodeValue.length>300)continue;
      nodes.push([n,n.nodeValue]);
    }}
    let completed=0;
    for(const [node,original] of nodes) {{
      if(!node.isConnected)continue;
      const out=await translator.translate(original.trim());
      if(!node.isConnected)continue;
      node.nodeValue=original.replace(original.trim(),out);completed++;
    }}
    translator.destroy?.();
    show('Traduzidos '+completed+' trechos textuais para '+target+'. Áudio gravado permanece no idioma original.');
  }} catch(err) {{show('Tradução não concluída: '+err.message+'. Use o menu de tradução do navegador.');}}
}}
document.getElementById('translate').addEventListener('click',translateText);
show('Idioma preferido do navegador: '+userLang+' · origem: '+SOURCE_LANG+' · aguardando player.');
</script></body></html>
'''


def run(repo: Path, stage: Path, slug: str, dry_run: bool) -> int:
    repo = repo.expanduser().resolve()
    stage = stage.expanduser().resolve()
    if not safe_slug(slug):
        raise ValueError('Slug inválido')
    if not repo.is_dir():
        raise FileNotFoundError(f'Repositório inexistente: {repo}')
    gitroot = subprocess.run(['git','-C',str(repo),'rev-parse','--show-toplevel'],capture_output=True,text=True,check=True).stdout.strip()
    if Path(gitroot).resolve() != repo:
        raise RuntimeError('O --repo informado não é a raiz do repositório Git')
    branch = subprocess.run(['git','-C',str(repo),'branch','--show-current'],capture_output=True,text=True,check=True).stdout.strip()
    head = subprocess.run(['git','-C',str(repo),'rev-parse','--short','HEAD'],capture_output=True,text=True,check=True).stdout.strip()
    print(f'Git: {repo} · branch={branch} · HEAD={head}')
    if branch != 'release/v3-alpha4-rc1':
        raise RuntimeError(f'Branch inesperada: {branch}; esperado release/v3-alpha4-rc1. Nenhuma alteração efetuada.')
    print('Alterações locais (só leitura):')
    subprocess.run(['git','-C',str(repo),'status','--short'],check=True)
    pub = stage / 'apresentacoes' / slug
    for expected in (pub / 'manifest.json', pub / 'projeto.json', pub / 'index.html', stage / 'apresentacoes' / 'catalog.json', stage / 'assets' / 'estudio-player' / 'estudio-player-v1.js'):
        if not expected.is_file():
            raise FileNotFoundError(f'Exportação incompleta: {expected}')
    if stage.is_relative_to(repo) or repo.is_relative_to(stage):
        raise RuntimeError('A pasta de stage não pode conter/estar dentro do repositório')
    project = json.loads((pub/'projeto.json').read_text(encoding='utf-8'))
    manifest = json.loads((pub/'manifest.json').read_text(encoding='utf-8'))
    refs = sorted(refs_from_json(project) | refs_from_json(manifest))
    print(f'Arquivos de mídia referenciados no JSON: {len(refs)}')
    missing, conflicts, copied = [], [], []
    for ref in refs:
        src = source_file(repo,ref)
        if src is None:
            # Uma mídia que já exista na publicação não requer cópia.
            if not any(target.is_file() for target in public_targets(stage,pub,ref)):
                missing.append(ref)
            continue
        if src.stat().st_size > MAX_COPY:
            missing.append(ref+' (maior que 60 MiB; não copiado)')
            continue
        for target in public_targets(stage,pub,ref):
            if dry_run:
                print(f'  PROPOSTO: {src} → {target}')
                continue
            result = save_if_unchanged_or_absent(src,target)
            if result == 'copiado':
                copied.append(str(target))
            elif result.startswith('CONFLITO'):
                conflicts.append(str(target))
    if missing:
        print('Mídia não localizada na origem nem na publicação:')
        for item in missing: print('  AUSENTE:',item)
    if conflicts:
        print('Conflitos preservados (não sobrescritos):')
        for item in conflicts:print('  CONFLITO:',item)
    title = project.get('titulo') or project.get('title') or manifest.get('titulo') or 'Higiene do Sono'
    if not isinstance(title,str): title='Higiene do Sono'
    files = list_media_map(stage,pub,slug)
    portal = stage/'portal'/'index.html'
    if portal.exists() and MARKER not in portal.read_text(encoding='utf-8',errors='replace'):
        raise FileExistsError(f'{portal} já existe e não foi gerado por este script; arquivo preservado.')
    if not dry_run:
        portal.parent.mkdir(parents=True,exist_ok=True)
        portal.write_text(portal_html(slug,title,files,lang_from_project(project)), encoding='utf-8')
    inject_audio_bridge(pub,stage,dry_run)
    print(f'Arquivos de mídia copiados: {len(copied)}; imagens disponíveis no stage: {len(files)}')
    print(f'Página integrada: {portal}'+(' (simulação, sem gravação)' if dry_run else ''))
    print('Testar: http://127.0.0.1:8877/portal/')
    print('Original: http://127.0.0.1:8877/apresentacoes/'+slug+'/')
    return 1 if conflicts or missing else 0


def main() -> int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repo',default='~/estudio_svg_v3_git')
    p.add_argument('--stage',default='~/estudio_player_stage')
    p.add_argument('--slug',default='higiene-do-sono')
    p.add_argument('--dry-run',action='store_true')
    args=p.parse_args()
    try: return run(Path(args.repo),Path(args.stage),args.slug,args.dry_run)
    except Exception as e:
        print(f'ERRO: {e}',file=sys.stderr)
        return 2

if __name__=='__main__':sys.exit(main())
