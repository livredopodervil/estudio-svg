"""Estúdio SVG V2.4: render econômico e mixagem sem vídeo."""
from __future__ import annotations
import hashlib, io, json, math, os, shutil, subprocess, sys, threading, time, wave, zipfile
from functools import lru_cache
from pathlib import Path
from schema import VERSION
from graphics import visualize
from scene_video import overlay_clip

ROOT=Path(__file__).resolve().parent
PROJECTS=ROOT/'projetos';MEDIA=ROOT/'midia';CACHE=ROOT/'cache';OUTPUT=ROOT/'render'
for d in (PROJECTS,MEDIA,CACHE,OUTPUT,CACHE/'voices',CACHE/'visual',CACHE/'audio',CACHE/'poster'):d.mkdir(parents=True,exist_ok=True)

class StudioError(Exception):pass

def digest(s):return hashlib.sha256(json.dumps(s,sort_keys=True,ensure_ascii=False,default=str,separators=(',',':')).encode()).hexdigest()[:22]
def sha_file(f):
    h=hashlib.sha256()
    with open(f,'rb') as inp:
        for chunk in iter(lambda:inp.read(512*1024),b''):h.update(chunk)
    return h.hexdigest()
def media_file(fn):
    if not fn:return None
    from schema import asset
    fn=asset(fn)
    f=MEDIA/fn
    if not f.is_file():raise StudioError('Mídia não encontrada: '+fn+'; importe no editor')
    return f

def asset_sha(fn):
    if not fn:return ''
    try:return sha_file(media_file(fn))
    except (OSError,StudioError):return 'AUSENTE:'+fn

def run(args,timeout=1200,input_bytes=None):
    try:p=subprocess.run([str(x) for x in args],stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=timeout,input=input_bytes)
    except FileNotFoundError as e:raise StudioError('Programa não instalado: '+str(args[0])) from e
    except subprocess.TimeoutExpired as e:raise StudioError('Tempo limite excedido: '+str(args[0])) from e
    if p.returncode:raise StudioError(f'{args[0]}: '+(p.stderr or p.stdout).decode(errors='replace')[-1800:])
    return p

def duration(path):
    try:
        return float(run(['ffprobe','-v','error','-show_entries','format=duration','-of','default=noprint_wrappers=1:nokey=1',path],25).stdout.strip())
    except Exception:return 0

def voice_extension(pr):
    return '.mp3' if pr.get('motor_voz','edge-tts')=='edge-tts' else '.wav'

def piper_model(pr):
    from schema import asset
    fn=asset(pr.get('modelo_piper',''))
    if not fn or not fn.lower().endswith('.onnx'):
        raise StudioError('Piper: informe um modelo .onnx em modelos/ no painel Projeto')
    path=ROOT/'modelos'/fn
    if not path.is_file():raise StudioError('Modelo Piper ausente em modelos/'+fn)
    if not path.with_suffix(path.suffix+'.json').is_file():
        raise StudioError('Piper: falta o arquivo de configuração modelos/'+fn+'.json')
    return path

@lru_cache(maxsize=12)
def model_digest(path,size,mtime_ns):
    return sha_file(path)

def tts_key(scene,pr):
    au=scene['audio'];motor=pr.get('motor_voz','edge-tts')
    if motor=='edge-tts':
        # Mesma chave da V2.2: permite aproveitar as vozes anteriormente sintetizadas.
        return digest(['tts',au['voice_text'],pr['voz'],pr['velocidade_voz']])
    if motor=='espeak-ng':return digest(['tts23-espeak',au['voice_text'],pr['voz_espeak'],pr['velocidade_espeak']])
    if motor=='piper':
        model=piper_model(pr);config=model.with_suffix(model.suffix+'.json')
        return digest(['tts23-piper',au['voice_text'],model_digest(str(model),model.stat().st_size,model.stat().st_mtime_ns),
                       model_digest(str(config),config.stat().st_size,config.stat().st_mtime_ns)])
    raise StudioError('Motor de voz desconhecido')

