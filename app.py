#!/usr/bin/env python3
"""Estúdio SVG V2.7: editor de imagens e apresentação vetorial."""
from __future__ import annotations
import argparse, binascii, base64, io, json, mimetypes, os, re, shutil, subprocess, sys, threading, time, traceback, uuid, hashlib, zipfile
from http.server import ThreadingHTTPServer,BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs,urlsplit
from PIL import Image, ImageOps
from project_bundle import bundle_to_file
from project_import import import_zip
from schema import VERSION, normalize,default_project,name,asset
from studio_core import (StudioError,ROOT,PROJECTS,MEDIA,CACHE,OUTPUT,project_render,cache_status,
                         clear_scene_cache,duration,scene_cached_media,scene_preview)
from graphics import visualize
from svg_graphic import clean_svg
from studio_project_manager_m1p import (
    project_path as managed_project_path, list_projects as managed_list_projects,
    trash_list as managed_trash_list, manage as managed_project_op,
    archive as managed_archive,
)
from offline_export import OfflineExport, OfflineError, MAX_FRAME_BYTES

OFFLINE_EXPORT=OfflineExport(OUTPUT/'.offline-checkpoints',OUTPUT,MEDIA)
BUNDLE_IMPORT_LOCK=threading.RLock()
PROJECT_LOCK=threading.RLock()
JOBS={};JOB_LOCK=threading.RLock();ENGINE_LOCK=threading.Lock();PREVIEW_LOCK=threading.Lock();SVG_LOCK=threading.RLock()

def project_path(project):return managed_project_path(PROJECTS,project)
def read_project(project):
    p=project_path(project)
    if not p.is_file():raise StudioError('Projeto não encontrado: '+project)
    return normalize(json.loads(p.read_text(encoding='utf8')))
def save_project(project,data):
    from studio_workspace import archive_path
    with PROJECT_LOCK:
        p=project_path(project);valid=normalize(data)
        if p.is_symlink() or archive_path(PROJECTS,project).exists():raise StudioError('Projeto arquivado ou caminho inseguro; restaure antes de salvar')
        tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(valid,ensure_ascii=False,indent=2),encoding='utf8');tmp.replace(p)
        return valid

def log_job(job,msg):
    line=str(msg)
    print('['+job['id']+'] '+line,flush=True)
    with JOB_LOCK:
        job['logs'].append(line)
        if len(job['logs'])>250:job['logs']=job['logs'][-250:]

def work(job,project,mode,scene,no_voice):
    with ENGINE_LOCK:
        with JOB_LOCK:job['status']='running';job['phase']='Preparando';job['progress']=.01
        try:
            pr=read_project(project)
            if mode=='render-leve':
                from studio_core import economy_config
                pr=economy_config(pr)
                actual_name=project+'_leve'
                actual_mode='render'
            else:
                actual_name=project
                actual_mode=mode
            def progress(q,msg):
                with JOB_LOCK:
                    job['phase']=msg;job['progress']=min(.99,max(.01,float(q)))
                # Log only stage changes or major steps to avoid network flood.
                now=time.monotonic()
                if now-job.get('lastlog',0)>2 or q>=1 or msg.startswith('MP4'):
                    job['lastlog']=now;log_job(job,msg)
            if mode in ('export-html','export-html-silent'):
                from standalone_html import export_html
                from studio_core import MEDIA as app_media, OUTPUT as app_output
                res=export_html(actual_name,pr,app_media,app_output,progress,with_audio=(mode=='export-html'))
            elif mode=='legendas-lote':
                from studio_core import batch_audio
                from subtitle_times import cues_for_voice
                if pr.get('motor_voz')!='edge-tts':
                    raise StudioError('Tempos por palavra em lote exigem Edge-TTS')
                source=project_path(project).read_bytes()
                updated=0;total=0
                count=max(1,len(pr['cenas']))
                for idx,sc in enumerate(pr['cenas']):
                    cues=cues_for_voice(sc,pr)
                    au=sc.get('audio') or {}
                    eligible=au.get('voice_enabled') and not au.get('muted') and not au.get('voice_file') and str(au.get('voice_text','')).strip()
                    if eligible and not cues:
                        batch_audio({**pr,'cenas':[sc]},lambda pc,msg:progress((idx+pc)*.94/count,msg),export_zip=False,force_timing=True)
                        cues=cues_for_voice(sc,pr)
                    if cues:
                        old=sc.get('legendas') or {}
                        sc['legendas']={**old,'enabled':True,'cues':cues}
                        updated+=1;total+=len(cues)
                    progress((idx+1)*.94/count,f'Legendas {idx+1}/{count}: '+str(len(cues))+' marcas')
                if not updated:
                    raise StudioError('Nenhuma marcação de palavra produzida; verifique textos e narração habilitada')
                with PROJECT_LOCK:
                    if project_path(project).read_bytes()!=source:
                        raise StudioError('Projeto modificado durante a síntese: áudio preservado, tempos não sobrescritos')
                    save_project(project,pr)
                progress(1,'Tempos registrados nas cenas')
                res={'timings':updated,'words':total,'scene_count':len(pr['cenas'])}
            elif mode=='audio-cena':
                from studio_core import batch_audio
                from audio_export import export_scene_voice
                if not isinstance(scene,int) or not (1<=scene<=len(pr['cenas'])):
                    raise StudioError('Número de cena inválido')
                single={**pr,'cenas':[pr['cenas'][scene-1]]}
                batch_audio(single,lambda pc,msg:progress(pc*.70,msg),export_zip=False)
                res=export_scene_voice(actual_name,pr,scene,
                                       lambda pc,msg:progress(.70+.30*pc,msg))
            elif mode in ('audio-mp3','audio-opus','voz-mp3'):
                from audio_export import export_project_audio, export_scene_voice
                if mode=='voz-mp3':
                    res=export_scene_voice(actual_name,pr,scene,progress)
                else:
                    res=export_project_audio(actual_name,pr,mode.removeprefix('audio-'),progress)
            elif mode=='legendas-cena':
                from studio_core import batch_audio
                if not isinstance(scene,int) or not 1<=scene<=len(pr['cenas']):
                    raise StudioError('Cena inválida para geração de tempos')
                current=pr['cenas'][scene-1]
                if pr.get('motor_voz')!='edge-tts' or current['audio'].get('voice_file'):
                    raise StudioError('Geração de tempos exige locução Edge-TTS, não gravação importada')
                if not current['audio']['voice_enabled'] or not current['audio']['voice_text'].strip():
                    raise StudioError('Ative a narração e preencha o texto da cena')
                batch_audio({**pr,'cenas':[current]},progress,export_zip=False,force_timing=True)
                res={'scene':scene,'timings':True}
            elif mode=='apresentacao-audio':
                from studio_core import batch_audio, project_audio_mix
                batch_audio(pr,lambda pc,msg:progress(pc*.45,msg))
                res=project_audio_mix(actual_name,pr,lambda pc,msg:progress(.45+pc*.55,msg))
            else:
                res=project_render(actual_name,pr,progress,actual_mode,scene,no_voice)
            with JOB_LOCK:job.update(status='done',phase='Concluído',progress=1,result=res)
        except Exception as e:
            log_job(job,'ERRO: '+str(e));traceback.print_exc()
            with JOB_LOCK:job.update(status='error',phase='Erro',error=str(e))

