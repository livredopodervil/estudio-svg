#!/usr/bin/env python3
"""Estúdio SVG V2.7: editor de imagens e apresentação vetorial."""
from __future__ import annotations
import argparse, base64, io, json, mimetypes, os, re, shutil, subprocess, sys, threading, time, traceback, uuid, hashlib
from http.server import ThreadingHTTPServer,BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs,urlsplit
from PIL import Image, ImageOps
from schema import VERSION, normalize,default_project,name,asset
from studio_core import (StudioError,ROOT,PROJECTS,MEDIA,CACHE,OUTPUT,project_render,cache_status,
                         clear_scene_cache,duration,scene_cached_media,scene_preview)
from graphics import visualize
from svg_graphic import clean_svg

JOBS={};JOB_LOCK=threading.RLock();ENGINE_LOCK=threading.Lock();PREVIEW_LOCK=threading.Lock();SVG_LOCK=threading.RLock()

def project_path(project):return PROJECTS/(name(project)+'.json')
def read_project(project):
    p=project_path(project)
    if not p.is_file():raise StudioError('Projeto não encontrado: '+project)
    return normalize(json.loads(p.read_text(encoding='utf8')))
def save_project(project,data):
    p=project_path(project);valid=normalize(data)
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
            res=project_render(actual_name,pr,progress,actual_mode,scene,no_voice)
            with JOB_LOCK:job.update(status='done',phase='Concluído',progress=1,result=res)
        except Exception as e:
            log_job(job,'ERRO: '+str(e));traceback.print_exc()
            with JOB_LOCK:job.update(status='error',phase='Erro',error=str(e))

def queue_job(project,mode,scene=None,no_voice=False):
    name(project);read_project(project)
    if mode not in ('quadros','audio','mix','render','render-leve','cena'):raise StudioError('Modo inválido')
    if mode=='cena':
        try:scene=int(scene)
        except (ValueError,TypeError):raise StudioError('Informe o número da cena')
    else:scene=None
    with JOB_LOCK:
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

