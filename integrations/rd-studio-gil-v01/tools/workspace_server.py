#!/usr/bin/env python3
"""Loopback workspace. No proxy, no privileged API; SpatialSeed in separate origin."""
import argparse,json,mimetypes,signal,threading
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer,SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlsplit,unquote
ROOT=Path(__file__).resolve().parents[1]
PARENT='http://127.0.0.1:8877'
PUBLIC={'apps','packages','vendor','assets','core','engine','modules','objects','regions','renderers','worlds','examples'}
SUFFIX={'.js','.mjs','.css','.html','.json','.svg','.png','.jpg','.jpeg','.webp','.gif','.ico','.woff','.woff2','.ttf','.wasm','.glb','.gltf','.bin','.mp3','.ogg','.wav','.webmanifest'}
def spatial_available(root):
    return bool(root and all((root/p).is_file() for p in ['apps/web/index.html','vendor/three.module.js','packages/instance-graph/src/InstanceGraph.js']))
class Shell(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.headers.get('Host')!='127.0.0.1:8877':return self.send_error(403)
        key=urlsplit(self.path).path
        if key=='/config.json':data=json.dumps(self.server.config).encode();mime='application/json'
        elif key in ('/','/workspace.js','/workspace.css'):
            file=ROOT/'workspace'/('index.html' if key=='/' else key[1:]);data=file.read_bytes();mime=mimetypes.guess_type(str(file))[0] or 'text/plain'
        else:return self.send_error(404)
        self.send_response(200);self.send_header('Content-Type',mime+'; charset=utf-8');self.send_header('Content-Length',str(len(data)));self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff');self.send_header('X-Frame-Options','DENY');self.send_header('Referrer-Policy','no-referrer');self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self'; frame-src http://127.0.0.1:8791 http://127.0.0.1:8784 http://127.0.0.1:8875 http://127.0.0.1:8792; frame-ancestors 'none'; object-src 'none'; base-uri 'none'");self.end_headers();self.wfile.write(data)
class Spatial(SimpleHTTPRequestHandler):
    def __init__(self,*a,**kw):super().__init__(*a,directory=str(self.server.root) if hasattr(self,'server') else str(self.root),**kw)
    def allowed(self):
        if self.headers.get('Host')!='127.0.0.1:8792':return False
        parts=unquote(urlsplit(self.path).path).strip('/').split('/')
        if any(not x or x.startswith('.') or x in {'node_modules','tests','__pycache__'} or '\\' in x for x in parts):return False
        if parts[0] not in PUBLIC:return False
        if parts[0]=='apps' and (len(parts)<2 or parts[1]!='web'):return False
        p=self.root.joinpath(*parts)
        if p.is_dir():p=p/'index.html'
        return p.suffix.lower() in SUFFIX and p.is_file() and p.resolve().is_relative_to(self.root) and not any(x.is_symlink() for x in [p,*p.parents] if x.is_relative_to(self.root))
    def do_GET(self):
        if self.allowed():super().do_GET()
        else:self.send_error(404)
    def do_HEAD(self):
        if self.allowed():super().do_HEAD()
        else:self.send_error(404)
    def list_directory(self,path):self.send_error(403);return None
    def end_headers(self):
        self.send_header('Content-Security-Policy',f'frame-ancestors {PARENT}');self.send_header('X-Content-Type-Options','nosniff');self.send_header('Cache-Control','no-store');super().end_headers()
def main():
    p=argparse.ArgumentParser();p.add_argument('--video',action='store_true');p.add_argument('--spatial',type=Path);a=p.parse_args();root=a.spatial.resolve() if a.spatial else None
    has=spatial_available(root);sp=None
    with ThreadingHTTPServer(('127.0.0.1',8877),Shell) as http:
        http.config={'site':True,'gil':True,'video':a.video,'spatial':has}
        if has:
            sp=ThreadingHTTPServer(('127.0.0.1',8792),type('SpatialBound',(Spatial,),{'root':root}));threading.Thread(target=sp.serve_forever,daemon=True).start()
        elif root:print('SpatialSeed nativo não iniciado: vendor/three.module.js ou entrada ausente. Nenhuma dependência instalada.',flush=True)
        print('Workspace: '+PARENT+'/',flush=True)
        try:http.serve_forever()
        except KeyboardInterrupt:pass
        finally:
            if sp:sp.shutdown();sp.server_close()
if __name__=='__main__':main()