def voice_source(scene,pr,required=True):
    au=scene['audio']
    if not au['voice_enabled']:return None
    if au['voice_file']:
        if not required and not (MEDIA/au['voice_file']).is_file():return None
        return media_file(au['voice_file'])
    if not au['voice_text'].strip():return None
    try:f=CACHE/'voices'/(tts_key(scene,pr)+voice_extension(pr))
    except StudioError:
        if required:raise
        return None
    if f.is_file() and f.stat().st_size>500 and duration(f)>.2:return f
    if required:raise StudioError(f'Falta a locução da cena "{scene["titulo"]}". Execute primeiro Áudio em lote.')
    return None

def synthesize(text,pr,tmp):
    engine=pr.get('motor_voz','edge-tts')
    if engine=='edge-tts':
        if not shutil.which('edge-tts'):raise StudioError('Instale edge-tts: python -m pip install edge-tts')
        run(['edge-tts','--voice',pr['voz'],'--rate',pr['velocidade_voz'],
            '--text',text,'--write-media',tmp],timeout=210)
    elif engine=='espeak-ng':
        exe=shutil.which('espeak-ng') or shutil.which('espeak')
        if not exe:raise StudioError('Instale voz offline: pkg install espeak')
        run([exe,'-b','1','-v',pr['voz_espeak'],'-s',str(pr['velocidade_espeak']),
             '-w',tmp,'--stdin'],input_bytes=text.encode('utf8'),timeout=150)
    elif engine=='piper':
        if not shutil.which('piper'):raise StudioError('Piper não instalado. Use uma instalação local do executável piper e um modelo .onnx.')
        model=piper_model(pr)
        run(['piper','--model',model,'--output_file',tmp],input_bytes=(text.strip()+'\n').encode('utf8'),timeout=300)
    else:raise StudioError('Motor desconhecido: '+engine)

def batch_audio(pr,progress=lambda *_:None):
    voices=[];counts=len(pr['cenas'])
    for i,scene in enumerate(pr['cenas']):
        au=scene['audio']
        if au['voice_enabled'] and au['voice_file']:
            f=media_file(au['voice_file'])
            if duration(f)<=0:raise StudioError(f'Áudio manual inválido na cena {i+1}')
            voices.append((i,f))
        elif au['voice_enabled'] and au['voice_text'].strip():
            f=CACHE/'voices'/(tts_key(scene,pr)+voice_extension(pr))
            if not f.is_file() or f.stat().st_size<500 or duration(f)<.2:
                tmp=CACHE/'voices'/(f.stem+'.part'+f.suffix)
                progress(i/counts,f'Gerando voz {i+1}/{counts} via {pr.get("motor_voz","edge-tts")}')
                try:
                    synthesize(au['voice_text'],pr,tmp)
                    if duration(tmp)<.2:raise StudioError(f'Locução {i+1} vazia')
                    tmp.replace(f)
                finally:tmp.unlink(missing_ok=True)
            voices.append((i,f))
        progress((i+1)/counts,f'Voz {i+1}/{counts}: cache pronto')
    zip_path=OUTPUT/'vozes_em_lote.zip';tmp=zip_path.with_suffix('.partial')
    with zipfile.ZipFile(tmp,'w',zipfile.ZIP_DEFLATED) as z:
        for i,f in voices:z.write(f,f'voz_{i+1:03d}{f.suffix}')
    tmp.replace(zip_path)
    return zip_path

def scene_length(scene,pr,voice=True):
    requested=scene['duracao'];voicef=voice_source(scene,pr,required=voice) if voice else None
    if voicef:
        need=duration(voicef)+scene['audio']['voice_delay']+.26
        if need>requested and pr['encaixe_voz']=='estender':requested=need
        elif need>requested:raise StudioError('Narração excede a duração da cena: '+scene['titulo'])
    fps=pr['video']['draw_fps']
    return max(1,math.ceil(requested*fps))/fps

