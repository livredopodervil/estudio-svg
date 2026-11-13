"""Offline, single-file audiovisual player built from the exact SVG scene renderer.

No calls to localhost and no remote resources. Each sample is calculated at an
absolute progress time; referenced image URI data are de-duplicated across frames.
"""
from __future__ import annotations

import base64
import html
import json
import math
import mimetypes
import re
import subprocess
import tempfile
import uuid
from pathlib import Path

from graphics import visualize
from schema import name, normalize
from studio_core import OUTPUT, MEDIA, StudioError, project_audio_mix, batch_audio, scene_length, voice_source

MAX_HTML_SIZE = 145_000_000
MAX_FRAMES = 3600
DATA_URI_RE = re.compile(r'data:image/(?:png|jpeg|webp);base64,[A-Za-z0-9+/=]+')


def _convert_audio(wav, temp):
    command=['ffmpeg','-hide_banner','-loglevel','error','-nostdin','-y','-i',str(wav),
             '-vn','-codec:a','libmp3lame','-b:a','128k',str(temp)]
    proc=subprocess.run(command, capture_output=True, timeout=240)
    if proc.returncode or not temp.is_file():
        raise StudioError('Falha ao converter mixagem para MP3: '+proc.stderr.decode(errors='replace')[-250:])


def _convert_video(source, temp):
    command=['ffmpeg','-hide_banner','-loglevel','error','-nostdin','-y','-i',str(source),
             '-map','0:v:0','-an','-pix_fmt','yuv420p','-c:v','libx264','-preset','veryfast',
             '-crf','25','-movflags','+faststart',str(temp)]
    proc=subprocess.run(command,capture_output=True,timeout=360)
    if proc.returncode or not temp.is_file():
        raise StudioError('Falha ao converter clipe para HTML: '+proc.stderr.decode(errors='replace')[-250:])


