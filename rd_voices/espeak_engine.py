"""Optional legacy eSpeak voice, never used as a fallback. Requires explicit selection."""
from __future__ import annotations
import hashlib,json,os,subprocess,tempfile,shutil,wave
from pathlib import Path
from .available_voices import require_voice

def synthesize(text,voice,tempo,pause,media_dir,cache_dir):
    item=require_voice(voice)
    if item['provider']!='espeak':raise ValueError('Voz não é eSpeak')
    if not isinstance(text,str) or not 1<=len(text.strip())<=3000 or '\x00' in text:raise ValueError('Texto inválido')
    if not .70<=tempo<=1.30:raise ValueError('Ritmo inválido')
    exe=shutil.which('espeak-ng')
    if not exe:raise ValueError('eSpeak NG indisponível')
    media=Path(media_dir);cache=Path(cache_dir)
    if not media.is_dir() or not cache.is_dir():raise ValueError('Diretórios indisponíveis')
    signature=json.dumps([text,voice,tempo],ensure_ascii=False)
    digest=hashlib.sha256(signature.encode()).hexdigest()[:24]
    name='rd-espeak-'+digest+'.wav';target=media/name
    if target.is_file() and not target.is_symlink():
        with wave.open(str(target),'rb') as w:return {'filename':name,'seconds':w.getnframes()/w.getframerate(),'cached':True}
    fd,path=tempfile.mkstemp(prefix='.rd-espeak-',suffix='.wav',dir=cache);os.close(fd)
    tmp=Path(path)
    try:
        proc=subprocess.run([exe,'-v',item['voice_id'],'-s',str(round(170/tempo)),'-w',str(tmp),'--stdin'],
                            input=text,encoding='utf-8',capture_output=True,timeout=100,check=False)
        if proc.returncode:raise ValueError('eSpeak: '+proc.stderr[-200:])
        with wave.open(str(tmp),'rb') as w:
            rate=w.getframerate();length=w.getnframes();
            if rate<=0 or length<=0:raise ValueError('eSpeak não gerou áudio')
        if target.exists() or target.is_symlink():raise ValueError('Arquivo de mídia já existe')
        os.replace(tmp,target)
        return {'filename':name,'seconds':length/rate,'cached':False}
    finally:tmp.unlink(missing_ok=True)
