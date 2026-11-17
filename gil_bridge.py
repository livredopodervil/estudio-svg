"""Explicit local authoring adapter. Never writes a project or replaces media.
The video studio owns narration and mixing; GIL owns compilation and sampling.
"""
from __future__ import annotations
import hashlib, json, math, os, signal, subprocess, tempfile
from pathlib import Path

MAX_SOURCE=250_000
MAX_VIDEO=64*1024*1024

def sha_text(source):
    return hashlib.sha256(source.encode('utf8')).hexdigest()

def settings(data):
    if not isinstance(data,dict) or set(data)-{'source','format','duration','fps','long_side','effects'}:
        raise ValueError('Parâmetros de componente inválidos')
    source=data.get('source'); kind=data.get('format','gil'); length=data.get('duration'); fps=data.get('fps',24); side=data.get('long_side',960); effects=data.get('effects',False)
    if not isinstance(source,str) or not 0<len(source.encode('utf8'))<=MAX_SOURCE:raise ValueError('Fonte vazia ou acima de 250 kB')
    if kind not in ('gil','spatialseed') or type(fps)!=int or not 12<=fps<=30 or type(side)!=int or not 320<=side<=1280 or type(effects)!=bool:raise ValueError('Formato, FPS, resolução ou efeitos inválidos')
    if length is not None and (type(length) not in (int,float) or not math.isfinite(length) or not .5<=length<=60 or length*fps>1800):raise ValueError('Duração: 0,5–60 s e até 1800 quadros')
    return source,kind,length,fps,side,effects

def run(args,limit):
    # New process group includes Node, rasterizer and FFmpeg; no orphan on timeout.
    with tempfile.TemporaryFile() as log:
        p=subprocess.Popen([str(x) for x in args],stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        try: rc=p.wait(timeout=limit)
        except BaseException:
            try:os.killpg(p.pid,signal.SIGKILL)
            except ProcessLookupError:pass
            p.wait();raise
        if rc:
            log.seek(0,2);log.seek(max(0,log.tell()-1800));raise ValueError('Adaptador falhou: '+log.read().decode('utf8','replace'))

def render_component(data, gil_root, spatial_root, cache, store, inspect):
    source,kind,length,fps,side,effects=settings(data)
    if not gil_root:raise ValueError('Inicie pelo RD Studio integrado (RD_GIL_ROOT não configurado)')
    root=Path(gil_root).resolve(); export=root/'tools/export_mp4.py'; inspect_js=root/'tools/inspect_component.mjs'
    if not export.is_file() or not inspect_js.is_file():raise ValueError('Instale a ponte GIL atualizada antes de iniciar o serviço')
    import sys
    with tempfile.TemporaryDirectory(prefix='gil-bridge-',dir=cache) as tmp:
        d=Path(tmp); src=d/'source.gil'; provenance=sha_text(source)
        if kind=='spatialseed':
            if not spatial_root:raise ValueError('Inicie com --spatial apontando para o SpatialSeed recuperado')
            original=d/'original.json';original.write_text(source,encoding='utf8')
            run(['node','--max-old-space-size=256',root/'tools/import_spatialseed.mjs',original,src,Path(spatial_root).resolve()],60)
            source=src.read_text('utf8')
        else:src.write_text(source,encoding='utf8')
        info=d/'info.json';run(['node','--max-old-space-size=256',inspect_js,src,info],40)
        details=json.loads(info.read_text()); duration=details['duration'] if length is None else length
        if not .5<=duration<=min(60,details['duration']) or duration*fps>1800:raise ValueError('Trecho excede a composição ou o limite de 60 s / 1800 quadros')
        if effects and not details['cues']:effects=False
        clip=d/'clip.mp4';args=[sys.executable,export,src,clip,'--fps',fps,'--long-side',side,'--duration',duration]
        if not effects:args.append('--silent')
        run(args,900)
        if not 0<clip.stat().st_size<=MAX_VIDEO:raise ValueError('MP4 acima de 64 MiB; reduza a resolução ou duração')
        actual=inspect(clip,'video')
        if effects:inspect(clip,'audio')
        # Existing validated media ingest, no project write. Store only after both checks.
        filename=store(clip.read_bytes(),'video','.mp4')
        return {'filename':filename,'duration':actual,'effects':effects,'component':{'format':'gil-timeline-0.1','origin':kind,'origin_sha256':provenance,'source':source,'source_sha256':sha_text(source),'duration':actual}}