def export_html(identifier, raw_project, media_dir, output_dir, progress=lambda *_:None, with_audio=True):
    project=normalize(raw_project)
    identifier=name(identifier)
    media_dir=Path(media_dir)
    for scene in project['cenas']:
        filename=scene['imagem']['arquivo']
        if filename and (not (media_dir/filename).is_file() or (media_dir/filename).is_symlink()):
            raise StudioError('Imagem referenciada ausente: '+filename)
    output_dir=Path(output_dir)
    output_dir.mkdir(parents=True,exist_ok=True)
    from studio_core import OUTPUT as core_output
    # A presentation mix is stored under OUTPUT and produced by the same backend.
    # Callers use the current application's OUTPUT directory.
    media_data={}
    with tempfile.TemporaryDirectory(prefix='html-', dir=output_dir) as tmp:
        tmp=Path(tmp)
        clips={}
        used_files=sorted({s.get('video_clipe',{}).get('arquivo','') for s in project['cenas']} - {''})
        for i,file in enumerate(used_files):
            source=media_dir / file
            if not source.is_file() or source.is_symlink():
                raise StudioError('Clipe referenciado ausente: '+file)
            # Always transcode to baseline H.264; old MOV/MKV/HEVC recordings must
            # also work when viewing the standalone file on another device.
            target=tmp/(uuid.uuid4().hex+'.mp4')
            _convert_video(source,target)
            clips[file]='data:video/mp4;base64,'+base64.b64encode(target.read_bytes()).decode('ascii')
            progress(.04+.12*(i+1)/max(1,len(used_files)),'Convertendo clipes para reprodução offline')
        durations=[]
        for scene in project['cenas']:
            voice=voice_source(scene,project,required=False)
            durations.append(scene_length(scene,project,voice=bool(voice)))
        audio_uri=''
        if with_audio:
            progress(.15,'Preparando áudio de todas as cenas')
            batch_audio(project,lambda p,m:progress(.15+.08*p,m))
            mixed=project_audio_mix(identifier,project,lambda p,m:progress(.23+.10*p,m))
            mix_path=core_output/mixed['audio']
            converted=tmp/'mix.mp3'
            _convert_audio(mix_path,converted)
            audio_uri='data:audio/mpeg;base64,'+base64.b64encode(converted.read_bytes()).decode('ascii')
            # Recompute lengths after synthesis, which may extend scenes.
            durations=[scene_length(s,project,voice=True) for s in project['cenas']]
        images=[]
        image_ids={}
        timeline=[]
        count=0
        for i,(scene,seconds) in enumerate(zip(project['cenas'],durations)):
            fps=project['video']['draw_fps']
            length=max(1,math.ceil(seconds*fps))
            count+=length
            if count>MAX_FRAMES:
                raise StudioError('Apresentação muito longa para HTML autônomo: limite de 3600 quadros. Reduza draw_fps ou divida o projeto.')
            samples=[]
            for j in range(length):
                p=min(1,j/(fps*seconds))
                svg=visualize(scene,p,i,len(project['cenas']),media_dir,
                    project['video']['width'],project['video']['height'])
                # Each distinct image data URI is shared by reference, not copied
                # into hundreds of frames. JS resolves the references locally.
                def image_repl(m):
                    uri=m.group(0)
                    if uri not in image_ids:
                        image_ids[uri]=len(images)
                        images.append(uri)
                    return 'ssimage:' + str(image_ids[uri])
                samples.append(DATA_URI_RE.sub(image_repl,svg))
            timeline.append({'seconds':seconds,'fps':fps,'frames':samples,'clip':scene.get('video_clipe',{}),
                             'title':scene.get('titulo','')})
            progress(.33+.60*(i+1)/len(durations),f'Preparando quadros offline {i+1}/{len(durations)}')
        data={'title':project['titulo'], 'width':project['video']['width'], 'height':project['video']['height'],
              'scenes':timeline,'images':images,'clips':clips,'audio':audio_uri}
        serialized=json.dumps(data,ensure_ascii=False,separators=(',',':'))
        encoded=base64.b64encode(serialized.encode('utf8')).decode('ascii')
        page=HTML_TEMPLATE.replace('%%TITLE%%',html.escape(project['titulo'],quote=True)).replace('%%PAYLOAD%%',encoded)
        if len(page.encode('utf8'))>MAX_HTML_SIZE:
            raise StudioError('HTML excede 145 MB. Reduza duração, draw_fps ou tamanho dos vídeos.')
        target=output_dir/(identifier+('_standalone.html' if with_audio else '_standalone_sem_audio.html'))
        intermediate=tmp/'standalone.html'
        intermediate.write_text(page,encoding='utf8')
        intermediate.replace(target)
    progress(1,'HTML autônomo concluído')
    return {'html':target.name,'frames':None,'cached':False}