class Handler(BaseHTTPRequestHandler):
    server_version='EstudioSVG/2.6'
    def log_message(self,fmt,*args):print('HTTP: '+fmt%args,flush=True)
    def response(self,status,data,mime='application/json; charset=utf-8'):
        if isinstance(data,(dict,list)):data=json.dumps(data,ensure_ascii=False).encode('utf8')
        elif isinstance(data,str):data=data.encode('utf8')
        self.send_response(status)
        for k,v in [('Content-Type',mime),('Content-Length',str(len(data))),('Cache-Control','no-store'),
                    ('X-Content-Type-Options','nosniff')]:self.send_header(k,v)
        self.end_headers();self.wfile.write(data)
    def stream_file(self,path):
        f=Path(path)
        if not f.is_file():return self.response(404,{'error':'Mídia ainda não disponível'})
        ext=f.suffix.lower();ctype={'.mp4':'video/mp4','.mp3':'audio/mpeg','.wav':'audio/wav',
          '.m4a':'audio/mp4','.ogg':'audio/ogg','.flac':'audio/flac','.aac':'audio/aac',
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
        self.end_headers()
        try:
            with f.open('rb') as inp:
                inp.seek(start);left=end-start+1
                while left>0:
                    data=inp.read(min(128*1024,left))
                    if not data:break
                    self.wfile.write(data);left-=len(data)
        except (BrokenPipeError,ConnectionResetError):pass

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
            if route=='/api/presentation' and method=='GET':
                project=read_project(q('name'))
                from studio_core import scene_length,voice_source
                d=[]
                for scene in project['cenas']:
                    v=voice_source(scene,project,required=False)
                    d.append(scene_length(scene,project,voice=bool(v)))
                from studio_core import digest,audio_key
                current=[]
                for c,secs in zip(project['cenas'],d):
                    v=voice_source(c,project,required=False)
                    current.append(audio_key(c,project,secs,v))
                sig=digest(['mix24',current])
                f=OUTPUT/(q('name')+'_mix.wav');meta=OUTPUT/(q('name')+'_mix.json')
                ready=False
                if f.is_file() and meta.is_file() and f.stat().st_size>44:
                    try:ready=json.loads(meta.read_text()).get('signature')==sig
                    except (ValueError,OSError):pass
                return self.response(200,{'project':project,'durations':d,'mix_ready':ready})
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
                return self.response(200,{'svg':svg,'revision':revision,'title':scene['titulo'],
                   'project':q('name'),'scene':idx+1})
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
            if route=='/api/project/validate' and method=='POST':
                # Validation is read-only: no project file is created or overwritten.
                data=self.payload(6_000_000)
                return self.response(200,{'ok':True,'project':normalize(data.get('project'))})
            if route=='/api/projects' and method=='GET':return self.response(200,{'projects':[p.stem for p in sorted(PROJECTS.glob('*.json'))]})
            if route=='/api/project' and method=='GET':return self.response(200,{'name':q('name','demo_organico'),'project':read_project(q('name','demo_organico'))})
            if route=='/api/project' and method=='POST':
                data=self.payload(6_000_000);pr=save_project(data.get('name',''),data.get('project'))
                return self.response(200,{'ok':True,'cenas':len(pr['cenas'])})
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
            if route=='/api/scene/media' and method=='GET':
                pr=read_project(q('name'));idx=int(q('scene','1'))-1
                kind=q('kind','voice')
                if kind not in ('voice','audio','visual','poster','image','music','voice_file'):
                    raise StudioError('Tipo de áudio/vídeo inválido')
                path=scene_cached_media(pr,idx,kind)
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
            if route=='/api/upload' and method=='POST':
                inp=self.payload(19_000_000);raw=base64.b64decode(str(inp.get('data','')).split(',')[-1],validate=True)
                if not raw or len(raw)>12_000_000:raise StudioError('Arquivo vazio ou maior que 12 MB')
                typ=inp.get('kind','image')
                if typ=='image':
                    with Image.open(io.BytesIO(raw)) as im:
                        im=ImageOps.exif_transpose(im).convert('RGB');im.thumbnail((1920,1920))
                        fn=uuid.uuid4().hex[:12]+'.jpg';im.save(MEDIA/fn,'JPEG',quality=90)
                elif typ=='audio':
                    ext=Path(str(inp.get('filename','audio.mp3'))).suffix.lower()
                    if ext not in ('.mp3','.wav','.m4a','.ogg','.flac','.aac'):raise StudioError('Áudio: MP3, WAV, M4A, OGG, FLAC ou AAC')
                    fn=uuid.uuid4().hex[:12]+ext;f=MEDIA/fn;f.write_bytes(raw)
                    if duration(f)<=0:f.unlink(missing_ok=True);raise StudioError('Áudio não reconhecido pelo FFprobe')
                else:raise StudioError('Tipo de mídia inválido')
                return self.response(200,{'filename':fn})
            if route.startswith('/api/output/') and method=='GET':
                fname=route.split('/')[-1]
                if not re.fullmatch('[a-zA-Z0-9_.-]+',fname):raise StudioError('Nome de arquivo inválido')
                f=OUTPUT/fname
                if not f.is_file():return self.response(404,{'error':'Arquivo não encontrado'})
                content='video/mp4' if fname.endswith('.mp4') else ('audio/wav' if fname.endswith('.wav') else ('application/zip' if fname.endswith('.zip') else 'text/plain'))
                self.send_response(200);self.send_header('Content-Type',content)
                self.send_header('Content-Length',str(f.stat().st_size));self.send_header('Content-Disposition',f'attachment; filename="{fname}"')
                self.end_headers()
                with f.open('rb') as inp:shutil.copyfileobj(inp,self.wfile,256*1024)
                return
            return self.response(404,{'error':'Rota não encontrada'})
        except (ValueError,TypeError,StudioError,KeyError,OverflowError,json.JSONDecodeError) as e:
            return self.response(400,{'error':str(e)})
        except Exception as e:
            traceback.print_exc();return self.response(500,{'error':'Erro interno: '+str(e)})
    def do_POST(self):self.route('POST')
    def do_GET(self):
        if self.path.startswith('/api/'):return self.route('GET')
        r=urlsplit(self.path).path
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
        filemap={'/':'index.html','/index.html':'index.html','/app.js':'app.js','/image-composer.js':'image-composer.js','/style.css':'style.css', '/captura':'captura.html','/captura.html':'captura.html','/captura.js':'captura.js','/vetor':'vetor.html','/vetor.html':'vetor.html','/vetor.js':'vetor.js','/vetor.css':'vetor.css','/vetor-classico':'vetor-classico.html','/vetor-classico.html':'vetor-classico.html','/vetor-classico.js':'vetor-classico.js','/vetor-classico.css':'vetor-classico.css'}
        if r not in filemap:return self.response(404,'Não encontrado','text/plain')
        fn=ROOT/'web'/filemap[r];mime=('.js' if r.endswith('js') else '.css' if r.endswith('css') else '.html')
        types={'.html':'text/html; charset=utf-8','.css':'text/css; charset=utf-8','.js':'text/javascript; charset=utf-8'}
        return self.response(200,fn.read_bytes(),types[mime])
    def do_HEAD(self):
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
    p=argparse.ArgumentParser(description='Estúdio SVG V2.7 para Termux')
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
        print('Estúdio SVG V2.7: http://127.0.0.1:'+str(args.port),flush=True)
        server=ThreadingHTTPServer(('127.0.0.1',args.port),Handler)
        try:server.serve_forever()
        except KeyboardInterrupt:print('\nServidor encerrado')
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
