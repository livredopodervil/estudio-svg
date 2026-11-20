"""Isolated Kokoro worker. Inputs are validated against installed model/catalog.
Returns WAV in existing MEDIA. It never downloads models or edits Termux runtime.
"""
from __future__ import annotations
import hashlib,json,os,sys,subprocess,tempfile,wave
from pathlib import Path
from .available_voices import require_voice,kokoro_base,kokoro_lexicon

class KokoroError(ValueError):pass

def synthesize(text,voice,speed,pause,media_dir,cache_dir,*,base=None,worker=None):
    if not isinstance(text,str) or not 1<=len(text.strip())<=3000 or '\x00' in text:raise KokoroError('Texto inválido')
    if not isinstance(speed,(float,int)) or not .7<=speed<=1.3:raise KokoroError('Velocidade fora do intervalo')
    catalog_voice=require_voice(voice)
    if catalog_voice['provider']!='kokoro':raise KokoroError('Voz não é Kokoro')
    root=kokoro_base(base)
    if root is None:raise KokoroError('Modelo Kokoro ausente')
    lex=kokoro_lexicon(root,catalog_voice['locale'])
    if not lex:raise KokoroError('Léxico Kokoro ausente para '+catalog_voice['locale'])
    m=Path(media_dir);c=Path(cache_dir)
    if not m.is_dir() or not c.is_dir():raise KokoroError('Diretórios de mídia e cache indisponíveis')
    sig={'text':text,'voice':voice,'sid':catalog_voice['sid'],'speed':speed,'pause':pause,
         'model':[ (root/'model.onnx').stat().st_size,(root/'model.onnx').stat().st_mtime_ns ]}
    digest=hashlib.sha256(json.dumps(sig,ensure_ascii=False,sort_keys=True).encode()).hexdigest()[:24]
    name='rd-kokoro-'+digest+'.wav';dest=m/name
    if dest.exists() and not dest.is_symlink() and dest.stat().st_size>44:
        with wave.open(str(dest),'rb') as r:
            return {'filename':name,'seconds':r.getnframes()/r.getframerate(),'cached':True,'voice':voice}
    with tempfile.NamedTemporaryFile(suffix='.wav',dir=c,delete=False) as f:tmp=Path(f.name)
    try:
        cmd=[sys.executable,'-m','rd_voices.kokoro_engine','--worker',str(root),str(lex),str(catalog_voice['sid']),str(speed),str(tmp)]
        try:
            p=subprocess.run(cmd,input=text,encoding='utf-8',capture_output=True,timeout=240,check=False,cwd=str(Path(__file__).resolve().parents[1]))
        except subprocess.TimeoutExpired as exc:raise KokoroError('Kokoro excedeu 240 s') from exc
        if p.returncode:raise KokoroError('Kokoro: '+p.stderr[-350:])
        with wave.open(str(tmp),'rb') as r:
            rate=r.getframerate();frames=r.getnframes()
            if rate<=0 or frames<=0 or r.getnchannels()!=1 or r.getsampwidth()!=2:
                raise KokoroError('WAV inválido retornado pelo Kokoro')
        if dest.exists() or dest.is_symlink():raise KokoroError('Conflito de mídia no destino')
        os.replace(tmp,dest)
        return {'filename':name,'seconds':frames/rate,'cached':False,'voice':voice}
    finally:tmp.unlink(missing_ok=True)

def _worker(args):
    from pathlib import Path
    import numpy as np
    import sherpa_onnx
    import wave
    base,lex,sid,speed,out=args
    text=sys.stdin.read(3001)
    config=sherpa_onnx.OfflineTtsConfig(model=sherpa_onnx.OfflineTtsModelConfig(
       kokoro=sherpa_onnx.OfflineTtsKokoroModelConfig(model=str(Path(base)/'model.onnx'),
       voices=str(Path(base)/'voices.bin'),tokens=str(Path(base)/'tokens.txt'),
       data_dir=str(Path(base)/'espeak-ng-data'),lexicon=lex,lang='pt-br' if 'pt' in Path(lex).name.lower() else ''),
       num_threads=2))
    tts=sherpa_onnx.OfflineTts(config)
    audio=tts.generate(text=text,sid=int(sid),speed=float(speed))
    samples=np.asarray(audio.samples,dtype=np.float32)
    rate=int(audio.sample_rate)
    if rate<=0 or not samples.size or not np.isfinite(samples).all():raise RuntimeError('Kokoro não gerou áudio válido')
    pcm=(np.clip(samples,-1,1)*32767).astype('<i2')
    with wave.open(out,'wb') as wav:
        wav.setnchannels(1);wav.setsampwidth(2);wav.setframerate(rate);wav.writeframes(pcm.tobytes())

if __name__=='__main__' and len(sys.argv)==7 and sys.argv[1]=='--worker':
    _worker(sys.argv[2:])
