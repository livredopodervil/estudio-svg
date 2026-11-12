"""Produce compressed, shareable standalone audio, without rendering video.

FFmpeg is executed with argument lists (no shell); all destination paths use
validated project names and the existing render output directory.
"""
from __future__ import annotations
import json
from pathlib import Path
from studio_core import (OUTPUT, StudioError, batch_audio, project_audio_mix,
                         voice_source, sha_file, run, duration)

FORMATS={
    'mp3': ('libmp3lame','160k','.mp3'),
    'opus': ('libopus','96k','.opus'),
}

def encode(source, target, fmt, progress=lambda *_:None):
    if fmt not in FORMATS:raise StudioError('Formato de áudio desconhecido')
    source=Path(source)
    if not source.is_file() or source.stat().st_size==0:raise StudioError('Áudio de origem não disponível')
    codec,bitrate,_=FORMATS[fmt]
    signature=sha_file(source)+'|'+codec+'|'+bitrate+'|v1'
    meta=target.with_name(target.name+'.manifest.json')
    if target.is_file() and target.stat().st_size>100 and meta.is_file():
        try:
            if json.loads(meta.read_text())['signature']==signature:
                progress(1,'Áudio compactado recuperado do cache')
                return {'audio':target.name,'cached':True}
        except (OSError,ValueError,KeyError):pass
    temp=target.with_name(target.stem+'.partial'+target.suffix)
    progress(.80,'Compactando para '+fmt.upper())
    try:
        run(['ffmpeg','-hide_banner','-loglevel','error','-nostdin','-y',
             '-i',str(source),'-vn','-map','0:a:0','-c:a',codec,'-b:a',bitrate,
             '-ar','48000',str(temp)],timeout=max(120,int(duration(source)*3)))
        if not temp.is_file() or temp.stat().st_size<100 or duration(temp)<=0:
            raise StudioError('Falha ao validar a conversão de áudio')
        temp.replace(target)
        meta.write_text(json.dumps({'signature':signature,'format':fmt},indent=2))
    finally:temp.unlink(missing_ok=True)
    progress(1,'Arquivo de áudio pronto para compartilhar')
    return {'audio':target.name,'cached':False}

def export_project_audio(name,project,fmt,progress=lambda *_:None):
    if fmt not in FORMATS:raise StudioError('Formato não suportado')
    batch_audio(project,lambda p,msg:progress(p*.35,msg))
    mixed=project_audio_mix(name,project,lambda p,msg:progress(.35+p*.4,msg))
    return encode(OUTPUT/mixed['audio'],OUTPUT/(name+'_mix'+FORMATS[fmt][2]),fmt,progress)

def export_scene_voice(name,project,index,progress=lambda *_:None):
    if not isinstance(index,int) or index<1 or index>len(project['cenas']):
        raise StudioError('Número de cena inválido')
    scene=project['cenas'][index-1]
    if not scene['audio']['voice_enabled']:
        raise StudioError('Narração desativada nesta cena')
    voice=voice_source(scene,project,required=True)
    if voice is None:
        raise StudioError('Cena sem narração; grave voz ou gere síntese primeiro')
    return encode(voice,OUTPUT/(f'{name}_cena_{index:03d}_voz.mp3'),'mp3',progress)
