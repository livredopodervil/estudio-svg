"""RD Studio M2.4: deterministic, local multi-character narration score.

No shell, network access, espeak output, model installation, or project writes.
Piper and Edge synthesize supported utterances. Browser voice export is explicitly unsupported.
"""
from __future__ import annotations

from array import array
import hashlib
import asyncio
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import threading
import uuid
import wave

from studio_piper_local import synthesize, PiperError

class ScoreError(ValueError):
    pass

ROLE = re.compile(r'^@personagem\s+([a-z][a-z0-9_-]{0,31})\s+(.+?)\s*$', re.I)
SCENE = re.compile(r'^@cena\s+(\d{1,3})\s*$', re.I)
TIME = re.compile(r'^(?:(\d{1,2}):)?(\d{1,3})(?:\.(\d{1,3}))?$')
EMOTIONS = {
    'neutro':(1.00,1.00),
    'calmo':(1.06,.93),
    'alegre':(.98,1.04),
    'triste':(1.10,.90),
    'urgente':(.91,1.10),
    'solene':(1.08,1.00),
}
_LOCK=threading.Lock()
MAX_SCRIPT=30000


def parse_provider_voice(value):
    """Seleção explícita em catálogo dos motores presentes, com legados compatíveis."""
    value=str(value).strip()
    if value in ('faber','edresson'):return value
    # Vozes do navegador são selecionáveis para prévia.
    # Não aparecem no catálogo instalado do servidor e não geram áudio exportável.
    if value.startswith('browser:'):
        if not re.fullmatch(r'browser:[A-Za-z0-9_.:-]{1,128}', value):
            raise ScoreError('Identificador de voz do navegador inválido')
        return value
    if not 1<=len(value)<=240:raise ScoreError('Identificador de voz inválido')
    from rd_voices.available_voices import require_voice
    try:require_voice(value)
    except ValueError as exc:raise ScoreError(str(exc)) from exc
    return value

def edge_cue_params(cue):
    """Emoção = intenção acústica aproximada, não estilo neural nativo."""
    from rd_voices.core import EXPRESSIVE_PRESETS, edge_parameters
    tone=cue.get('pitch_hz',0);volume=cue.get('volume_pct',0)
    rate=round((1.0/cue['tempo']-1.0)*100)
    return edge_parameters({'prosody':{'rate_pct':rate,'pitch_hz':tone,'volume_pct':volume},
                            'intention':cue['emotion']})

from rd_voices.score_bridge import synthesize_edge_score as render_edge_score

def seconds(value):
    m=TIME.fullmatch(value.strip())
    if not m:raise ScoreError('Marcação temporal inválida: '+str(value))
    minute=int(m[1] or 0);sec=int(m[2]);ms=int((m[3] or '0').ljust(3,'0'))
    if m[1] is not None and sec>=60:raise ScoreError('Segundos devem ficar abaixo de 60 em M:SS')
    t=minute*60+sec+ms/1000
    if t>600:raise ScoreError('Tempo ultrapassa 600 s por cena')
    return t


def options(raw,line):
    result={}
    if not raw.strip():return result
    for part in raw.split(','):
        if '=' not in part:raise ScoreError(f'Linha {line}: parâmetro inválido: {part}')
        k,v=map(str.strip,part.split('=',1))
        if k not in ('ritmo','ganho','pausa','voz','tom','volume'):raise ScoreError(f'Linha {line}: parâmetro desconhecido: {k}')
        if k in result:raise ScoreError(f'Linha {line}: parâmetro repetido: {k}')
        if k=='voz':
            result[k]=parse_provider_voice(v);continue
        try:n=float(v)
        except ValueError:raise ScoreError(f'Linha {line}: número inválido: {v}') from None
        lo,hi={'ritmo':(.70,1.30),'ganho':(0,2),'pausa':(0,1),'tom':(-100,100),'volume':(-100,100)}[k]
        if not math.isfinite(n) or not lo<=n<=hi:raise ScoreError(f'Linha {line}: {k} fora de {lo}–{hi}')
        result[k]=n
    return result


