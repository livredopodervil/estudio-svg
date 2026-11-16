#!/usr/bin/env python3
"""Loopback-only GIL authoring service. No Git, arbitrary paths, or admin token.
One bounded temporary render at a time. Published players use no such API.
"""
import argparse, hashlib, json, os, re, secrets, signal, subprocess, sys, tempfile, threading, time
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit, unquote
ROOT=Path(__file__).resolve().parents[1]
class RenderState:
    def __init__(self,root,timeout=900):
        self.root=Path(root);self.timeout=timeout;self.lock=threading.RLock();self.job=None;self.proc=None;self.closed=False;self.worker=None
    def submit(self,data):
        if not isinstance(data,dict) or set(data)-{'source','fps','long_side','duration','silent'}:raise ValueError('Parâmetros inválidos')
        source=data.get('source');fps=data.get('fps',24);side=data.get('long_side',960);duration=data.get('duration');silent=data.get('silent',False)
        if not isinstance(source,str) or not 0<len(source.encode())<=250000 or type(fps)!=int or not 12<=fps<=30 or type(side)!=int or not 320<=side<=1280 or type(duration) not in (int,float) or not .1<=duration<=120 or duration*fps>1800 or type(silent)!=bool:raise ValueError('Limites: fonte 250 kB, 12–30 fps, 320–1280 px, até 120 s e 1800 quadros')
        with self.lock:
            if self.closed or self.job and self.job['status']=='running':raise RuntimeError('Renderização em andamento')
            # Private temp directory: no use of user-supplied filenames.
            import shutil
            if self.job:shutil.rmtree(self.root/self.job['id'],ignore_errors=True)
            jid=secrets.token_hex(12);d=self.root/jid;d.mkdir(mode=0o700);(d/'source.gil').write_text(source,encoding='utf-8')
            self.job={'id':jid,'status':'running','source_sha256':hashlib.sha256(source.encode()).hexdigest(),'duration':duration,'fps':fps,'long_side':side,'message':'Preparando exportação'}
            args=[sys.executable,str(ROOT/'tools/export_mp4.py'),str(d/'source.gil'),str(d/'video.mp4'),'--fps',str(fps),'--long-side',str(side),'--duration',str(duration)]
            if silent:args.append('--silent')
            self.worker=threading.Thread(target=self._run,args=(jid,args),daemon=True);self.worker.start();return dict(self.job)
    def _run(self,jid,args):
        d=self.root/jid;log=d/'render.log'
        try:
            with log.open('wb') as f:
                with self.lock:
                    if self.closed:raise RuntimeError('Serviço encerrado')
                    self.proc=subprocess.Popen(args,stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
                    proc=self.proc
                try:code=proc.wait(timeout=self.timeout)
                except subprocess.TimeoutExpired:
                    self._kill(proc);proc.wait();raise RuntimeError('Limite de tempo de renderização atingido')
            if code or not (d/'video.mp4').is_file():raise RuntimeError('Exportador falhou; confira Node, FFmpeg e rasterizador. '+log.read_text(errors='replace')[-1400:])
            result={'status':'done','message':'MP4 pronto','bytes':(d/'video.mp4').stat().st_size}
        except Exception as e:result={'status':'error','message':str(e)[:1600]}
        with self.lock:
            self.proc=None
            if self.job and self.job['id']==jid:self.job.update(result)
    @staticmethod
    def _kill(proc):
        if proc and proc.poll() is None:
            try:os.killpg(proc.pid,signal.SIGKILL)
            except ProcessLookupError:pass
    def status(self):
        with self.lock:return dict(self.job) if self.job else None
    def close(self):
        with self.lock:self.closed=True;self._kill(self.proc)
        if self.worker:self.worker.join(timeout=10)
class Server(ThreadingHTTPServer):
    daemon_threads=True
    def __init__(self,address,state):
        self.state=state;self.token=secrets.token_urlsafe(32);super().__init__(address,Handler)
    @property
    def origin(self):return f'http://127.0.0.1:{self.server_port}'
class Handler(SimpleHTTPRequestHandler):
    def __init__(self,*args,**kwargs):super().__init__(*args,directory=str(ROOT),**kwargs)
    def end_headers(self):
        self.send_header('X-Content-Type-Options','nosniff');self.send_header('Cross-Origin-Resource-Policy','same-origin');self.send_header('Cache-Control','no-store');self.send_header('X-Frame-Options','DENY');super().end_headers()
    def safe(self):
        if self.headers.get('Host')!=self.server.origin.removeprefix('http://') or self.headers.get('Sec-Fetch-Site')=='cross-site':self.send_error(403);return False
        return True
    def reply(self,obj,code=200):
        b=json.dumps(obj,ensure_ascii=False).encode();self.send_response(code);self.send_header('Content-Type','application/json; charset=utf-8');self.send_header('Content-Length',str(len(b)));self.end_headers()
        if self.command!='HEAD':self.wfile.write(b)
    def static_allowed(self,path):
        p=unquote(path);parts=Path(p.lstrip('/')).parts
        if p=='/':return True
        if not parts or any(x.startswith('.') for x in parts):return False
        if len(parts)==1:return parts[0] in ('index.html','style.css','player-template.html')
        allowed={'src':{'.mjs'},'vendor':{'.js','.mjs','.json'},'assets':{'.svg'},'examples':{'.gil','.json','.md'}}
        target=ROOT.joinpath(*parts)
        return parts[0] in allowed and target.suffix in allowed[parts[0]] and target.is_file() and target.resolve().is_relative_to(ROOT) and not any(q.is_symlink() for q in [target,*target.parents] if q.is_relative_to(ROOT))
    def do_GET(self):self.read_route()
    def do_HEAD(self):self.read_route()
    def read_route(self):
        if not self.safe():return
        u=urlsplit(self.path)
        if u.path=='/api/session':return self.reply({'token':self.server.token,'job':self.server.state.status()})
        if u.path=='/api/render':return self.reply({'job':self.server.state.status()})
        m=re.fullmatch(r'/api/video/([a-f0-9]{24})\.mp4',u.path)
        if m:return self.video(m[1],u.query=='download=1')
        if not self.static_allowed(u.path):self.send_error(404);return
        if self.command=='HEAD':super().do_HEAD()
        else:super().do_GET()
    def do_POST(self):
        if not self.safe():return
        if self.path!='/api/render':self.send_error(404);return
        if self.headers.get('Origin')!=self.server.origin or not secrets.compare_digest(self.headers.get('X-GIL-Token',''),self.server.token):self.send_error(403);return
        try:
            n=int(self.headers.get('Content-Length','0'))
            if not 0<n<=300000 or self.headers.get_content_type()!='application/json':raise ValueError('Requisição inválida ou excessiva')
            data=json.loads(self.rfile.read(n));job=self.server.state.submit(data);self.reply({'job':job},202)
        except (ValueError,TypeError) as e:self.reply({'error':str(e)},400)
        except RuntimeError as e:self.reply({'error':str(e)},409)
    def video(self,jid,download):
        state=self.server.state
        # Open under lock, so a replacement cannot delete before open.
        with state.lock:
            job=state.status()
            if not job or job['id']!=jid or job['status']!='done':self.send_error(404);return
            f=(state.root/jid/'video.mp4').open('rb')
        with f:
            size=os.fstat(f.fileno()).st_size;start=0;end=size-1;status=200;range_value=self.headers.get('Range')
            if range_value:
                m=re.fullmatch(r'bytes=(\d*)-(\d*)',range_value)
                if m and (m[1] or m[2]):
                    if m[1]:start=int(m[1]);end=min(end,int(m[2])) if m[2] else end
                    else:start=max(0,size-int(m[2]))
                    status=206
                if status!=206 or not 0<=start<=end<size:
                    self.send_response(416);self.send_header('Content-Range',f'bytes */{size}');self.send_header('Content-Length','0');self.end_headers();return
            self.send_response(status);self.send_header('Content-Type','video/mp4');self.send_header('Accept-Ranges','bytes');self.send_header('Content-Length',str(end-start+1))
            if status==206:self.send_header('Content-Range',f'bytes {start}-{end}/{size}')
            if download:self.send_header('Content-Disposition',f'attachment; filename="gil-{jid[:12]}.mp4"')
            self.end_headers()
            if self.command=='HEAD':return
            f.seek(start);remaining=end-start+1
            try:
                while remaining:
                    b=f.read(min(65536,remaining))
                    if not b:break
                    self.wfile.write(b);remaining-=len(b)
            except (BrokenPipeError,ConnectionResetError):pass
    def log_message(self,fmt,*args):pass # never log source or session token

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--port',type=int,default=8791);a=p.parse_args()
    with tempfile.TemporaryDirectory(prefix='gil-jobs-') as d:
        state=RenderState(d)
        with Server(('127.0.0.1',a.port),state) as server:
            def stop(sig,frame):raise KeyboardInterrupt
            signal.signal(signal.SIGTERM,stop)
            print('GIL autoria e render: '+server.origin,flush=True)
            try:server.serve_forever()
            except KeyboardInterrupt:pass
            finally:state.close()
if __name__=='__main__':main()
