"""Subtitle timing adapter for Edge-TTS SRT sidecars, read-only and deterministic.
Only returns bounded scene-relative cues; media files are never modified here.
"""
from __future__ import annotations
import math
import re

STAMP = re.compile(r'(?:(\d{1,2}):)?(\d{1,2}):(\d{2})[,.](\d{1,3})')
ARROW = re.compile(r'(?P<start>(?:\d{1,2}:)?\d{1,2}:\d{2}[,.]\d{1,3})\s*-->\s*(?P<end>(?:\d{1,2}:)?\d{1,2}:\d{2}[,.]\d{1,3})')


def seconds(value):
    m = STAMP.fullmatch(str(value).strip())
    if not m:
        raise ValueError('Timestamp inválido')
    h, minute, sec, fraction = m.groups()
    if int(minute) > 59 or int(sec) > 59:
        raise ValueError('Timestamp fora do intervalo')
    return 3600 * int(h or 0) + 60 * int(minute) + int(sec) + int(fraction.ljust(3, '0')) / 1000


def parse_srt(text, delay=0, limit=800):
    """Parse SRT/VTT word or phrase cues, bounded for persisted JSON scenes."""
    if not isinstance(text, str) or len(text) > 250_000:
        raise ValueError('Arquivo de legendas muito grande')
    if not math.isfinite(float(delay)) or delay < 0 or delay > 30:
        raise ValueError('Atraso de locução inválido')
    output=[]
    for block in re.split(r'\r?\n\s*\r?\n', text.replace('\r\n', '\n').strip()):
        lines=[line.strip() for line in block.split('\n')]
        pos=next((i for i,line in enumerate(lines) if ARROW.search(line)),None)
        if pos is None:continue
        match=ARROW.search(lines[pos])
        content=' '.join(line for line in lines[pos+1:] if line).strip()
        if not content:continue
        start=seconds(match.group('start'))+delay
        end=seconds(match.group('end'))+delay
        if not (0<=start<end<=3600):continue
        if len(content)>180:continue
        output.append({'start':round(start,3),'end':round(end,3),'text':content})
        if len(output)>limit:raise ValueError('Excesso de palavras nas legendas')
    return sorted(output,key=lambda c:(c['start'],c['end']))


def cues_for_voice(scene, project):
    """Read the SRT written in the same synthesis call as the cached Edge voice."""
    from studio_core import effective_voice
    selected=effective_voice(scene,project)
    if selected:
        if selected['provider']!='edge':return []
    elif project.get('motor_voz')!='edge-tts':return []
    audio=scene.get('audio') or {}
    if audio.get('voice_file') or not audio.get('voice_enabled') or audio.get('muted'):return []
    from studio_core import CACHE, tts_key, voice_source
    voice=voice_source(scene,project,required=False)
    if voice is None:return []
    path=CACHE/'voices'/(tts_key(scene,project)+'.srt')
    if not path.is_file() or path.is_symlink() or path.stat().st_size>250_000:return []
    return parse_srt(path.read_text(encoding='utf8'), float(audio.get('voice_delay',0)))