def _parse_score_legacy(source, scene_count=1):
    if not isinstance(source,str) or len(source)>MAX_SCRIPT or '\x00' in source:
        raise ScoreError('Roteiro de áudio inválido ou acima de 30.000 caracteres')
    if not isinstance(scene_count,int) or not 1<=scene_count<=150:
        raise ScoreError('Número de cenas inválido')
    voices={'narrador':'faber'};current_scene=1;takes=[];effects=[]
    for number,raw in enumerate(source.splitlines(),1):
        line=raw.strip()
        if not line or line.startswith('#'):continue
        r=ROLE.fullmatch(line)
        if r:
            voices[r[1].lower()]=parse_provider_voice(r[2]);continue
        r=SCENE.fullmatch(line)
        if r:
            current_scene=int(r[1]);
            if not 1<=current_scene<=scene_count:raise ScoreError(f'Linha {number}: cena {current_scene} inexistente')
            continue
        if line.startswith('@'):raise ScoreError(f'Linha {number}: diretiva desconhecida')
        parts=[x.strip() for x in line.split('|',4)]
        if len(parts)<4:raise ScoreError(f'Linha {number}: use tempo | personagem | emoção | parâmetros | texto')
        at=seconds(parts[0]);role=parts[1].lower()
        if role=='!efeito':
            if len(parts)!=4:raise ScoreError(f'Linha {number}: efeito exige tempo | !efeito | arquivo.wav | ganho=...')
            filename=parts[2]
            if not re.fullmatch(r'[A-Za-z0-9_.-]{1,128}\.(?:wav|mp3|ogg|m4a)',filename,re.I) or '..' in filename:
                raise ScoreError(f'Linha {number}: nome de efeito inseguro')
            opt=options(parts[3],number)
            if set(opt)-{'ganho'}:raise ScoreError(f'Linha {number}: efeito suporta apenas ganho')
            effects.append({'scene':current_scene,'at':at,'file':filename,'gain':opt.get('ganho',.7),'line':number})
            continue
        if len(parts)!=5:raise ScoreError(f'Linha {number}: fala exige cinco campos separados por |')
        if role not in voices:raise ScoreError(f'Linha {number}: personagem {role!r} não declarado')
        emotion=parts[2].lower()
        if emotion not in EMOTIONS:raise ScoreError(f'Linha {number}: emoção desconhecida {emotion!r}')
        opt=options(parts[3],number)
        text=parts[4].strip()
        if not 1<=len(text)<=3000:raise ScoreError(f'Linha {number}: fala precisa de 1 a 3000 caracteres')
        factor,volume=EMOTIONS[emotion]
        tempo=round(max(.70,min(1.30,opt.get('ritmo',.94)*factor)),4)
        gain=round(opt.get('ganho',1.0)*volume,4)
        voice=opt.get('voz',voices[role])
        takes.append({'scene':current_scene,'at':at,'role':role,'voice':voice,
                      'emotion':emotion,'tempo':tempo,'gain':gain,
                      'pause':opt.get('pausa',.30),'pitch_hz':round(opt.get('tom',0)),
                      'volume_pct':round(opt.get('volume',0)),
                      'text':text,'line':number})
    if not takes and not effects:raise ScoreError('Roteiro sem falas ou efeitos')
    if len(takes)>80 or len(effects)>40:raise ScoreError('Limite: 80 falas e 40 efeitos por roteiro')
    if len({x['scene'] for x in takes+effects})>15:raise ScoreError('Gere no máximo 15 cenas por lote')
    if sum(len(x['text']) for x in takes)>16000:raise ScoreError('Máximo de 16.000 caracteres por lote')
    return {'characters':voices,'takes':takes,'effects':effects,'warnings':
            ['Emoções são aproximações acústicas; Edge TTS não oferece estilos emocionais nativos por este cliente.'] if any(t['emotion']!='neutro' for t in takes) else []}