def visual_key(scene,pr,seconds):
    c={k:v for k,v in scene.items() if k not in ('audio','fala','id')}
    file=c['imagem']['arquivo']
    clip=c.get('video_clipe',{}).get('arquivo','')
    return digest(['visual-4','2.7.3',c,pr['video'],seconds,asset_sha(file),
      asset_sha(clip),sha_file(ROOT/'graphics.py'),sha_file(ROOT/'scene_animation.py'),
      sha_file(ROOT/'scene_video.py'),sha_file(ROOT/'svg_engine_legacy.py')])

def audio_key(scene,pr,seconds,voice_path):
    au=scene['audio'];tracks=[(x,asset_sha(x['file'])) for x in au['tracks']]
    continuous=pr.get('trilha_continua',False)
    return digest(['audio-4',au,continuous,('' if continuous else pr['trilha']),('' if continuous else asset_sha(pr['trilha'])),
                   (0 if continuous else pr['volume_musica']),pr['volume_voz'],
                   voice_path.name if voice_path else '',(sha_file(voice_path) if voice_path else ''),
                   asset_sha(au['music_file']),tracks,seconds])

def convert_svg(svg,width,height):
    b=svg.encode()
    try:
        import cairosvg
        return cairosvg.svg2png(bytestring=b,output_width=width,output_height=height)
    except ImportError:pass
    except Exception as e:raise StudioError('Falha CairoSVG: '+str(e)) from e
    exe=shutil.which('magick') or shutil.which('convert')
    if not exe:raise StudioError('Instale ImageMagick: pkg install imagemagick')
    try:
        env=dict(os.environ,MAGICK_THREAD_LIMIT='1',OMP_NUM_THREADS='1')
        p=subprocess.run([exe,'-background','none','-density','96','svg:-','png:-'],input=b,
                         stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=55,env=env)
    except subprocess.TimeoutExpired as e:raise StudioError('Imagem SVG demorou demais') from e
    if p.returncode or not p.stdout.startswith(b'\x89PNG'):
        raise StudioError('Conversão SVG -> PNG: '+p.stderr.decode(errors='replace')[-1000:])
    from PIL import Image
    try:
        with Image.open(io.BytesIO(p.stdout)) as im:
            if im.size!=(width,height):
                im=im.convert('RGB').resize((width,height),Image.Resampling.LANCZOS)
                dst=io.BytesIO();im.save(dst,'PNG');return dst.getvalue()
    except Exception as e:raise StudioError('PNG inválido: '+str(e)) from e
    return p.stdout

def poster(scene,pr,index,total):
    cfg=pr['video'];sec=scene_length(scene,pr,voice=False)
    key=visual_key(scene,pr,sec)
    out=CACHE/'poster'/(key+'.png')
    if out.is_file() and out.stat().st_size>100:return out,False
    svg=visualize(scene,.66,index,total,MEDIA,cfg['width'],cfg['height'])
    tmp=out.with_suffix('.tmp.png');tmp.write_bytes(convert_svg(svg,cfg['width'],cfg['height']));tmp.replace(out)
    return out,True

