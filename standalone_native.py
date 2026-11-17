"""Embeds GIL runtime, native objects and referenced media into a portable HTML.

All source modules are taken from the explicit installed runtime allowlist.
No external resources and no alternative animation evaluator.
"""
from __future__ import annotations
import base64
import json
import posixpath
import re
from pathlib import Path
from mimetypes import guess_type
from gil_runtime_paths import MODULES

IMPORT_PATTERN = re.compile(r'''(?P<head>\b(?:from|import)\s*['"])(?P<path>\.{1,2}/[^'"]+)(?P<tail>['"])''')


def embed_modules(runtime_root: str | Path, app_root: str | Path) -> str:
    root = Path(runtime_root).resolve()
    if not (root / 'src/model.mjs').is_file():
        raise ValueError('Runtime GIL ausente: informe RD_GIL_ROOT ao iniciar o Estúdio.')
    studio = Path(app_root).resolve() / 'web'
    gil_allowed = set(MODULES)
    extra = {'scene-objects.mjs', 'gil-native.mjs', 'viewport-affine.mjs'}
    scripts = {}
    for target in sorted(gil_allowed | {'studio/' + f for f in extra}):
        if target.startswith('studio/'):
            source = studio / target[7:]
            key = '@studio/' + target[7:]
        else:
            source = root / target
            key = '@gil/' + target
        if not source.is_file() or source.is_symlink() or source.stat().st_size > 2_000_000:
            raise ValueError('Dependência GIL indisponível: ' + target)
        contents = source.read_text(encoding='utf-8')
        def rewrite(match):
            relative = match.group('path').split('?', 1)[0].split('#', 1)[0]
            path = posixpath.normpath(posixpath.join(posixpath.dirname(target), relative))
            if target.startswith('studio/') and path.startswith('studio/gil-runtime/'):
                path = path[len('studio/gil-runtime/'):]
            if path in gil_allowed:
                spec = '@gil/' + path
            elif path.startswith('studio/') and path[7:] in extra:
                spec = '@studio/' + path[7:]
            else:
                raise ValueError(f'Dependência não autorizada em {target}: {relative}')
            return match.group('head') + spec + match.group('tail')
        contents = IMPORT_PATTERN.sub(rewrite, contents)
        scripts[key] = 'data:text/javascript;base64,' + base64.b64encode(contents.encode('utf-8')).decode('ascii')
    return '<script type="importmap">' + json.dumps({'imports': scripts}, separators=(',', ':')) + '</script>'


def embed_media(project: dict, media_root: Path) -> dict[str, str]:
    used = set()
    for scene in project['cenas']:
        for obj in scene.get('objetos_midia') or []:
            if obj.get('kind') in ('image', 'video') and obj.get('file'):
                used.add(obj['file'])
    result = {}
    for filename in sorted(used):
        if not re.fullmatch(r'[A-Za-z0-9_.-]{1,255}', filename):
            raise ValueError('Nome de mídia inválido: ' + filename)
        media = media_root / filename
        if not media.is_file() or media.is_symlink():
            raise ValueError('Mídia ausente: ' + filename)
        if media.stat().st_size > 120_000_000:
            raise ValueError('Mídia grande demais para HTML único: ' + filename)
        mime = guess_type(filename)[0] or 'application/octet-stream'
        if not (mime.startswith('image/') or mime.startswith('video/')):
            raise ValueError('Mídia não suportada para HTML independente: ' + filename)
        result[filename] = 'data:' + mime + ';base64,' + base64.b64encode(media.read_bytes()).decode('ascii')
    return result


NATIVE_BOOT = '''<script type="module">
import {syncObjects,pauseObjects} from '@studio/scene-objects.mjs';
import {updateLayer} from '@studio/gil-native.mjs';
const data=window.__RD_NATIVE_DATA;
const frame=document.getElementById('frame');
try {
  const dim={width:data.width,height:data.height};
  let last=-1;
  window.__RD_NATIVE_STOP=()=>pauseObjects(frame);
  window.__RD_NATIVE_FRAME=(i,time,playing)=>{
    if(i!==last){pauseObjects(frame);last=i;}
    const scene=data.scenes[i];
    updateLayer(frame,scene.gil_native||null,time,dim);
    syncObjects(frame,scene.objects||[],time,dim,playing,1,
      e=>document.getElementById('note').textContent='Mídia: '+e,
      name=>data.native_assets[name]||'');
  };
  document.getElementById('start').disabled=false;
  document.getElementById('note').textContent='GIL carregada. Pronto para reproduzir offline.';
} catch(e) {
  document.getElementById('note').textContent='Falha ao iniciar GIL offline: '+e.message;
}
</script>'''


def attach_native(page: str, runtime_root: str | Path, app_root: Path) -> str:
    mapping = embed_modules(runtime_root, app_root)
    old = 'const data=JSON.parse(new TextDecoder().decode(bytes));'
    if old not in page or '  const clip=s.clip||{};' not in page:
        raise ValueError('Template HTML incompatível com GIL nativa.')
    page = page.replace(old, old + 'window.__RD_NATIVE_DATA=data;document.getElementById("start").disabled=true;', 1)
    page = page.replace('  const clip=s.clip||{};', '  window.__RD_NATIVE_FRAME?.(i,time,playing);\n  const clip=s.clip||{};', 1)
    page = page.replace('function stop(){playing=false;', 'function stop(){window.__RD_NATIVE_STOP?.();playing=false;', 1)
    page = page.replace('</head>', mapping + '</head>', 1)
    page = page.replace('</body>', NATIVE_BOOT + '</body>', 1)
    return page