def parse_score(source, scene_count=1):
    """Compatível com RD-Audio 1 e novos perfis declarativos U3."""
    from rd_audio_profiles import compile_score
    try:
        compiled = compile_score(source)
        parsed = _parse_score_legacy(compiled.source, scene_count)
    except ValueError as exc:
        raise ScoreError(str(exc)) from exc
    for cue in parsed['takes']:
        extra = compiled.lines.get(cue['line'])
        if extra:
            cue.update(extra)
    parsed['processors'] = compiled.processors
    if compiled.lines:parsed['warnings'].append('Perfis acústicos personalizados não significam emoção neural nativa.')
    return parsed


def status_kokoro(root=None):
    from rd_voices.available_voices import installed_catalog
    catalog=installed_catalog(kokoro_root=(root if root is not None else None))
    kok=[x for x in catalog['voices'] if x['provider']=='kokoro']
    pt=[x for x in kok if x['locale']=='pt-BR' and x['available']]
    return {'installed':bool(kok),'models':int(bool(kok)),'lexicons':int(bool(pt)),
            'ready_ptbr':bool(pt),'validated_audio':False,
            'detail':('Kokoro configurado; confirmar pronúncia por audição' if pt else 'Kokoro ou léxico PT-BR ausente')}

def pcm_bytes(path, ffmpeg):
    proc=subprocess.run([ffmpeg,'-nostdin','-v','error','-i',str(path),'-vn','-ac','1','-ar','22050',
                         '-f','s16le','-acodec','pcm_s16le','-'],capture_output=True,timeout=75,check=False)
    if proc.returncode or not proc.stdout:raise ScoreError('Falha ao decodificar áudio: '+proc.stderr.decode('utf-8','replace')[-250:])
    if len(proc.stdout)%2:raise ScoreError('PCM de comprimento inválido')
    return proc.stdout