def render_visual(scene,pr,index,total,seconds,progress=lambda *_:None):
    cfg=pr['video'];key=visual_key(scene,pr,seconds)
    out=CACHE/'visual'/(key+'.mp4')
    if out.is_file() and out.stat().st_size>500 and abs(duration(out)-seconds)<.2:return out,False
    fps=cfg['draw_fps'];output_fps=cfg['fps'];num=round(seconds*fps)
    tmp=out.with_suffix('.partial.mp4')
    args=['ffmpeg','-hide_banner','-loglevel','error','-nostdin','-y','-f','image2pipe','-framerate',str(fps),
          '-vcodec','png','-i','pipe:0','-vf',f'fps={output_fps},format=yuv420p',
          '-c:v','libx264','-threads','2','-preset','veryfast','-crf','25','-pix_fmt','yuv420p','-an','-movflags','+faststart',tmp]
    ff=subprocess.Popen([str(x) for x in args],stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
    err=b''
    try:
        for j in range(num):
            svg=visualize(scene,(j+.5)/num,index,total,MEDIA,cfg['width'],cfg['height'])
            ff.stdin.write(convert_svg(svg,cfg['width'],cfg['height']))
            if j==num-1 or j%max(1,fps)==0:progress((j+1)/num,f'Cena {index+1}: quadro {j+1}/{num}')
        ff.stdin.close();ff.stdin=None
        _,err=ff.communicate(timeout=max(90,int(seconds*12)))
        if ff.returncode:raise StudioError('Codificação da cena: '+err.decode(errors='replace')[-1300:])
        if not tmp.exists() or duration(tmp)<seconds-.2:raise StudioError('Vídeo da cena incompleto')
        clip=scene.get('video_clipe',{})
        if clip.get('arquivo'):
            composed=out.with_suffix('.overlay.mp4')
            try:
                overlay_clip(tmp, media_file(clip['arquivo']), composed, clip,
                  cfg['width'],cfg['height'],cfg['fps'],seconds,run)
                if duration(composed)<seconds-.2:raise StudioError('Sobreposição do vídeo incompleta')
                composed.replace(tmp)
            finally:composed.unlink(missing_ok=True)
        tmp.replace(out);return out,True
    except (BrokenPipeError,OSError) as e:
        raise StudioError('Falha na comunicação com FFmpeg: '+str(e)+' '+err.decode(errors='replace')[-350:]) from e
    finally:
        if ff.poll() is None:ff.kill()
        tmp.unlink(missing_ok=True)

def make_scene_audio(scene,pr,seconds,voice_path):
    key=audio_key(scene,pr,seconds,voice_path)
    out=CACHE/'audio'/(key+'.wav')
    if out.is_file() and out.stat().st_size>1000:
        try:
            with wave.open(str(out),'rb') as wav:
                if wav.getframerate()==48000 and wav.getnchannels()==2 and wav.getnframes()==round(seconds*48000):return out,False
        except wave.Error:pass
    au=scene['audio']
    inputs=[];filters=[];mixed=[];index=0
    def add(file,volume,start=0,loop=False,fade_in=0,fade_out=0):
        nonlocal index
        if not file or volume<=0:return
        if loop:inputs.extend(['-stream_loop','-1'])
        inputs.extend(['-i',str(file)])
        tag=f't{index}';f=f'[{index}:a]aresample=48000,aformat=channel_layouts=stereo,asetpts=PTS-STARTPTS,volume={volume:.5f}'
        usable=max(.05,seconds-start)
        if fade_in>0:f+=f',afade=t=in:st=0:d={min(fade_in,usable):.3f}'
        if fade_out>0:f+=f',afade=t=out:st={max(0,usable-fade_out):.3f}:d={min(fade_out,usable):.3f}'
        f+=f',atrim=0:{usable:.5f},adelay={round(start*1000)}:all=1[{tag}]'
        filters.append(f);mixed.append('['+tag+']');index+=1
    if voice_path:
        add(voice_path,pr['volume_voz']*au['voice_volume'],au['voice_delay'])
    # Per-scene music is unchanged; global music is added *once* after scene concatenation.
    music=au['music_file'] or ('' if pr.get('trilha_continua',False) else pr['trilha'])
    if music:
        vol=au['music_volume'] if au['music_file'] else pr['volume_musica']
        if au['duck_music'] and voice_path:vol*=.33
        add(media_file(music),vol,loop=True)
    for t in au['tracks']:
        add(media_file(t['file']),t['volume'],t['start'],t['loop'],t['fade_in'],t['fade_out'])
    tmp=out.with_suffix('.partial.wav')
    if not mixed:
        with wave.open(str(tmp),'wb') as f:
            f.setnchannels(2);f.setsampwidth(2);f.setframerate(48000)
            chunk=b'\x00'*48000*2*2
            frames=round(seconds*48000)
            for i in range(0,frames,48000):f.writeframes(chunk[:min(48000,frames-i)*4])
    else:
        filters.append(''.join(mixed)+f'amix=inputs={len(mixed)}:normalize=0:duration=longest,alimiter=limit=0.93,apad=whole_dur={seconds:.5f},atrim=0:{seconds:.5f}[a]')
        run(['ffmpeg','-hide_banner','-loglevel','error','-nostdin','-y',*inputs,
             '-filter_complex',';'.join(filters),'-map','[a]','-ar','48000','-ac','2',
             '-c:a','pcm_s16le',tmp],timeout=max(120,int(seconds*8)))
    # Exact sample count is important for concatenation.
    fixed=tmp.with_suffix('.fixed.wav');num=round(seconds*48000)
    with wave.open(str(tmp),'rb') as src, wave.open(str(fixed),'wb') as dst:
        dst.setnchannels(2);dst.setsampwidth(2);dst.setframerate(48000)
        if src.getnchannels()!=2 or src.getsampwidth()!=2 or src.getframerate()!=48000:raise StudioError('Formato interno de áudio inesperado')
        left=num
        while left:
            count=min(left,8192);block=src.readframes(count)
            actual=len(block)//4
            if actual<count:block+=b'\0'*((count-actual)*4)
            dst.writeframesraw(block);left-=count
    fixed.replace(out);tmp.unlink(missing_ok=True)
    return out,True

def continuous_music_signature(pr):
    return [pr.get('trilha_continua',False),pr['trilha'],pr['volume_musica'],asset_sha(pr['trilha'])]


def continuous_duck_intervals(pr, scene_audios):
    """Return positions where the global track should be lowered for the spoken voice."""
    intervals=[];offset=0.
    for scene,audio in zip(pr['cenas'],scene_audios):
        with wave.open(str(audio),'rb') as f:seconds=f.getnframes()/f.getframerate()
        if scene['audio']['duck_music']:
            voice=voice_source(scene,pr,required=False)
            if voice:
                begin=offset+scene['audio']['voice_delay']
                end=min(offset+seconds,begin+duration(voice))
                if end>begin:intervals.append((begin,end))
        offset+=seconds
    return intervals


def apply_continuous_music(dry_path, target, pr, start_seconds=0, duck_intervals=()):
    """Overlay one uninterrupted music stream on the already concatenated scene mix."""
    track=pr.get('trilha')
    volume=pr['volume_musica']
    if not(pr.get('trilha_continua') and track and volume>0):
        shutil.copyfile(dry_path,target)
        return
    music=media_file(track)
    with wave.open(str(dry_path),'rb') as wavein:
        total=wavein.getnframes()/wavein.getframerate()
    # Use a continuously looped music source; offset only matters for scene previews.
    duck=''.join(f",volume=0.33:enable='between(t,{begin:.5f},{end:.5f})'"
                 for begin,end in duck_intervals)
    f=(f'[1:a]aresample=48000,aformat=channel_layouts=stereo,'
       f'atrim=start={max(0,start_seconds):.5f}:duration={total:.5f},asetpts=PTS-STARTPTS,'
       f'volume={volume:.5f}{duck},apad=whole_dur={total:.5f}[music];'
       f'[0:a]aresample=48000,aformat=channel_layouts=stereo[dry];'
       f'[dry][music]amix=inputs=2:normalize=0:duration=first,'
       f'alimiter=limit=0.93,atrim=0:{total:.5f}[a]')
    run(['ffmpeg','-hide_banner','-loglevel','error','-nostdin','-y',
         '-i',dry_path,'-stream_loop','-1','-i',music,
         '-filter_complex',f,'-map','[a]','-ar','48000','-ac','2',
         '-c:a','pcm_s16le',target],timeout=max(120,int(total*5)))


def concat_audio(paths,out,pr=None):
    """Concatenate 48 kHz stereo scenes, adding global soundtrack if requested."""
    import tempfile
    if pr and pr.get('trilha_continua') and pr.get('trilha') and pr.get('volume_musica',0)>0:
        with tempfile.TemporaryDirectory(dir=str(CACHE)) as directory:
            dry=Path(directory)/'dry.wav'
            concat_audio(paths,dry)
            apply_continuous_music(dry,out,pr,duck_intervals=continuous_duck_intervals(pr,paths))
        return
    with wave.open(str(out),'wb') as dst:
        dst.setnchannels(2);dst.setsampwidth(2);dst.setframerate(48000)
        for p in paths:
            with wave.open(str(p),'rb') as src:
                if (src.getnchannels(),src.getsampwidth(),src.getframerate())!=(2,2,48000):raise StudioError('Áudio incompatível em '+str(p))
                while True:
                    data=src.readframes(48000)
                    if not data:break
                    dst.writeframesraw(data)

def mux_video(segments,audios,target,pr=None):
    import tempfile
    target=Path(target);target.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(dir=str(CACHE)) as d:
        d=Path(d);playlist=d/'clips.txt';silent=d/'silent.mp4';audio=d/'audio.wav'
        playlist.write_text(''.join("file '"+str(Path(p).resolve()).replace("'", "'\\''")+"'\n" for p in segments))
        run(['ffmpeg','-hide_banner','-loglevel','error','-nostdin','-y','-f','concat','-safe','0',
             '-i',playlist,'-c','copy','-an',silent],timeout=1800)
        concat_audio(audios,audio,pr)
        tmp=target.with_suffix('.partial.mp4')
        try:
            run(['ffmpeg','-hide_banner','-loglevel','error','-nostdin','-y',
                 '-i',silent,'-i',audio,'-map','0:v:0','-map','1:a:0','-c:v','copy','-c:a','aac',
                 '-b:a','192k','-ar','48000','-ac','2','-movflags','+faststart','-shortest',tmp],timeout=1800)
            if tmp.stat().st_size<1000 or duration(tmp)<1:raise StudioError('Vídeo final inválido')
            tmp.replace(target)
        finally:tmp.unlink(missing_ok=True)
    return target

def export_to_android(target,log=lambda _:None):
    movies=Path.home()/'storage'/'shared'/'Movies'
    if movies.is_dir():
        try:
            shutil.copy2(target,movies/target.name);log('Copiado para Android/Movies/'+target.name)
        except OSError as e:log('Aviso: não foi possível copiar para Movies: '+str(e))

def economy_config(pr):
    """Cópia leve; preserva proporção, cenas, vozes e JSON original."""
    import copy
    p=copy.deepcopy(pr)
    cfg=p['video'];w=cfg['width'];h=cfg['height']
    scale=min(1.0,720/max(w,h))
    cfg['width']=max(320,2*round(w*scale/2))
    cfg['height']=max(320,2*round(h*scale/2))
    cfg['draw_fps']=2
    return p


def project_audio_mix(name,pr,progress=lambda *_:None):
    """Somente áudio; não gera PNG nem MP4 de cena."""
    scenes=pr['cenas'];paths=[];signs=[]
    for i,scene in enumerate(scenes):
        voice=voice_source(scene,pr,required=True)
        seconds=scene_length(scene,pr,voice=True)
        out,modified=make_scene_audio(scene,pr,seconds,voice)
        paths.append(out)
        signs.append(audio_key(scene,pr,seconds,voice))
        progress((i+1)/len(scenes)*.9,f'Áudio da cena {i+1}/{len(scenes)}: '+('gerado' if modified else 'cache'))
    final=OUTPUT/(name+'_mix.wav');manifest=OUTPUT/(name+'_mix.json');signature=digest(['mix25',signs,continuous_music_signature(pr)])
    if final.is_file() and final.stat().st_size>1000 and manifest.is_file():
        try:
            if json.loads(manifest.read_text())['signature']==signature:
                progress(1,'Mix final recuperado do cache')
                return {'audio':final.name,'cached':True}
        except (ValueError,OSError,KeyError):pass
    temporary=final.with_suffix('.partial.wav')
    try:
        concat_audio(paths,temporary,pr)
        temporary.replace(final)
        manifest.write_text(json.dumps({'signature':signature,'duration':duration(final),'cenas':len(scenes)},indent=2))
    finally:temporary.unlink(missing_ok=True)
    progress(1,'Mix pronto, sem gerar vídeo')
    return {'audio':final.name,'cached':False}


def project_render(name,pr,progress=lambda *_:None,mode='render',scene_only=None,no_voice=False):
    scenes=pr['cenas'];total=len(scenes)
    if mode=='mix':
        return project_audio_mix(name,pr,progress)
    if mode=='audio':
        path=batch_audio(pr,progress)
        return {'batch':path.name}
    if mode=='quadros':
        zipfile_path=OUTPUT/(name+'_quadros.zip')
        with zipfile.ZipFile(zipfile_path,'w',zipfile.ZIP_DEFLATED) as z:
            for i,c in enumerate(scenes):
                path,_=poster(c,pr,i,total);z.write(path,f'cena_{i+1:03d}.png')
                progress((i+1)/total,f'Quadro {i+1}/{total}')
        return {'frames':zipfile_path.name}
    # Render either a single scene preview or the whole project.
    indices=[scene_only-1] if scene_only is not None else list(range(total))
    if any(i<0 or i>=total for i in indices):raise StudioError('Índice de cena inválido')
    segs=[];audio=[];signs=[]
    for k,i in enumerate(indices):
        scene=scenes[i];v=voice_source(scene,pr,required=not no_voice) if not no_voice else None
        seconds=scene_length(scene,pr,voice=not no_voice)
        keyv=visual_key(scene,pr,seconds)
        keya=audio_key(scene,pr,seconds,v)
        seg,changed=render_visual(scene,pr,i,total,seconds,
             lambda pc,msg,i=i,k=k:progress((k+pc*.77)/len(indices),msg))
        progress((k+.78)/len(indices),f'Cena {i+1}: '+('renderizada' if changed else 'visual recuperado do cache'))
        aud,a_changed=make_scene_audio(scene,pr,seconds,v)
        segs.append(seg);audio.append(aud);signs.append([keyv,keya])
        progress((k+1)/len(indices),f'Cena {i+1}: áudio '+('atualizado' if a_changed else 'em cache'))
    output=(name+f'_cena_{scene_only:03d}.mp4') if scene_only is not None else (name+'.mp4')
    target=OUTPUT/output;manifest=OUTPUT/(output+'.manifest.json');signature=digest(['final-4',signs,continuous_music_signature(pr) if scene_only is None else None])
    if target.is_file() and target.stat().st_size>1000 and manifest.is_file():
        try:
            if json.loads(manifest.read_text())['signature']==signature and duration(target)>0:
                progress(1,'MP4 final recuperado do cache');export_to_android(target)
                return {'video':target.name,'cached':True}
        except (OSError,KeyError,ValueError):pass
    progress(.95,'Montando MP4 sem reprocessar cenas preservadas')
    mux_video(segs,audio,target,pr if scene_only is None else None)
    manifest.write_text(json.dumps({'signature':signature,'duration':duration(target),'segments':len(segs)},indent=2))
    export_to_android(target)
    progress(1,'MP4 concluído')
    return {'video':target.name,'cached':False}

def cache_status(pr):
    arr=[]
    for i,c in enumerate(pr['cenas']):
        voice=voice_source(c,pr,required=False)
        length=scene_length(c,pr,voice=bool(voice))
        vis=visual_key(c,pr,length)
        aud=audio_key(c,pr,length,voice)
        arr.append({'index':i+1,'id':c['id'],'title':c['titulo'],
                    'visual':(CACHE/'visual'/(vis+'.mp4')).is_file(),
                    'audio':(CACHE/'audio'/(aud+'.wav')).is_file(),
                    'voice':bool(voice) or not(c['audio']['voice_enabled'] and (c['audio']['voice_text'] or c['audio']['voice_file'])),
                    'seconds':length})
    return arr

def clear_scene_cache(pr,scene_num):
    if not 1<=scene_num<=len(pr['cenas']):raise StudioError('Cena não encontrada')
    c=pr['cenas'][scene_num-1];voice=voice_source(c,pr,required=False)
    seconds=scene_length(c,pr,voice=bool(voice))
    for f in [CACHE/'visual'/(visual_key(c,pr,seconds)+'.mp4'),
              CACHE/'audio'/(audio_key(c,pr,seconds,voice)+'.wav'),
              CACHE/'poster'/(visual_key(c,pr,seconds)+'.png')]:f.unlink(missing_ok=True)
    # Regerar o MP4 final numa nova renderização após limpeza de cache.
    for f in OUTPUT.glob('*.manifest.json'):f.unlink(missing_ok=True)
    # Voz neural preservada; sua síntese é gerenciada separadamente.
    return True


def scene_cached_media(pr,index,kind):
    """Somente mídias que correspondem ao JSON atual; nenhum trabalho dispendioso aqui."""
    if not 0<=index<len(pr['cenas']):raise StudioError('Cena inválida')
    c=pr['cenas'][index]
    v=voice_source(c,pr,required=False)
    seconds=scene_length(c,pr,voice=bool(v))
    if kind=='voice':return v
    if kind=='audio':
        p=CACHE/'audio'/(audio_key(c,pr,seconds,v)+'.wav')
        return p if p.is_file() else None
    if kind=='visual':
        p=CACHE/'visual'/(visual_key(c,pr,seconds)+'.mp4')
        return p if p.is_file() else None
    if kind=='poster':
        p=CACHE/'poster'/(visual_key(c,pr,seconds)+'.png')
        return p if p.is_file() else None
    if kind=='image':return media_file(c['imagem']['arquivo']) if c['imagem']['arquivo'] else None
    if kind=='music':return media_file(c['audio']['music_file'] or pr['trilha']) if (c['audio']['music_file'] or pr['trilha']) else None
    if kind=='voice_file':return media_file(c['audio']['voice_file']) if c['audio']['voice_file'] else None
    raise StudioError('Tipo de mídia desconhecido')

def scene_preview(pr,index):
    """Cria apenas uma cópia multiplexada das cenas visuais e áudios em cache."""
    video=scene_cached_media(pr,index,'visual')
    audio=scene_cached_media(pr,index,'audio')
    if video is None or audio is None:
        raise StudioError('Cena ainda não renderizada. Use Renderizar cena ou Renderizar MP4.')
    key=digest(['scene-preview23',sha_file(video),sha_file(audio)])
    out=CACHE/'previews'/(key+'.mp4');out.parent.mkdir(parents=True,exist_ok=True)
    if out.is_file() and out.stat().st_size>1000 and duration(out)>0:return out
    tmp=out.with_suffix('.partial.mp4')
    try:
        run(['ffmpeg','-hide_banner','-loglevel','error','-nostdin','-y',
             '-i',video,'-i',audio,'-map','0:v:0','-map','1:a:0',
             '-c:v','copy','-c:a','aac','-b:a','160k','-movflags','+faststart','-shortest',tmp],timeout=180)
        if duration(tmp)<.5:raise StudioError('Prévia MP4 incompleta')
        tmp.replace(out)
    finally:tmp.unlink(missing_ok=True)
    return out
