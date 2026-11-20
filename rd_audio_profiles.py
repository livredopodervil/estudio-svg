"""RD Audio U3: declarative per-character/per-style profiles and safe FFmpeg pipeline.

No eval, no shell, no model download, no implicit voice fallback. Old score
syntax survives verbatim when no new directives occur. A text score is the
persistent source of truth; no new project schema field is required.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import uuid
import wave

ID = r'[a-z][a-z0-9_-]{0,31}'
DEF = re.compile(r'^@(perfil|processador)\s+('+ID+r')\s+(\{.*\})\s*$', re.I)
CHAR = re.compile(r'^@personagem\s+('+ID+r')\s+(.+)$', re.I)
FALA = re.compile(r'^@fala\s+(\d{1,2}:\d{2}(?:\.\d{1,3})?|\d{1,3}(?:\.\d{1,3})?)\s+(.+)$', re.I)
TAG = re.compile(r'^\[([a-z_]+)=([^\]\r\n]+)\]\s*',re.I)
KEYS = {'ritmo':(.70,1.30),'ganho':(0,2),'pausa':(0,1),
        'tom':(-100,100),'volume':(-100,100)}
VOICE = re.compile(r'^[a-z][a-z0-9_-]*:[a-zA-Z0-9._:-]{1,120}$|^[a-z][a-z0-9_-]{1,40}$')
FILTERS = {'highpass','lowpass','acompressor','alimiter','agate','equalizer',
           'loudnorm','volume','atempo','afftdn','deesser'}

class ProfileError(ValueError): pass

@dataclass
class Compiled:
    source: str
    lines: dict = field(default_factory=dict)
    profiles: dict = field(default_factory=dict)
    processors: dict = field(default_factory=dict)


def _config(raw, kind, line):
    if len(raw)>4000:raise ProfileError(f'Linha {line}: JSON muito grande')
    try: value=json.loads(raw)
    except json.JSONDecodeError as exc:raise ProfileError(f'Linha {line}: JSON inválido: {exc.msg}') from exc
    if not isinstance(value,dict):raise ProfileError(f'Linha {line}: esperado objeto JSON')
    allowed=set(KEYS)|{'voz','processador'} if kind=='perfil' else {'ffmpeg'}
    unknown=set(value)-allowed
    if unknown:raise ProfileError(f'Linha {line}: propriedades não reconhecidas: {sorted(unknown)}')
    if kind=='perfil':
        for k,(lo,hi) in KEYS.items():
            if k in value:
                v=value[k]
                if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or not lo<=v<=hi:
                    raise ProfileError(f'Linha {line}: {k} deve estar entre {lo} e {hi}')
        if 'voz' in value and not VOICE.fullmatch(str(value['voz'])):
            raise ProfileError(f'Linha {line}: voz inválida')
        if 'processador' in value and not re.fullmatch(ID,str(value['processador'])):
            raise ProfileError(f'Linha {line}: processador inválido')
    else:
        value['ffmpeg']=_filters(value.get('ffmpeg',[]),line)
    return value


def _filters(filters,line=0):
    if not isinstance(filters,list) or len(filters)>10:raise ProfileError(f'Linha {line}: ffmpeg exige lista de até 10 filtros')
    for v in filters:
        if not isinstance(v,str) or not 1<=len(v)<=250 or any(ch in v for ch in '\n\r;[]\\\x00'):
            raise ProfileError(f'Linha {line}: filtro FFmpeg inválido')
        name=v.split('=',1)[0]
        if name not in FILTERS:raise ProfileError(f'Linha {line}: filtro não autorizado: {name}')
    return filters


def _options(raw,line):
    result={}
    for arg in raw.split(',') if raw.strip() else []:
        if '=' not in arg:raise ProfileError(f'Linha {line}: opção exige chave=valor')
        k,v=(x.strip() for x in arg.split('=',1))
        if k in result:raise ProfileError(f'Linha {line}: opção repetida {k}')
        if k in KEYS:
            try: n=float(v)
            except ValueError: raise ProfileError(f'Linha {line}: número inválido') from None
            lo,hi=KEYS[k]
            if not math.isfinite(n) or not lo<=n<=hi:raise ProfileError(f'Linha {line}: {k} fora de {lo}–{hi}')
            result[k]=n
        elif k=='voz':
            if not VOICE.fullmatch(v):raise ProfileError(f'Linha {line}: voz inválida')
            result[k]=v
        else:raise ProfileError(f'Linha {line}: opção desconhecida: {k}')
    return result


def _tagline(line, lineno):
    m=FALA.fullmatch(line)
    if not m:return line
    at, rest=m.groups(); tags={}
    while rest.startswith('['):
        x=TAG.match(rest)
        if not x:raise ProfileError(f'Linha {lineno}: tag inválida')
        k,v=x.group(1).lower(),x.group(2).strip()
        if k not in ('personagem','emocao','estilo','ritmo','ganho','pausa','tom','volume','voz'):
            raise ProfileError(f'Linha {lineno}: tag desconhecida: {k}')
        if k in tags:raise ProfileError(f'Linha {lineno}: tag repetida: {k}')
        tags[k]=v;rest=rest[x.end():]
    text=rest.strip()
    if not text or '|' in text:raise ProfileError(f'Linha {lineno}: texto vazio ou contém |')
    role=tags.pop('personagem',None)
    if not role or not re.fullmatch(ID,role):raise ProfileError(f'Linha {lineno}: @fala exige [personagem=...]')
    style=tags.pop('estilo',tags.pop('emocao','neutro'))
    opts=','.join(f'{k}={v}' for k,v in tags.items())
    return f'{at} | {role} | {style} | {opts} | {text}'


def compile_score(source):
    if not isinstance(source,str) or len(source)>30000 or '\x00' in source:
        raise ProfileError('Roteiro inválido ou muito grande')
    raw_lines=source.splitlines()
    profiles={};processors={}; chars={}
    for n,raw in enumerate(raw_lines,1):
        line=raw.strip();m=DEF.fullmatch(line)
        if m:
            kind,name,payload=m.groups();group=profiles if kind.lower()=='perfil' else processors
            if name in group:raise ProfileError(f'Linha {n}: perfil/processador duplicado: {name}')
            if len(group)>=32:raise ProfileError('Limite: 32 perfis/processadores')
            group[name]=_config(payload,kind.lower(),n)
        elif line.startswith('@perfil ') or line.startswith('@processador '):
            raise ProfileError(f'Linha {n}: diretiva malformada; use @perfil nome {{...}}')
    for name,p in profiles.items():
        if 'processador' in p and p['processador'] not in processors:
            raise ProfileError(f'Perfil {name}: processador não definido: {p["processador"]}')
    out=[];metadata={}
    for n,raw in enumerate(raw_lines,1):
        line=raw.strip()
        if DEF.fullmatch(line):out.append('# perfil definido');continue
        mc=CHAR.fullmatch(line)
        if mc:
            name,tail=mc.groups();tokens=tail.split();style=None;voice=None
            for item in tokens:
                if item.startswith('perfil='):
                    if style is not None:raise ProfileError(f'Linha {n}: perfil duplicado')
                    style=item[len('perfil='):]
                elif voice is None:voice=item
                else:raise ProfileError(f'Linha {n}: @personagem possui tokens excedentes')
            if style and style not in profiles:raise ProfileError(f'Linha {n}: perfil inexistente: {style}')
            voice=voice or profiles.get(style,{}).get('voz')
            if not voice or not VOICE.fullmatch(voice):raise ProfileError(f'Linha {n}: personagem sem voz válida')
            chars[name]={'voice':voice,'profile':style}
            out.append(f'@personagem {name} {voice}');continue
        if line.startswith('@fala '):line=_tagline(line,n)
        if not line or line.startswith('@') or line.startswith('#'):
            out.append(raw if not line.startswith('@fala ') else line);continue
        parts=[p.strip() for p in line.split('|',4)]
        if len(parts)==5 and parts[1].lower()!='!efeito':
            at,role,style,opts,text=parts;role=role.lower();style=style.lower()
            if style in profiles or (role in chars and chars[role].get('profile')):
                chosen=profiles.get(style) or profiles[chars[role]['profile']]
                local=_options(opts,n)
                params={k:v for k,v in chosen.items() if k in KEYS or k=='voz'}
                params.update(local)
                # Speaker voice is explicit: it is never silently changed by a style,
                # unless a voice override was specified on the line itself.
                if 'voz' in chosen and 'voz' not in local:params.pop('voz',None)
                known='neutro'
                ordered=','.join(f'{k}={v}' for k,v in params.items())
                out.append(f'{at} | {role} | {known} | {ordered} | {text}')
                metadata[n]={'emotion':style,'processor':chosen.get('processador'),
                             'profile':style if style in profiles else chars[role]['profile']}
                continue
        out.append(line if line.startswith('@fala ') else raw)
    return Compiled('\n'.join(out),metadata,profiles,processors)


def process_take(path, proc_name, processors, media_dir, cache_dir, ffmpeg=None):
    """Per-take FFmpeg with an allowlisted filter graph; subprocess without shell.
    Returns a WAV in media_dir, preserving the original voice file.
    """
    if not proc_name:return Path(path)
    if proc_name not in processors:raise ProfileError('Processador inexistente: '+str(proc_name))
    filters=_filters(processors[proc_name]['ffmpeg'])
    if not filters:return Path(path)
    path=Path(path);media_dir=Path(media_dir);cache_dir=Path(cache_dir)
    if path.is_symlink() or not path.is_file() or path.parent.resolve()!=media_dir.resolve():
        raise ProfileError('Áudio de origem fora da pasta de mídias')
    ffmpeg=ffmpeg or shutil.which('ffmpeg')
    if not ffmpeg:raise ProfileError('ffmpeg não encontrado')
    key=hashlib.sha256(json.dumps({'file':path.name,'size':path.stat().st_size,
          'mtime':path.stat().st_mtime_ns,'filters':filters},sort_keys=True).encode()).hexdigest()[:32]
    dest=media_dir/('rd-profile-'+key+'.wav')
    if dest.is_file() and not dest.is_symlink():
        try:
            with wave.open(str(dest),'rb') as f:
                if f.getnframes()>0:return dest
        except wave.Error:pass
        raise ProfileError('Cache de processamento inválido')
    tmp=cache_dir/('.rd-profile-'+uuid.uuid4().hex+'.wav')
    cmd=[str(ffmpeg),'-nostdin','-hide_banner','-loglevel','error','-y',
         '-i',str(path),'-vn','-af',','.join(filters),'-t','240',
         '-ac','1','-ar','22050','-c:a','pcm_s16le',str(tmp)]
    try:
        p=subprocess.run(cmd,capture_output=True,timeout=100,check=False)
        if p.returncode:raise ProfileError('ffmpeg: '+p.stderr.decode('utf-8','replace')[-300:])
        with wave.open(str(tmp),'rb') as f:
            if f.getnframes()<1 or f.getnchannels()!=1 or f.getframerate()!=22050:
                raise ProfileError('FFmpeg retornou WAV inválido')
        if dest.is_symlink() or dest.exists():raise ProfileError('Destino de processamento existente')
        os.replace(tmp,dest);return dest
    except subprocess.TimeoutExpired as exc:raise ProfileError('Processamento externo excedeu 100 segundos') from exc
    finally:tmp.unlink(missing_ok=True)