def generate(source, scene_durations, media_dir, cache_dir, *, synth=synthesize, edge_synth=render_edge_score, kokoro_synth=None, espeak_synth=None, ffmpeg=None, only_line=None):
    if not isinstance(scene_durations,list) or not 1<=len(scene_durations)<=150:
        raise ScoreError('Durações das cenas inválidas')
    if not all(isinstance(x,(int,float)) and not isinstance(x,bool) and math.isfinite(x) and .5<=x<=600 for x in scene_durations):
        raise ScoreError('Duração de cena inválida')
    parsed=parse_score(source,len(scene_durations));media_dir=Path(media_dir);cache_dir=Path(cache_dir)
    if only_line is not None:
        if isinstance(only_line,bool) or not isinstance(only_line,int) or only_line<0:
            raise ScoreError('Número de linha inválido para amostra')
        matches=parsed['takes'] if only_line==0 else [x for x in parsed['takes'] if x['line']==only_line]
        if not matches:raise ScoreError('Fala da amostra não encontrada')
        parsed['takes']=[{**matches[0], 'at':0.0}]
        parsed['effects']=[]
        scene_durations=[.5 for _ in scene_durations]
    if not media_dir.is_dir() or not cache_dir.is_dir():raise ScoreError('Mídia/cache não disponíveis')
    ffmpeg=ffmpeg or shutil.which('ffmpeg')
    if not ffmpeg:raise ScoreError('ffmpeg indisponível')
    if not _LOCK.acquire(blocking=False):raise ScoreError('Outra geração de roteiro está em execução')
    try:
        scenes=sorted({x['scene'] for x in parsed['takes']+parsed['effects']});responses=[]
        for scene in scenes:
            cues=[x for x in parsed['takes'] if x['scene']==scene];effects=[x for x in parsed['effects'] if x['scene']==scene]
            segments=[]
            for cue in cues:
                provider=cue['voice'].split(':',1)[0] if ':' in cue['voice'] else 'piper'
                if provider=='edge':
                    item=edge_synth(cue['text'],cue['voice'],edge_cue_params(cue),media_dir,cache_dir)
                elif provider=='piper':
                    vid=cue['voice'].split(':',1)[-1]
                    item=synth(cue['text'],vid,cue['tempo'],cue['pause'],media_dir,cache_dir)
                elif provider=='kokoro':
                    if kokoro_synth is None:
                        from rd_voices.kokoro_engine import synthesize as kokoro_synth
                    item=kokoro_synth(cue['text'],cue['voice'],1.0/cue['tempo'],cue['pause'],media_dir,cache_dir)
                elif provider=='espeak':
                    if espeak_synth is None:
                        from rd_voices.espeak_engine import synthesize as espeak_synth
                    item=espeak_synth(cue['text'],cue['voice'],cue['tempo'],cue['pause'],media_dir,cache_dir)
                else:
                    raise ScoreError('Voz '+provider+' não exporta áudio neste motor; selecione um motor que exporte arquivos')
                p=media_dir/item['filename']
                if p.is_symlink() or not p.is_file():raise ScoreError('Áudio de locução inválido')
                from rd_audio_profiles import process_take
                p=process_take(p,cue.get('processor'),parsed['processors'],media_dir,cache_dir,ffmpeg)
                segments.append((cue['at'],cue['gain'],p))
            for effect in effects:
                p=media_dir/effect['file']
                if p.is_symlink() or not p.is_file() or p.stat().st_size>32_000_000:
                    raise ScoreError(f'Linha {effect["line"]}: efeito não encontrado ou inválido: {effect["file"]}')
                segments.append((effect['at'],effect['gain'],p))
            signature={'format':'rd-score-1','script':source,'scene':scene,
                       'files':[(p.name,p.stat().st_size,p.stat().st_mtime_ns,t,g) for t,g,p in segments]}
            digest=hashlib.sha256(json.dumps(signature,sort_keys=True,ensure_ascii=False).encode()).hexdigest()[:24]
            name='rd-score-'+digest+'.wav';target=media_dir/name
            if target.exists() and not target.is_symlink():
                with wave.open(str(target),'rb') as w:
                    if w.getnchannels()!=1 or w.getframerate()!=22050 or w.getsampwidth()!=2:raise ScoreError('Cache de roteiro inválido')
                    duration=w.getnframes()/22050
                responses.append({'scene':scene,'filename':name,'seconds':duration,'cached':True,'takes':len(cues),'effects':len(effects),'transcript':' '.join(c['text'] for c in cues)})
                continue
            decoded=[];length=int(math.ceil(scene_durations[scene-1]*22050))
            for at,gain,p in segments:
                raw=pcm_bytes(p,ffmpeg);frames=len(raw)//2
                end=int(round(at*22050))+frames
                if end>600*22050:raise ScoreError(f'Cena {scene}: roteiro ultrapassa 600 segundos')
                length=max(length,end)
                decoded.append((int(round(at*22050)),gain,raw))
            mix=array('i',[0])*length
            for start,gain,raw in decoded:
                samples=array('h');samples.frombytes(raw)
                if os.sys.byteorder!='little':samples.byteswap()
                for k,sample in enumerate(samples):mix[start+k]+=round(sample*gain)
            peak=max((abs(n) for n in mix),default=0);normalize=min(1.,32766/max(1,peak))
            pcm=array('h',(max(-32768,min(32767,round(v*normalize))) for v in mix))
            if os.sys.byteorder!='little':pcm.byteswap()
            tmp=cache_dir/('.rd-score-'+uuid.uuid4().hex+'.wav')
            try:
                with wave.open(str(tmp),'wb') as out:
                    out.setnchannels(1);out.setsampwidth(2);out.setframerate(22050);out.writeframes(pcm.tobytes())
                if target.is_symlink() or target.exists():raise ScoreError('Destino já existe em estado incompatível')
                os.replace(tmp,target)
            finally:tmp.unlink(missing_ok=True)
            responses.append({'scene':scene,'filename':name,'seconds':length/22050,'cached':False,
                              'takes':len(cues),'effects':len(effects),'peak_reduced':normalize<1,'transcript':' '.join(c['text'] for c in cues)})
        providers=sorted({'edge' if cue['voice'].startswith('edge:') else 'piper' for cue in parsed['takes']})
        return {'scenes':responses,'warnings':parsed['warnings'],'count':len(responses),'providers':providers}
    except (OSError,subprocess.SubprocessError, wave.Error,PiperError,RuntimeError) as e:
        raise ScoreError(str(e)) from e
    finally:_LOCK.release()