def queue_job(project,mode,scene=None,no_voice=False):
    name(project)
    if mode not in ('legendas-lote','quadros','audio','mix','render','render-leve','cena','apresentacao-audio','audio-mp3','audio-opus','voz-mp3','audio-cena','legendas-cena','export-html','export-html-silent'):raise StudioError('Modo inválido')
    if mode in ('cena','voz-mp3','audio-cena','legendas-cena'):
        try:scene=int(scene)
        except (ValueError,TypeError):raise StudioError('Informe o número da cena')
    else:scene=None
    with JOB_LOCK:
        read_project(project)
        active=next((j for j in JOBS.values() if j['status'] in ('queued','running')),None)
        if active:
            if active['project']==project and active['mode']==mode and active['scene']==scene:return active,True
            raise StudioError(f'Já existe uma tarefa ativa: {active["project"]} / {active["mode"]}. Aguarde o término.')
        ident=uuid.uuid4().hex[:12]
        job={'id':ident,'project':project,'mode':mode,'scene':scene,'status':'queued','phase':'Na fila',
             'progress':0,'logs':[],'result':None,'error':None,'lastlog':0}
        JOBS[ident]=job
        # Avoid uncontrolled job history growth.
        if len(JOBS)>45:
            for old in list(JOBS)[:len(JOBS)-40]:
                if JOBS[old]['status'] not in ('running','queued'):del JOBS[old]
    threading.Thread(target=work,args=(job,project,mode,scene,no_voice),daemon=True).start()
    return job,False

VIDEO_EXT={'.mp4','.webm','.mov','.mkv','.m4v'}
AUDIO_EXT={'.mp3','.wav','.m4a','.ogg','.flac','.aac','.webm','.mp4'}
UPLOADS={}
UPLOAD_LOCK=threading.RLock()
MAX_MEDIA_BYTES=250_000_000


def inspect_media(f,kind):
    """Reject corrupt uploads and media without the expected stream type."""
    output=subprocess.run(['ffprobe','-v','error','-show_entries','stream=codec_type',
      '-show_entries','format=duration,format_name','-of','json',str(f)],
      capture_output=True,timeout=35)
    if output.returncode:raise StudioError('FFprobe não reconheceu o arquivo de mídia')
    data=json.loads(output.stdout)
    streams={x.get('codec_type') for x in data.get('streams',[])}
    if kind not in streams:raise StudioError('Arquivo não contém faixa '+('de vídeo' if kind=='video' else 'de áudio'))
    try:seconds=float(data.get('format',{}).get('duration',0))
    except (TypeError,ValueError):seconds=0
    if seconds<=0 and 'matroska' in str(data.get('format',{}).get('format_name','')):
        # Browser MediaRecorder sometimes emits WebM without final duration metadata.
        # Remux losslessly to make audio duration/scene-length detection reliable.
        fixed=f.with_name(f.name+'.fixed.webm')
        try:
            p=subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-nostdin','-y',
               '-i',str(f),'-map','0','-c','copy','-f','webm',str(fixed)],
               capture_output=True,timeout=180)
            if p.returncode or not fixed.is_file():
                raise StudioError('Não foi possível finalizar duração da gravação WebM')
            fixed.replace(f)
            r=subprocess.run(['ffprobe','-v','error','-show_entries','format=duration',
                '-of','default=noprint_wrappers=1:nokey=1',str(f)],capture_output=True,timeout=35)
            seconds=float(r.stdout.decode().strip() or '0')
        finally:fixed.unlink(missing_ok=True)
    if not 0<seconds<=3600:raise StudioError('Duração de mídia inválida (máximo: 60 minutos)')
    return seconds


def store_media_bytes(raw,kind,ext):
    allowed=VIDEO_EXT if kind=='video' else AUDIO_EXT
    if ext not in allowed:raise StudioError('Extensão não permitida para '+kind)
    final=MEDIA/(uuid.uuid4().hex[:12]+ext)
    temp=CACHE/(uuid.uuid4().hex+'.upload')
    try:
        temp.write_bytes(raw)
        inspect_media(temp,kind)
        temp.replace(final)
        return final.name
    finally:temp.unlink(missing_ok=True)


def image_alias(raw):
    """Convert a user label to a safe JPEG basename; never overwrite existing media."""
    label = str(raw or '').strip()
    stem = re.sub(r'[^A-Za-z0-9_-]+', '_', Path(label).stem).strip('_')[:70]
    if not stem:raise StudioError('Escolha um nome com letras ou números')
    candidate = stem + '.jpg'
    i = 2
    while (MEDIA/candidate).exists():
        candidate = f'{stem}_{i}.jpg'
        i += 1
        if i > 10000:raise StudioError('Não foi possível encontrar nome livre')
    return candidate


def presentation_mix_status(project_name, project):
    """Return scene durations and the current mix, never a stale audio file.

    project_audio_mix writes signature mix25; older presentation handlers
    incorrectly checked mix24 and therefore always reported the mix absent.
    """
    from studio_core import scene_length, voice_source, audio_key, digest, continuous_music_signature
    durations=[]
    keys=[]
    for scene in project['cenas']:
        voice=voice_source(scene,project,required=False)
        seconds=scene_length(scene,project,voice=bool(voice))
        durations.append(seconds)
        keys.append(audio_key(scene,project,seconds,voice))
    expected=digest(['mix25',keys,continuous_music_signature(project)])
    audio=OUTPUT/(name(project_name)+'_mix.wav')
    meta=OUTPUT/(name(project_name)+'_mix.json')
    ready=False
    if audio.is_file() and meta.is_file() and audio.stat().st_size>44:
        try:
            ready=json.loads(meta.read_text(encoding='utf8')).get('signature')==expected
        except (OSError,ValueError,TypeError):pass
    return durations,(audio if ready else None)


