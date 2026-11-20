"""Neural offline Portuguese narration via installed Termux Piper wrapper.

Never changes the wrapper, ONNX files, glibc or the existing mixer.
Output is a WAV filename in the existing Studio MEDIA directory, suitable for
cenas[].audio.voice_file.
"""
from __future__ import annotations
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import threading
import uuid
import wave

VOICES={"faber":("pt_BR-faber-medium.onnx",22050),
        "edresson":("pt_BR-edresson-low.onnx",16000)}
_BUSY=threading.Lock()

class PiperError(ValueError):
    pass

def _wav_info(path:Path, rate:int):
    try:
        if path.is_symlink() or not path.is_file() or not 44<path.stat().st_size<=36_000_000:
            raise PiperError('WAV inexistente, inseguro ou muito grande')
        with wave.open(str(path),'rb') as wav:
            if wav.getnchannels()!=1 or wav.getsampwidth()!=2 or wav.getframerate()!=rate or wav.getcomptype()!='NONE':
                raise PiperError('Formato WAV inesperado do Piper')
            seconds=wav.getnframes()/rate
            if not .03<seconds<=240:raise PiperError('Duração de voz inválida ou acima de 240 segundos')
            return seconds
    except (wave.Error,EOFError, OSError) as e:
        raise PiperError('WAV inválido: '+str(e)) from e

def synthesize(text,voice,length_scale,sentence_silence,media_dir,cache_dir,*,model_root=None,piper_binary=None):
    if not isinstance(text,str) or not (1<=len(text.strip())<=3000) or '\x00' in text:
        raise PiperError('Texto da narração deve ter 1 a 3000 caracteres')
    from rd_voices.available_voices import piper_models
    if not isinstance(voice,str) or not voice or '/' in voice or '..' in voice:
        raise PiperError('Identificador Piper inválido')
    if isinstance(length_scale,bool) or not isinstance(length_scale,(int,float)) or not math.isfinite(length_scale) or not .70<=length_scale<=1.30:
        raise PiperError('Velocidade deve estar entre 0,70 e 1,30')
    if isinstance(sentence_silence,bool) or not isinstance(sentence_silence,(int,float)) or not math.isfinite(sentence_silence) or not 0<=sentence_silence<=1:
        raise PiperError('Pausa deve estar entre 0 e 1 segundo')
    model_dir=Path(model_root) if model_root is not None else Path.home()/'piper_tts'
    choices=piper_models(model_dir)
    spec=choices.get(voice)
    if spec is None:raise PiperError('Modelo Piper não instalado: '+voice)
    model=spec['model'];rate=spec['rate']
    config=Path(str(model)+'.json')
    if model.is_symlink() or config.is_symlink():raise PiperError('Symlink de modelo não permitido')
    # Models are a fixed allowlist; never use user-provided paths or shell commands.
    exe=piper_binary or shutil.which('piper')
    if not exe or not Path(exe).is_file():raise PiperError('Wrapper piper ausente no PATH')
    media_dir=Path(media_dir);cache_dir=Path(cache_dir)
    if not media_dir.is_dir() or not cache_dir.is_dir():raise PiperError('Diretórios de mídia/cache indisponíveis')
    signature={"format":1,"text":text.strip(),"voice":voice,
      "scale":float(length_scale),"silence":float(sentence_silence),
      "model":[model.name,model.stat().st_size,model.stat().st_mtime_ns],
      "config":[config.stat().st_size,config.stat().st_mtime_ns]}
    digest=hashlib.sha256(json.dumps(signature,sort_keys=True,ensure_ascii=False).encode()).hexdigest()[:24]
    filename='rd-piper-'+digest+'.wav'
    target=media_dir/filename
    if target.is_file() and not target.is_symlink():
        return {"filename":filename,"seconds":_wav_info(target,rate),"cached":True,"voice":voice}
    if not _BUSY.acquire(blocking=False):raise PiperError('Outra narração Piper está em andamento')
    temp=cache_dir/('.rd-piper-'+uuid.uuid4().hex+'.wav')
    try:
        if target.is_file() and not target.is_symlink():
            return {"filename":filename,"seconds":_wav_info(target,rate),"cached":True,"voice":voice}
        try:
            result=subprocess.run([str(exe),'--model',str(model),'--length_scale',str(length_scale),
                '--sentence_silence',str(sentence_silence),'--output_file',str(temp)],
                input=text.strip().encode('utf-8'),stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=240,check=False)
        except subprocess.TimeoutExpired as e:
            raise PiperError('Piper excedeu 240 segundos') from e
        except OSError as e:
            raise PiperError('Falha ao executar wrapper Piper: '+str(e)) from e
        if result.returncode!=0:raise PiperError('Piper falhou: '+result.stderr.decode('utf-8','replace')[-300:])
        seconds=_wav_info(temp,rate)
        if target.exists() or target.is_symlink():raise PiperError('Destino de áudio já existe em estado incompatível')
        os.replace(temp,target)
        return {"filename":filename,"seconds":seconds,"cached":False,"voice":voice}
    finally:
        temp.unlink(missing_ok=True)
        _BUSY.release()
