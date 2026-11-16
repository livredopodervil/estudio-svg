#!/usr/bin/env python3
"""Run the three independent local services. Never kill processes not created here."""
from pathlib import Path
import argparse,subprocess,sys,socket,time,signal,os
root=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--site',required=True,type=Path);p.add_argument('--video',type=Path);a=p.parse_args();site=a.site.expanduser().resolve();video=a.video.expanduser().resolve() if a.video else None
if not (site/'index.html').is_file():sys.exit('Site inexistente ou sem index.html')
if video and not (video/'app.py').is_file():sys.exit('Estúdio SVG não localizado')
ports=[8875,8876,8791]+([8784] if video else [])
for port in ports:
    with socket.socket() as s:
        try:s.bind(('127.0.0.1',port))
        except OSError:sys.exit(f'Porta {port} ocupada; encerre a instância anterior de forma normal.')
children=[]
def start(args,cwd):
    child=subprocess.Popen([sys.executable,*args],cwd=cwd,start_new_session=True);children.append(child)
try:
    start([str(root/'rdstudio/server.py'),'--repo',str(site),'--port','8875','--preview-port','8876'],root/'rdstudio')
    start([str(root/'gil/tools/local_server.py'),'--port','8791'],root/'gil')
    if video:start(['app.py','servir','--port','8784'],video)
    print('RD Studio: http://127.0.0.1:8875/\nPrévia: http://127.0.0.1:8876/\nGIL: http://127.0.0.1:8791/\nEstúdio SVG: http://127.0.0.1:8784/ (se iniciado)\nCtrl+C encerra somente os serviços iniciados por este comando.',flush=True)
    while all(c.poll() is None for c in children):time.sleep(.5)
    sys.exit('Um serviço terminou; confira a saída acima.')
except KeyboardInterrupt:pass
finally:
    for c in children:
        if c.poll() is None:
            try:os.killpg(c.pid,signal.SIGTERM)
            except ProcessLookupError:pass
    for c in children:
        try:c.wait(timeout=5)
        except subprocess.TimeoutExpired:
            try:os.killpg(c.pid,signal.SIGKILL)
            except ProcessLookupError:pass
            c.wait()