class Handler(BaseHTTPRequestHandler):
    server_version='EstudioSVG/3.0-alpha'
    def log_message(self,fmt,*args):print('HTTP: '+fmt%args,flush=True)
    def response(self,status,data,mime='application/json; charset=utf-8'):
        if isinstance(data,(dict,list)):data=json.dumps(data,ensure_ascii=False).encode('utf8')
        elif isinstance(data,str):data=data.encode('utf8')
        self.send_response(status)
        for k,v in [('Content-Type',mime),('Content-Length',str(len(data))),('Cache-Control','no-store'),
                    ('X-Content-Type-Options','nosniff')]:self.send_header(k,v)
        self.end_headers()
        if self.command!='HEAD':self.wfile.write(data)
    def stream_file(self,path,extra_headers=None):
        f=Path(path)
        if not f.is_file():return self.response(404,{'error':'Mídia ainda não disponível'})
        ext=f.suffix.lower();ctype={'.mp4':'video/mp4','.mp3':'audio/mpeg','.wav':'audio/wav',
          '.m4a':'audio/mp4','.ogg':'audio/ogg','.flac':'audio/flac','.aac':'audio/aac',
          '.webm':'video/webm','.m4v':'video/mp4','.mov':'video/quicktime','.mkv':'video/x-matroska',
          '.png':'image/png','.jpg':'image/jpeg','.jpeg':'image/jpeg'}.get(ext,'application/octet-stream')
        size=f.stat().st_size;start=0;end=size-1;partial=False
        rh=self.headers.get('Range','')
        if rh:
            m=re.fullmatch(r'bytes=(\d*)-(\d*)',rh)
            if not m or (not m.group(1) and not m.group(2)):
                self.send_response(416);self.send_header('Content-Range',f'bytes */{size}');self.end_headers();return
            if not m.group(1):
                count=int(m.group(2));start=max(0,size-count)
            else:
                start=int(m.group(1))
                if m.group(2):end=min(size-1,int(m.group(2)))
            if start>=size or start>end:
                self.send_response(416);self.send_header('Content-Range',f'bytes */{size}');self.end_headers();return
            partial=True
        self.send_response(206 if partial else 200)
        self.send_header('Content-Type',ctype)
        self.send_header('Content-Length',str(end-start+1))
        self.send_header('Accept-Ranges','bytes')
        self.send_header('Cache-Control','no-store')
        self.send_header('X-Content-Type-Options','nosniff')
        if partial:self.send_header('Content-Range',f'bytes {start}-{end}/{size}')
        for k,v in (extra_headers or {}).items():self.send_header(k,v)
        self.end_headers()
        if self.command=='HEAD':return
        try:
            with f.open('rb') as inp:
                inp.seek(start);left=end-start+1
                while left>0:
                    data=inp.read(min(128*1024,left))
                    if not data:break
                    self.wfile.write(data);left-=len(data)
        except (BrokenPipeError,ConnectionResetError):pass

    def chunked_upload(self,v):
        """Sequential, bounded chunks allow camera recordings beyond JSON body limits."""
        action=str(v.get('op',''))
        with UPLOAD_LOCK:
            now=time.monotonic()
            for old,rec in list(UPLOADS.items()):
                if now-rec['last']>3600:
                    rec['path'].unlink(missing_ok=True);del UPLOADS[old]
            if action=='start':
                kind=str(v.get('kind',''))
                ext=Path(str(v.get('filename',''))).suffix.lower()
                if kind not in ('audio','video','bundle') or ext not in ({'.zip'} if kind=='bundle' else AUDIO_EXT if kind=='audio' else VIDEO_EXT):
                    raise StudioError('Formato de mídia não permitido')
                size=int(v.get('size',0))
                if not 0<size<=MAX_MEDIA_BYTES:raise StudioError('Arquivo maior que 250 MB')
                token=uuid.uuid4().hex
                path=CACHE/(token+'.upload')
                path.touch(exist_ok=False)
                UPLOADS[token]={'path':path,'ext':ext,'kind':kind,'size':size,'count':0,'next':0,'last':now}
                return self.response(200,{'upload_id':token})
            token=str(v.get('upload_id',''))
            rec=UPLOADS.get(token)
            if not rec:raise StudioError('Envio não encontrado ou expirado')
            rec['last']=now
            if action=='append':
                index=int(v.get('index',-1))
                if index!=rec['next']:raise StudioError('Fragmentos fora de ordem')
                data=base64.b64decode(str(v.get('data','')),validate=True)
                if not data or len(data)>1_300_000 or rec['count']+len(data)>rec['size']:
                    raise StudioError('Fragmento excede o tamanho anunciado')
                with rec['path'].open('ab') as out:out.write(data)
                rec['count']+=len(data);rec['next']+=1
                return self.response(200,{'received':rec['count']})
            if action=='abort':
                rec['path'].unlink(missing_ok=True);del UPLOADS[token]
                return self.response(200,{'aborted':True})
            if action=='finish':
                if rec['count']!=rec['size']:raise StudioError('Envio incompleto')
                try:
                    if rec['kind']=='bundle':
                        with BUNDLE_IMPORT_LOCK, PROJECT_LOCK:
                            result=import_zip(rec['path'],v.get('name',''),PROJECTS,MEDIA,CACHE,inspect_media)
                            # Legacy importers may ignore media referenced only by instance_library.
                            from studio_instance_assets import restore_instance_media
                            result['instance_media_restored']=restore_instance_media(rec['path'],MEDIA)
                        return self.response(200,result)
                    inspect_media(rec['path'],rec['kind'])
                    fn=uuid.uuid4().hex[:12]+rec['ext']
                    rec['path'].replace(MEDIA/fn)
                    return self.response(200,{'filename':fn})
                finally:
                    rec['path'].unlink(missing_ok=True);del UPLOADS[token]
            raise StudioError('Operação de envio inválida')

    def payload(self,maxbytes=6_000_000):
        if not self.headers.get('Content-Type','').startswith('application/json'):raise StudioError('Requisição deve ser JSON')
        try:n=int(self.headers.get('Content-Length',0))
        except ValueError:raise StudioError('Content-Length inválido')
        if not 1<=n<=maxbytes:raise StudioError('Tamanho da requisição fora do limite')
        return json.loads(self.rfile.read(n))
    def valid_origin(self):
        origin=self.headers.get('Origin')
        if not origin:return True
        u=urlsplit(origin)
        return u.scheme=='http' and u.hostname in ('localhost','127.0.0.1') and u.port==self.server.server_port
    def route(self,method):
        url=urlsplit(self.path);route=url.path;args=parse_qs(url.query)
        def q(key,default=''):return args.get(key,[default])[0]
        try:
            if method=='POST' and not self.valid_origin():return self.response(403,{'error':'Origem não autorizada'})
            if route=='/api/health' and method=='GET':
                return self.response(200,{'ok':True,'version':VERSION,
                    'tools':{k:bool(shutil.which(k)) for k in ['ffmpeg','ffprobe','edge-tts','convert','espeak-ng','piper','termux-tts-speak']}})
            if route=='/api/player-v3' and method=='GET':
                identifier=name(q('name'));project=read_project(identifier)
                revision=hashlib.sha256(json.dumps(project,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
                if q('revision') and q('revision')!=revision:raise StudioError('Projeto alterado; reabra o Player.')
                if q('scene'):
                    if q('revision')!=revision:raise StudioError('Projeto alterado; reabra o Player.')
                    i=int(q('scene'))-1
                    if not 0<=i<len(project['cenas']):raise StudioError('Cena inválida')
                    v=project['video'];c=project['cenas'][i]
                    # Camadas e SVG procedurais recebem a mesma composição de graphics.
                    src=visualize(c,1,i,len(project['cenas']),MEDIA,v['width'],v['height'],browser=True)
                    return self.response(200,src,'image/svg+xml; charset=utf-8')
                from studio_core import voice_source
                voices={}
                for i,c in enumerate(project['cenas']):
                    try:ready=voice_source(c,project,required=False)
                    except StudioError:ready=None
                    if ready:voices[str(i)]='/api/player-v3/voice?name='+identifier+'&scene='+str(i+1)+'&revision='+revision
                return self.response(200,{'project':project,'revision':revision,'voices':voices})
            if route=='/api/player-v3/voice' and method=='GET':
                identifier=name(q('name'));project=read_project(identifier)
                revision=hashlib.sha256(json.dumps(project,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
                if q('revision')!=revision:raise StudioError('Projeto alterado; reabra o Player.')
                i=int(q('scene'))-1
                if not 0<=i<len(project['cenas']):raise StudioError('Cena inválida')
                from studio_core import voice_source
                path=voice_source(project['cenas'][i],project,required=False)
                if path is None:return self.response(404,{'error':'Voz não disponível'})
                return self.stream_file(path)
            if route=='/api/presentation' and method=='GET':
                identifier=name(q('name'))
                project=read_project(identifier)
                mix_error=None
                try:durations,mix=presentation_mix_status(identifier,project)
                except StudioError as exc:
                    if not str(exc).startswith('Narração excede a duração da cena:'):raise
                    durations=[c['duracao'] for c in project['cenas']];mix=None;mix_error=str(exc)
                return self.response(200,{'project':project,'durations':durations,'mix_error':mix_error,
                    'mix_ready':bool(mix),'audio_url':('/api/presentation/audio?name='+identifier) if mix else None})
            if route=='/api/presentation/audio' and method=='GET':
                identifier=name(q('name'))
                _,mix=presentation_mix_status(identifier,read_project(identifier))
                if not mix:
                    return self.response(404,{'error':'Mix ausente ou desatualizado. Use Preparar áudio na apresentação.'})
                return self.stream_file(mix)
            if route=='/api/svg/clean' and method=='POST':
                v=self.payload(9_000_000)
                doc=clean_svg(v.get('svg',''),MEDIA,storage=True)
                return self.response(200,{'svg':clean_svg(doc,MEDIA,storage=False)})
            if route=='/api/vector/status' and method=='GET':
                return self.response(200,{'installed':(ROOT/'web'/'vendor'/'svgedit'/'editor'/'Editor.js').is_file(),
                   'version':'7.4.2','editor_url':'/vetor'})
            if route=='/api/svg/document' and method=='GET':
                pr=read_project(q('name'));idx=int(q('scene','1'))-1
                if not 0<=idx<len(pr['cenas']):raise StudioError('Cena não existe')
                scene=pr['cenas'][idx]
                if scene['tipo']!='svg':raise StudioError('Converta a cena para tipo SVG no Estúdio')
                raw=scene.get('svg','') or '<g class="layer" id="layer1"><title>Camada 1</title></g>'
                svg=clean_svg(raw,MEDIA,storage=False)
                revision=hashlib.sha256(scene.get('svg','').encode('utf8')).hexdigest()
                cfg=pr['video']
                return self.response(200,{'svg':svg,'revision':revision,'title':scene['titulo'],
                    'canvas_height':round(1280*cfg['height']/cfg['width']),
                    'format':f"{cfg['width']}×{cfg['height']}",'project':q('name'),'scene':idx+1})
            if route=='/api/svg/document' and method=='POST':
                v=self.payload(9_000_000)
                n=name(v.get('name',''));idx=int(v.get('scene',0))-1
                with SVG_LOCK:
                    pr=read_project(n)
                    if not 0<=idx<len(pr['cenas']):raise StudioError('Cena não existe')
                    scene=pr['cenas'][idx]
                    if scene['tipo']!='svg':raise StudioError('Essa cena não é SVG')
                    expected=str(v.get('revision',''))
                    actual=hashlib.sha256(scene.get('svg','').encode('utf8')).hexdigest()
                    if expected!=actual:raise StudioError('A cena foi alterada em outra aba. Recarregue antes de salvar.')
                    doc=clean_svg(v.get('svg',''),MEDIA,storage=True)
                    if len(doc)>2_000_000:raise StudioError('SVG excedeu o limite após conversão das imagens')
                    scene['svg']=doc
                    # Backup the project before overwriting (last saved state).
                    old=project_path(n)
                    if old.is_file():shutil.copy2(old,old.with_suffix('.vector-backup.json'))
                    save_project(n,pr)
                    revision=hashlib.sha256(doc.encode('utf8')).hexdigest()
                return self.response(200,{'ok':True,'revision':revision,'scene':idx+1})
            if route=='/api/project/bundle' and method=='GET':
                identifier=name(q('name'))
                pr=read_project(identifier)
                if any((c.get('gil_nativo') or c.get('objetos_midia')) for c in pr['cenas']):raise StudioError('ZIP com GIL nativa ainda não validado; preserve o JSON do projeto.')
                # Unique temporary file avoids collisions between concurrent requests.
                temporary=CACHE/('bundle-'+uuid.uuid4().hex+'.zip')
                try:
                    bundle_to_file(identifier,pr,MEDIA,temporary)
                    self.send_response(200)
                    self.send_header('Content-Type','application/zip')
                    self.send_header('Content-Disposition',f'attachment; filename="{identifier}-com-midia.zip"')
                    self.send_header('Content-Length',str(temporary.stat().st_size))
                    self.send_header('Cache-Control','no-store')
                    self.end_headers()
                    with temporary.open('rb') as src:shutil.copyfileobj(src,self.wfile,256*1024)
                finally:temporary.unlink(missing_ok=True)
                return
            if route=='/api/media/image/alias' and method=='POST':
                v=self.payload()
                old=asset(v.get('file',''))
                if not old or Path(old).suffix.lower() not in ('.jpg','.jpeg','.png','.webp'):
                    raise StudioError('Imagem de origem inválida')
                src=MEDIA/old
                if not src.is_file() or src.is_symlink():raise StudioError('Imagem original não encontrada')
                fresh=image_alias(v.get('new_name',''))
                # New alias is a copy. Other scenes keep the original basename.
                with (MEDIA/fresh).open('xb') as target:
                    try:
                        if src.suffix.lower() in ('.jpg','.jpeg'):
                            with src.open('rb') as original:shutil.copyfileobj(original,target,256*1024)
                        else:
                            with Image.open(src) as picture:
                                ImageOps.exif_transpose(picture).convert('RGB').save(target,'JPEG',quality=90)
                    except Exception:
                        (MEDIA/fresh).unlink(missing_ok=True)
                        raise
                return self.response(200,{'filename':fresh,'original':old})
            if route=='/api/project/validate' and method=='POST':
                # Validation is read-only: no project file is created or overwritten.
                data=self.payload(6_000_000)
                return self.response(200,{'ok':True,'project':normalize(data.get('project'))})
            if route=='/api/workspace/voice-plan' and method=='POST':
                from studio_workspace import voice_plan
                v=self.payload();return self.response(200,{'rows':voice_plan(v['project'],v['first'],v['last'])})
            if route=='/api/workspace/inventory' and method=='POST':
                from studio_workspace import inventory
                v=self.payload();return self.response(200,{'files':inventory(v['project'],MEDIA)})
            if route=='/api/workspace/archived' and method=='GET':
                from studio_workspace import archived_projects
                with PROJECT_LOCK:return self.response(200,{'projects':archived_projects(PROJECTS)})
            if route=='/api/workspace/archive' and method=='POST':
                from studio_workspace import change_archive
                port=self.server.server_port
                if self.headers.get('Origin') not in (f'http://127.0.0.1:{port}',f'http://localhost:{port}') or self.headers.get('Host') not in (f'127.0.0.1:{port}',f'localhost:{port}'):
                    return self.response(403,{'error':'Origem local explícita necessária'})
                v=self.payload();identifier=name(v.get('name'));action=v.get('action')
                if action not in ('archive','restore') or v.get('confirm')!=identifier:raise StudioError('Confirmação inválida')
                with BUNDLE_IMPORT_LOCK, JOB_LOCK, PROJECT_LOCK:
                    if any(j['status'] in ('queued','running') for j in JOBS.values()):raise StudioError('Aguarde o fim da produção')
                    managed_archive(PROJECTS,identifier,restore=action=='restore')
                return self.response(200,{'ok':True,'name':identifier})
            if route=='/api/workspace/gil-example' and method=='GET':
                root=os.environ.get('RD_GIL_ROOT');key=q('id')
                allowed={'native-demo','basic-geometry','orbit-simple','pulse-simple'}
                if not root or key not in allowed:raise StudioError('Exemplo indisponível; inicie pelo RD Studio integrado')
                base=ROOT/'examples'/'components';src=base/(key+'.gil')
                if not src.is_file() or src.is_symlink() or src.stat().st_size>250000:raise StudioError('Exemplo GIL ausente ou inválido')
                return self.response(200,{'source':src.read_text('utf8'),'name':key+'.gil'})
            if route=='/api/project/manage' and method=='POST':
                v=self.payload();action=v.get('action','')
                identifier=v.get('name','')
                if action not in ('mkdir','restore') and (not identifier or v.get('confirm')!=identifier):
                    raise StudioError('Confirme o identificador do projeto')
                with BUNDLE_IMPORT_LOCK, JOB_LOCK, PROJECT_LOCK:
                    if any(j['status'] in ('queued','running') for j in JOBS.values()):
                        raise StudioError('Finalize a tarefa de renderização/voz antes de gerenciar projetos')
                    result=managed_project_op(PROJECTS, action, identifier,
                        new_name=v.get('new_name',''), folder=v.get('folder',''), token=v.get('token',''))
                return self.response(200,result)
            if route=='/api/projects' and method=='GET':
                r=managed_list_projects(PROJECTS);r['trash']=managed_trash_list(PROJECTS);return self.response(200,r)
            if route=='/api/project' and method=='GET':return self.response(200,{'name':q('name','demo_organico'),'project':read_project(q('name','demo_organico'))})
            if route=='/api/project' and method=='POST':
                data=self.payload(6_000_000);pr=save_project(data.get('name',''),data.get('project'))
                return self.response(200,{'ok':True,'cenas':len(pr['cenas'])})
            if route=='/api/project/rename' and method=='POST':
                port=self.server.server_port
                if self.headers.get('Origin') not in (f'http://127.0.0.1:{port}',f'http://localhost:{port}') or self.headers.get('Host') not in (f'127.0.0.1:{port}',f'localhost:{port}'):
                    return self.response(403,{'error':'Origem local explícita necessária'})
                v=self.payload(4096)
                old=name(v.get('name',''));new=name(v.get('new_name',''))
                if v.get('confirm')!=old:raise StudioError('Confirmação inválida')
                from studio_project_ops import rename_project
                with BUNDLE_IMPORT_LOCK,JOB_LOCK,PROJECT_LOCK:
                    if any(j['status'] in ('queued','running') for j in JOBS.values()):raise StudioError('Aguarde a produção terminar')
                    rename_project(PROJECTS,old,new)
                return self.response(200,{'ok':True,'old_name':old,'name':new})
            if route=='/api/project/new' and method=='POST':
                v=self.payload();n=name(v.get('name',''))
                if project_path(n).exists():raise StudioError('Nome já existe')
                pr=default_project();pr['titulo']=str(v.get('titulo','Novo projeto'))[:180]
                pr['cenas']=pr['cenas'][:1];save_project(n,pr)
                return self.response(200,{'name':n})
            if route=='/api/preview' and method=='POST':
                data=self.payload(2_600_000)
                c=normalize({'cenas':[data['scene']]})['cenas'][0]
                v=data.get('video',{}) if isinstance(data.get('video'),dict) else {}
                w=int(v.get('width',1280));h=int(v.get('height',720))
                if min(w,h)<320 or max(w,h)>1920:raise StudioError('Resolução inválida')
                src=visualize(c,float(data.get('progress',0)),int(data.get('index',0)),int(data.get('total',1)),MEDIA,w,h)
                return self.response(200,src,'image/svg+xml; charset=utf-8')
            if route.startswith('/api/offline-export/'):
                # API de escrita restrita ao host/origem do Studio; token não previsível.
                port=self.server.server_port
                allowed=(f'http://127.0.0.1:{port}',f'http://localhost:{port}')
                if self.headers.get('Origin') not in allowed or self.headers.get('Host') not in (f'127.0.0.1:{port}',f'localhost:{port}'):
                    return self.response(403,{'error':'Exportação offline exige origem e host locais explícitos'})
                if route=='/api/offline-export/plan' and method=='POST':
                    from studio_core import browser_audio_plan
                    v=self.payload(6_000_000);pr=normalize(v['project'])
                    with ENGINE_LOCK: lengths,_=browser_audio_plan(pr)
                    return self.response(200,{'durations':lengths})
                if route=='/api/offline-export/start' and method=='POST':
                    from studio_core import browser_audio_plan,browser_audio_mix
                    v=self.payload(6_000_000);pr=normalize(v['project'])
                    if not ENGINE_LOCK.acquire(blocking=False):
                        raise StudioError('Produção de áudio ocupada; tente novamente após sua conclusão')
                    try:
                        planning=browser_audio_plan(pr)
                        return self.response(200,OFFLINE_EXPORT.start(
                            pr,durations=planning[0],voices=planning[1],
                            build_mix=lambda dest:browser_audio_mix(pr,dest,planning),
                            gil_events=v.get('gil_audio',[]),fps=int(pr['video']['fps']),
                            width=int(pr['video']['width']),height=int(pr['video']['height'])))
                    finally:ENGINE_LOCK.release()
                if route=='/api/offline-export/frame' and method=='POST':
                    if self.headers.get('Content-Type')!='image/png':
                        raise OfflineError('Quadro precisa ser PNG')
                    try:n=int(self.headers.get('Content-Length','0'))
                    except (TypeError,ValueError):raise OfflineError('Content-Length inválido')
                    if not 100<=n<=MAX_FRAME_BYTES:raise OfflineError('Quadro ultrapassa limite de upload')
                    return self.response(200,OFFLINE_EXPORT.upload(q('token'),int(q('index','-1')),self.rfile.read(n)))
                if route=='/api/offline-export/status' and method=='GET':
                    return self.response(200,OFFLINE_EXPORT.status(q('token')))
                if route=='/api/offline-export/finish' and method=='POST':
                    v=self.payload(2048)
                    return self.response(200,OFFLINE_EXPORT.finish(v.get('token')))
                return self.response(405,{'error':'Método de exportação offline não autorizado'})
            if route=='/api/browser-render/audio' and method=='POST':
                import tempfile
                from studio_core import browser_audio_mix, browser_audio_plan
                data=self.payload(6_000_000);pr=normalize(data['project'])
                if data.get('stream') is True:
                    # Only this dedicated disposable directory; no project/media/cache eviction.
                    import studio_core as core
                    folder=core.CACHE/'browser-render';folder.mkdir(exist_ok=True)
                    if folder.is_symlink():raise StudioError('Pasta de mix web insegura.')
                    if not ENGINE_LOCK.acquire(blocking=False):raise StudioError('Aguarde o fim da produção de áudio/vídeo.')
                    token=uuid.uuid4().hex;path=folder/(token+'.wav')
                    try:
                        for old in folder.glob('*.wav'):
                            if re.fullmatch(r'[0-9a-f]{32}\.wav',old.name) and not old.is_symlink() and old.is_file() and time.time()-old.stat().st_mtime>86400:old.unlink(missing_ok=True)
                        planning=browser_audio_plan(pr)
                        browser_audio_mix(pr,path,planning)
                    except Exception:
                        path.unlink(missing_ok=True);raise
                    finally:ENGINE_LOCK.release()
                    return self.response(200,{'token':token,'durations':planning[0],'url':'/api/browser-render/mix?token='+token})
                with tempfile.TemporaryDirectory(prefix='estudio-web-audio-') as directory:
                    path=Path(directory)/'mix.wav'
                    if not ENGINE_LOCK.acquire(blocking=False):raise StudioError('Aguarde o fim da produção de áudio/vídeo.')
                    try:
                        planning=browser_audio_plan(pr)
                        browser_audio_mix(pr,path,planning)
                    finally:ENGINE_LOCK.release()
                    return self.stream_file(path,{'X-Estudio-Durations':json.dumps(planning[0],separators=(',',':'))})
            if route in ('/api/browser-render/mix','/api/browser-render/release'):
                import studio_core as core
                token=q('token','') if method=='GET' else self.payload(1024).get('token','')
                if not isinstance(token,str) or not re.fullmatch(r'[0-9a-f]{32}',token):raise StudioError('Token de mix inválido')
                folder=core.CACHE/'browser-render';path=folder/(token+'.wav')
                if folder.is_symlink() or path.is_symlink():raise StudioError('Caminho de mix inseguro')
                if route.endswith('/mix') and method=='GET':return self.stream_file(path)
                if route.endswith('/release') and method=='POST':
                    path.unlink(missing_ok=True);return self.response(200,{'ok':True})
                return self.response(405,{'error':'Método inválido'})
            if route=='/api/scene/media' and method=='GET':
                pr=read_project(q('name'));idx=int(q('scene','1'))-1
                kind=q('kind','voice')
                if kind not in ('voice','audio','visual','poster','image','music','voice_file'):
                    raise StudioError('Tipo de áudio/vídeo inválido')
                path=scene_cached_media(pr,idx,kind)
                if path is None and kind=='audio' and q('prepare')=='1':
                    from studio_core import prepare_preview_audio
                    with ENGINE_LOCK:path=prepare_preview_audio(pr,idx)
                if path is None:return self.response(404,{'error':'Mídia não gerada ou não importada'})
                return self.stream_file(path)
            if route=='/api/scene/preview' and method=='POST':
                v=self.payload();pr=read_project(v['name']);idx=int(v['scene'])-1
                with PREVIEW_LOCK:path=scene_preview(pr,idx)
                return self.response(200,{'url':'/api/scene/preview-file?name='+v['name']+'&scene='+str(idx+1)})
            if route=='/api/scene/preview-file' and method=='GET':
                pr=read_project(q('name'));idx=int(q('scene','1'))-1
                # idempotent, only cached media can be multiplexed
                with PREVIEW_LOCK:path=scene_preview(pr,idx)
                return self.stream_file(path)
            if route=='/api/tts/android' and method=='POST':
                v=self.payload(12000)
                pr=read_project(v['name']);idx=int(v['scene'])-1
                if not 0<=idx<len(pr['cenas']):raise StudioError('Cena não existe')
                phrase=pr['cenas'][idx]['audio']['voice_text'].strip()
                if not phrase:raise StudioError('Esta cena não possui texto de voz')
                if not shutil.which('termux-tts-speak'):
                    raise StudioError('Instale pkg install termux-api e o aplicativo Termux:API')
                # A voz sai nos alto-falantes do Android. O comando NÃO cria WAV.
                try:
                    result=subprocess.run(['termux-tts-speak','-l','pt','-n','BR',phrase[:3500]],
                        stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=20)
                except subprocess.TimeoutExpired:raise StudioError('Termux:API não respondeu em 20 s')
                if result.returncode:raise StudioError('Falha no TTS Android: '+result.stderr.decode(errors='replace')[-400:])
                return self.response(200,{'ok':True,'message':'Solicitada reprodução no Android; sem arquivo exportado'})
            if route=='/api/preview/timing' and method=='GET':
                from studio_core import scene_length,voice_source
                pr=read_project(q('name'))
                return self.response(200,{'scenes':[{'id':c['id'],'seconds':scene_length(c,pr,voice=bool(voice_source(c,pr,required=False)))} for c in pr['cenas']]})
            if route=='/api/subtitles/voice-cues' and method=='GET':
                identifier=name(q('name'))
                pr=read_project(identifier)
                i=int(q('scene','0'))-1
                if not 0<=i<len(pr['cenas']):raise StudioError('Cena inválida')
                from subtitle_times import cues_for_voice
                cues=cues_for_voice(pr['cenas'][i],pr)
                if not cues:return self.response(404,{'error':'Tempos de palavras indisponíveis. Gere a locução com tempos ou importe SRT/VTT.'})
                return self.response(200,{'source':'edge-tts','cues':cues,'count':len(cues)})
            if route=='/api/cache/status' and method=='GET':return self.response(200,{'scenes':cache_status(read_project(q('name')))})
            if route=='/api/cache/clear' and method=='POST':
                v=self.payload();return self.response(200,{'ok':clear_scene_cache(read_project(v['name']),int(v['scene']))})
            if route=='/api/job' and method=='POST':
                v=self.payload();j,reused=queue_job(v.get('name',''),v.get('mode','render'),v.get('scene'),bool(v.get('no_voice',False)))
                return self.response(202,{'job':j['id'],'reused':reused})
            if route=='/api/jobs/active' and method=='GET':
                with JOB_LOCK:active=next((j for j in JOBS.values() if j['status'] in ('queued','running')),None)
                return self.response(200,{'job':active['id'] if active else None})
            if route.startswith('/api/job/') and method=='GET':
                with JOB_LOCK:j=JOBS.get(route.split('/')[-1])
                if not j:return self.response(404,{'error':'Trabalho não encontrado'})
                return self.response(200,{k:v for k,v in j.items() if k!='lastlog'})
            if route=='/api/media/image' and method=='GET':
                fname=asset(q('file'))
                if not fname or Path(fname).suffix.lower() not in ('.jpg','.jpeg','.png','.webp'):
                    raise StudioError('Imagem inválida')
                f=MEDIA/fname
                if not f.is_file():return self.response(404,{'error':'Imagem não encontrada'})
                ctype=mimetypes.guess_type(fname)[0] or 'application/octet-stream'
                return self.response(200,f.read_bytes(),ctype)
            if route=='/api/media/clip' and method=='GET':
                filename=asset(q('file'))
                if not filename or Path(filename).suffix.lower() not in VIDEO_EXT:
                    raise StudioError('Formato de vídeo inválido')
                return self.stream_file(MEDIA/filename)
            if route=='/api/component/gil' and method=='POST':
                origin=self.headers.get('Origin','');port=self.server.server_port
                if origin not in (f'http://127.0.0.1:{port}',f'http://localhost:{port}') or self.headers.get('Host') not in (f'127.0.0.1:{port}',f'localhost:{port}'):
                    return self.response(403,{'error':'Origem local explícita necessária'})
                from gil_bridge import render_component
                data=self.payload(800_000)
                if not ENGINE_LOCK.acquire(blocking=False):return self.response(409,{'error':'Outra renderização está em andamento'})
                try:
                    result=render_component(data,os.environ.get('RD_GIL_ROOT'),os.environ.get('RD_SPATIALSEED_ROOT'),CACHE,store_media_bytes,inspect_media)
                    return self.response(200,result)
                finally:ENGINE_LOCK.release()
            if route=='/api/upload/chunks' and method=='POST':
                return self.chunked_upload(self.payload(2_000_000))
            if route=='/api/upload' and method=='POST':
                inp=self.payload(19_000_000);raw=base64.b64decode(str(inp.get('data','')).split(',')[-1],validate=True)
                if not raw or len(raw)>12_000_000:raise StudioError('Arquivo vazio ou maior que 12 MB')
                typ=inp.get('kind','image')
                if typ=='image':
                    with Image.open(io.BytesIO(raw)) as im:
                        im=ImageOps.exif_transpose(im).convert('RGB');im.thumbnail((1920,1920))
                        fn=image_alias(inp.get('preferred_name')) if inp.get('preferred_name') else uuid.uuid4().hex[:12]+'.jpg'
                        with (MEDIA/fn).open('xb') as target:im.save(target,'JPEG',quality=90)
                elif typ in ('audio','video'):
                    ext=Path(str(inp.get('filename','audio.mp3'))).suffix.lower()
                    fn=store_media_bytes(raw,typ,ext)

                else:raise StudioError('Tipo de mídia inválido')
                return self.response(200,{'filename':fn})
            if route.startswith('/api/output/') and method=='GET':
                fname=route.split('/')[-1]
                if not re.fullmatch('[a-zA-Z0-9_.-]+',fname):raise StudioError('Nome de arquivo inválido')
                f=OUTPUT/fname
                if not f.is_file():return self.response(404,{'error':'Arquivo não encontrado'})
                content='video/mp4' if fname.endswith('.mp4') else ('audio/wav' if fname.endswith('.wav') else ('audio/mpeg' if fname.endswith('.mp3') else ('audio/ogg' if fname.endswith('.opus') else ('application/zip' if fname.endswith('.zip') else ('text/html; charset=utf-8' if fname.endswith('.html') else 'text/plain')))))
                self.send_response(200);self.send_header('Content-Type',content)
                self.send_header('Content-Length',str(f.stat().st_size));self.send_header('Content-Disposition',f'attachment; filename="{fname}"')
                self.end_headers()
                with f.open('rb') as inp:shutil.copyfileobj(inp,self.wfile,256*1024)
                return
            return self.response(404,{'error':'Rota não encontrada'})
        except (ValueError,TypeError,StudioError,OfflineError,KeyError,OverflowError,binascii.Error,json.JSONDecodeError,zipfile.BadZipFile,UnicodeError) as e:
            return self.response(400,{'error':str(e)})
        except Exception as e:
            traceback.print_exc();return self.response(500,{'error':'Erro interno: '+str(e)})
    def do_POST(self):self.route('POST')
    def do_GET(self):
        if self.path.startswith('/api/'):return self.route('GET')
        r=urlsplit(self.path).path
        if r in ('/gil-native.mjs','/scene-objects.mjs','/instance-manager-v1.mjs','/instance-graph-v1.mjs','/scene-object-editor.mjs','/browser-render.mjs','/viewport-affine.mjs','/platform-capabilities.mjs','/viewport-gizmo.mjs','/visual-effects.mjs','/title-gallery.mjs','/title-gil.mjs','/roteiro-v02.mjs','/roteiro-styles.mjs','/roteiro-editor.mjs','/roteiro-plan-v03.mjs','/roteiro-catalog-v04.mjs','/roteiro-project-v04.mjs','/roteiro-v04-ui.mjs','/studio-m1p.mjs','/voice-bulk.mjs','/subtitle-frame.mjs','/offline-render.mjs','/object-crop.mjs','/svg-direct-edit.mjs','/studio-command-registry-v1.mjs','/studio-console-v1.mjs'):
            return self.response(200,(ROOT/'web'/r[1:]).read_bytes(),'text/javascript; charset=utf-8')
        if r.startswith('/gil-runtime/'):
            from gil_runtime_paths import MODULES
            rel=r[len('/gil-runtime/'):]; configured=os.environ.get('RD_GIL_ROOT')
            if rel not in MODULES or not configured:return self.response(404,'Runtime GIL não disponível','text/plain')
            base=Path(configured).resolve(); f=(base/rel).resolve()
            if not f.is_relative_to(base) or not f.is_file() or f.stat().st_size>2_000_000:return self.response(404,'Módulo GIL indisponível','text/plain')
            return self.response(200,f.read_bytes(),'text/javascript; charset=utf-8')
        if r.startswith('/vendor/svgedit/'):
            vendor=(ROOT/'web'/'vendor'/'svgedit').resolve()
            f=(vendor/r[len('/vendor/svgedit/'):]).resolve()
            if not f.is_relative_to(vendor) or not f.is_file():return self.response(404,'Arquivo do SVG-Edit não disponível','text/plain')
            if f.stat().st_size>20_000_000:return self.response(413,'Arquivo muito grande','text/plain')
            ctype=mimetypes.guess_type(str(f))[0] or 'application/octet-stream'
            if ctype in ('text/javascript','application/javascript'):ctype='text/javascript'
            self.send_response(200)
            self.send_header('Content-Type',ctype)
            self.send_header('Content-Length',str(f.stat().st_size))
            self.send_header('Cache-Control','public, max-age=86400')
            self.send_header('X-Content-Type-Options','nosniff')
            self.end_headers()
            with f.open('rb') as inp:shutil.copyfileobj(inp,self.wfile,128*1024)
            return
        filemap={'/':'index.html','/index.html':'index.html','/app.js':'app.js','/image-composer.js':'image-composer.js','/media-recorder.js':'media-recorder.js','/style.css':'style.css', '/captura':'captura.html','/captura.html':'captura.html','/captura.js':'captura.js','/captura-record.js':'captura-record.js','/espacial':'espacial.html','/espacial.html':'espacial.html','/espacial.js':'espacial.js','/espacial.css':'espacial.css','/vetor':'vetor.html','/vetor.html':'vetor.html','/vetor.js':'vetor.js','/vetor.css':'vetor.css','/vetor-classico':'vetor-classico.html','/vetor-classico.html':'vetor-classico.html','/vetor-classico.js':'vetor-classico.js','/vetor-classico.css':'vetor-classico.css'}
        filemap['/media-recorder-v35.js']='media-recorder-v35.js'
        filemap['/layers-v36.js']='layers-v36.js'
        filemap['/timing-v37.js']='timing-v37.js'
        filemap['/workspace-v38.js']='workspace-v38.js'
        filemap['/edit-history.js']='edit-history.js'
        filemap['/media-start-gate.js']='media-start-gate.js'
        filemap['/studio-layout-v1.js']='studio-layout-v1.js'
        filemap['/studio-layout-v1.css']='studio-layout-v1.css'
        # Explicit allowlist: never serve arbitrary repository files.
        player_files={'/player-v3/':'index.html','/player-v3/index.html':'index.html',
          '/player-v3/player.js':'player.js','/player-v3/runtime.js':'runtime.js',
          '/player-v3/media_layer.js':'media_layer.js','/player-v3/v34/voice_locale.js':'v34/voice_locale.js'}
        if r in player_files:
            fn=ROOT/'web_player'/'v3'/player_files[r]
            mime='text/javascript; charset=utf-8' if fn.suffix=='.js' else 'text/html; charset=utf-8'
            return self.response(200,fn.read_bytes(),mime)
        if r not in filemap:return self.response(404,'Não encontrado','text/plain')
        fn=ROOT/'web'/filemap[r];mime=('.js' if r.endswith('js') else '.css' if r.endswith('css') else '.html')
        types={'.html':'text/html; charset=utf-8','.css':'text/css; charset=utf-8','.js':'text/javascript; charset=utf-8'}
        return self.response(200,fn.read_bytes(),types[mime])
    def do_HEAD(self):
        # Media clients may probe length before requesting byte ranges.
        if urlsplit(self.path).path in ('/api/media/clip','/api/player-v3/voice','/api/scene/media','/api/browser-render/mix'):
            return self.route('GET')
        self.send_response(200);self.send_header('Content-Length','0');self.end_headers()


def migrate(old):
    old=Path(old).expanduser()
    if not old.is_dir():raise StudioError('Pasta de origem não existe: '+str(old))
    count=0
    for f in (old/'projetos').glob('*.json'):
        if not re.fullmatch('[A-Za-z0-9_-]{1,64}',f.stem):continue
        try:pr=normalize(json.loads(f.read_text(encoding='utf8')))
        except (ValueError,TypeError) as e:print('Ignorando',f.name,':',e);continue
        dest=project_path(f.stem)
        if dest.exists():continue
        save_project(f.stem,pr);count+=1
    for src in (old/'midia').glob('*'):
        if src.is_file() and re.fullmatch('[A-Za-z0-9_.-]+',src.name):
            if not (MEDIA/src.name).exists():shutil.copy2(src,MEDIA/src.name)
    print(f'Migração concluída: {count} projetos novos, mídias copiadas sem sobrescrever.')

def cli():
    p=argparse.ArgumentParser(description='Estúdio SVG V3 experimental para Termux')
    p.add_argument('acao',nargs='?',default='servir',choices=['servir','verificar','quadros','audio','mix','render','render-leve','cena','cache-status','cache-clear','migrar'])
    p.add_argument('--projeto',default='demo_organico');p.add_argument('--port',type=int,default=8771)
    p.add_argument('--scene',type=int);p.add_argument('--sem-voz',action='store_true')
    p.add_argument('--origem',default=str(Path.home()/'estudio_svg_v2'))
    args=p.parse_args()
    if args.acao=='verificar':
        print('Estúdio SVG',VERSION,'\nPython:',sys.version.split()[0],'\nPasta:',ROOT)
        for x in ['ffmpeg','ffprobe','edge-tts','espeak-ng','piper','termux-tts-speak','magick','convert']:
            print(x+':',shutil.which(x) or 'não encontrado')
        print('Projetos:',*[f.stem for f in PROJECTS.glob('*.json')])
    elif args.acao=='migrar':migrate(args.origem)
    elif args.acao=='servir':
        # O contexto fecha explicitamente o socket também no Ctrl+C.
        with ThreadingHTTPServer(('127.0.0.1',args.port),Handler) as server:
            print('Estúdio SVG V3 alpha: http://127.0.0.1:'+str(args.port),flush=True)
            try:
                server.serve_forever()
            except KeyboardInterrupt:
                print('\nServidor encerrado (Ctrl+C)',flush=True)
    elif args.acao=='cache-status':
        for x in cache_status(read_project(args.projeto)):
            print(f"{x['index']:02d} {x['title'][:35]:35} | visual={x['visual']} audio={x['audio']} voz={x['voice']} {x['seconds']:.2f}s")
    elif args.acao=='cache-clear':
        if not args.scene:raise SystemExit('Informe --scene N')
        clear_scene_cache(read_project(args.projeto),args.scene);print('Cache da cena limpo (voz preservada)')
    else:
        modes={'quadros':'quadros','audio':'audio','mix':'mix','render':'render','render-leve':'render','cena':'render'}
        mode=modes[args.acao]
        if args.acao=='cena' and not args.scene:raise SystemExit('Informe --scene N')
        def progress(n,msg):print(f'{n*100:5.1f}%  {msg}',flush=True)
        pr=read_project(args.projeto)
        project_name=args.projeto
        if args.acao=='render-leve':
            from studio_core import economy_config
            pr=economy_config(pr); project_name += '_leve'
        output=project_render(project_name,pr,progress,mode,
                             args.scene if args.acao=='cena' else None,args.sem_voz)
        for k,v in output.items():print(k+':',v)

if __name__=='__main__':cli()