HTML_TEMPLATE=r'''<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover"><meta name="theme-color" content="#080807"><title>%%TITLE%%</title>
<style>
*{box-sizing:border-box}html,body{margin:0;width:100%;height:100%;overflow:hidden;background:#080807;color:#f8e7d1;font-family:system-ui,sans-serif}#screen{position:fixed;inset:0;display:grid;place-items:center;background:#080807}#frame{position:relative;overflow:hidden;background:#080807}#scene{position:absolute;inset:0}#scene svg{width:100%;height:100%;display:block}#video{position:absolute;z-index:2;pointer-events:none;background:#070707}#video[hidden]{display:none}#controls{position:fixed;bottom:max(12px,env(safe-area-inset-bottom));left:50%;transform:translateX(-50%);display:flex;gap:8px;flex-wrap:wrap;align-items:center;justify-content:center;max-width:98vw;background:#17120fdf;border:1px solid #8e6853;border-radius:13px;padding:10px;z-index:3}#controls button{border:1px solid #b99073;background:#473024;color:#fff3df;border-radius:9px;padding:9px 13px;font-size:14px}#note{font-size:12px;max-width:240px}body.playing #controls{display:none}body.playing.reveal #controls{display:flex}#audio{display:none}
</style></head><body><main id="screen"><div id="frame"><div id="scene"></div><video id="video" muted playsinline preload="metadata" hidden></video></div></main>
<div id="controls"><button id="start">▶ Iniciar</button><button id="pause">■ Parar</button><button id="full">⛶ Tela cheia</button><span id="note">Apresentação offline · pressione Iniciar para reproduzir com som.</span></div><audio id="audio" preload="auto"></audio>
<script>
(()=>{'use strict';
const encoded='%%PAYLOAD%%';
const bytes=Uint8Array.from(atob(encoded),x=>x.charCodeAt(0));
const data=JSON.parse(new TextDecoder().decode(bytes));
const $=s=>document.getElementById(s),audio=$('audio'),video=$('video');
const screen=$('screen'),frame=$('frame'),scene=$('scene');
let playing=false,epoch=0,raf=0,last=-1,clipName='',clipScene=-1,showTimer=0;
const total=data.scenes.reduce((t,s)=>t+s.seconds,0);
if(data.audio)audio.src=data.audio;
function fit(){const scale=Math.min(screen.clientWidth/data.width,screen.clientHeight/data.height);frame.style.width=Math.round(data.width*scale)+'px';frame.style.height=Math.round(data.height*scale)+'px';}
function sceneAt(t){let cursor=0;for(let i=0;i<data.scenes.length;i++){const s=data.scenes[i];if(t<cursor+s.seconds||i===data.scenes.length-1)return {i,s,time:Math.max(0,t-cursor)};cursor+=s.seconds;}return {i:0,s:data.scenes[0],time:0};}
function update(t){const {i,s,time}=sceneAt(Math.max(0,t));const index=Math.min(s.frames.length-1,Math.max(0,Math.floor(time*s.fps)));const key=i+':'+index;if(key!==last){last=key;scene.innerHTML=s.frames[index].replace(/ssimage:(\d+)/g,(_,j)=>data.images[+j]);}
const clip=s.clip||{};if(!clip.arquivo||!data.clips[clip.arquivo]){video.pause();video.hidden=true;if(clipName){video.removeAttribute('src');video.load();clipName='';}clipScene=-1;return;}
if(clipName!==clip.arquivo||clipScene!==i){video.pause();clipName=clip.arquivo;clipScene=i;video.src=data.clips[clipName];video.load();}
const x=Number(clip.x??.5),y=Number(clip.y??.56),w=Number(clip.w??.7),h=Number(clip.h??.4);Object.assign(video.style,{left:100*(x-w/2)+'%',top:100*(y-h/2)+'%',width:100*w+'%',height:100*h+'%',objectFit:clip.fit==='contain'?'contain':'cover',opacity:String(clip.opacidade??1)});
const raw=Number(clip.inicio||0)+time;const dur=video.duration;video.loop=!!clip.repetir;if(!clip.repetir&&Number.isFinite(dur)&&raw>=dur){video.pause();video.hidden=true;return;}video.hidden=false;
const wanted=clip.repetir&&Number.isFinite(dur)&&dur>0?raw%dur:raw;if(video.readyState>=1&&Math.abs(video.currentTime-wanted)>.40){try{video.currentTime=wanted;}catch(e){}}
if(playing&&video.paused)video.play().catch(()=>{});if(!playing&&!video.paused)video.pause();}
function stop(){playing=false;cancelAnimationFrame(raf);audio.pause();video.pause();document.body.classList.remove('playing','reveal');$('note').textContent='Apresentação parada. Toque em Iniciar para recomeçar.';}
function tick(now){if(!playing)return;const t=data.audio?audio.currentTime:(now-epoch)/1000;if(t>=total){stop();return;}update(t);raf=requestAnimationFrame(tick);}
$('start').onclick=async()=>{if(playing)return;audio.currentTime=0;try{if(data.audio)await audio.play();}catch(e){$('note').textContent='Áudio bloqueado: '+e.message;return;}playing=true;epoch=performance.now();last=-1;document.activeElement?.blur?.();document.body.classList.add('playing');document.body.classList.remove('reveal');update(0);raf=requestAnimationFrame(tick);};
$('pause').onclick=stop;$('full').onclick=()=>{if(!document.fullscreenElement)document.documentElement.requestFullscreen?.().catch(()=>{});else document.exitFullscreen?.();};
screen.onclick=()=>{if(!playing)return;document.body.classList.add('reveal');clearTimeout(showTimer);showTimer=setTimeout(()=>document.body.classList.remove('reveal'),3500);};
audio.onended=()=>{if(playing)stop();};addEventListener('resize',fit);fit();update(0);
})();
</script></body></html>'''
