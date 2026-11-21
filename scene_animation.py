"""Adaptador Python do motor de animação V3, fonte única: web_player/v3/runtime.js.

Não implementa easing/ciclos/pivôs. Todo cálculo vem da ponte Node persistente.
Em exportações, falha explicitamente se Node ou pivôs exatos forem indisponíveis.
"""
from __future__ import annotations
import atexit
import json
import os
from pathlib import Path
import select
import shutil
import subprocess
import threading
import xml.etree.ElementTree as ET

_BRIDGE = Path(__file__).resolve().parent / 'web_player/v3/animation_bridge.cjs'
_LOCK = threading.RLock()
_PROCESS = None


def _request(op, **data):
    global _PROCESS
    with _LOCK:
        if _PROCESS is None or _PROCESS.poll() is not None:
            node=shutil.which('node')
            if not node or not _BRIDGE.is_file():
                raise RuntimeError('Motor V3 obrigatório para exportação: instale Node.js e confira animation_bridge.cjs.')
            _PROCESS=subprocess.Popen([node,str(_BRIDGE)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,
                 stderr=subprocess.DEVNULL,text=True,bufsize=1,close_fds=True)
        try:
            _PROCESS.stdin.write(json.dumps({'op':op,**data},ensure_ascii=False,allow_nan=False)+'\n')
            _PROCESS.stdin.flush()
            ready,_,_=select.select([_PROCESS.stdout],[],[],20)
            if not ready:raise RuntimeError('Motor V3 não respondeu em 20 segundos')
            reply=_PROCESS.stdout.readline()
            if not reply:raise RuntimeError('Motor V3 encerrou a comunicação')
            payload=json.loads(reply)
            if not payload.get('ok'):
                raise RuntimeError('Animação V3: '+str(payload.get('error','erro desconhecido')))
            return payload['result']
        except (BrokenPipeError,ValueError,OSError):
            try:_PROCESS.kill()
            except OSError:pass
            _PROCESS=None
            raise


def _close():
    global _PROCESS
    with _LOCK:
        if _PROCESS is not None:
            try:_PROCESS.terminate();_PROCESS.wait(timeout=1)
            except (OSError,subprocess.TimeoutExpired):
                try:_PROCESS.kill()
                except OSError:pass
            _PROCESS=None

atexit.register(_close)


def ease(position,mode):return _request('ease',progress=position,mode=mode)
def progress_at(animation,position):return _request('progress',animation=animation,progress=position)


def _value(attrs,key,default=None):
    try:
        n=float(attrs.get(key,default));return n if __import__('math').isfinite(n) else default
    except (ValueError,TypeError):return default


def _record(element,root=None):
    attrs=dict(element.attrib)
    tag=element.tag.split('}')[-1]
    line=next((dict(e.attrib) for e in element.iter() if e is not element and e.tag.split('}')[-1]=='line'),None)
    bbox=None
    if tag=='line':
        x1=_value(attrs,'x1');x2=_value(attrs,'x2');y1=_value(attrs,'y1');y2=_value(attrs,'y2')
        if None not in (x1,x2,y1,y2):bbox={'x':min(x1,x2),'y':min(y1,y2),'width':abs(x2-x1),'height':abs(y2-y1)}
    elif tag in ('rect','image'):
        x=_value(attrs,'x',0);y=_value(attrs,'y',0);w=_value(attrs,'width');h=_value(attrs,'height')
        if w is not None and h is not None:bbox={'x':x,'y':y,'width':w,'height':h}
    elif tag in ('circle','ellipse'):
        x=_value(attrs,'cx');y=_value(attrs,'cy');rx=_value(attrs,'r') if tag=='circle' else _value(attrs,'rx')
        ry=rx if tag=='circle' else _value(attrs,'ry')
        if None not in (x,y,rx,ry):bbox={'x':x-rx,'y':y-ry,'width':2*rx,'height':2*ry}
    # SVG paths/groups have no trustworthy bbox without a renderer. Require explicit pivot.
    return {'id':attrs.get('id',''),'tag':tag,'attrs':attrs,'line':line,'bbox':bbox,
        'transform':attrs.get('transform',''),'opacity':attrs.get('opacity','1')}


def effects(animations,target,position,center=(640,360)):
    if not animations:return '',1.0
    attrs={'id':target,'data-pivot-x':str(center[0]),'data-pivot-y':str(center[1])}
    rows=_request('evaluate',records=[{'id':target,'tag':'g','attrs':attrs,'transform':'','opacity':'1'}],
        animations=animations,progress=position)
    return rows[0]['transform'],float(rows[0]['opacity'])


def animate_svg_fragment(fragment,animations,position):
    if not animations:return fragment
    root=ET.fromstring(fragment)
    elements=[el for el in root.iter() if el.get('id')]
    if not elements:return fragment
    rows=_request('evaluate',records=[_record(el,root) for el in elements],animations=animations,progress=position)
    byid={r['id']:r for r in rows}
    for el in elements:
        r=byid.get(el.get('id'))
        if not r or not r['animated']:continue
        if r['transform']:el.set('transform',r['transform'])
        else:el.attrib.pop('transform',None)
        el.set('opacity',r['opacity'])
    return ET.tostring(root,encoding='unicode')


def animate_markup(markup,animations,position,target,center):
    if not markup:return ''
    transform,opacity=effects(animations,target,position,center)
    if not transform and opacity==1:return markup
    return f'<g transform="{transform}" opacity="{opacity:.4f}">{markup}</g>'


def animate_image_markup(markup,animations,position,center):
    return animate_markup(markup,animations,position,'__imagem__',center)
