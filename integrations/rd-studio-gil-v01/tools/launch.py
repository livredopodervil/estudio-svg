#!/usr/bin/env python3
"""Run the three independent local services. Never kill processes not created here."""
from pathlib import Path
import argparse,subprocess,sys,socket,time,signal,os
root=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--site',required=True,type=Path);p.add_argument('--video',type=Path);p.add_argument('--spatial',type=Path);a=p.parse_args();site=a.site.expanduser().resolve();video=a.video.expanduser().resolve() if a.video else None
if not (site/'index.html').is_file():sys.exit('Site inexistente ou sem index.html')
if video and not (video/'app.py').is_file():sys.exit('Estúdio SVG não localizado')
spatial=a.spatial.expanduser().resolve() if a.spatial else None
if spatial and not (spatial/'packages/instance-graph/src/InstanceGraph.js').is_file():sys.exit('SpatialSeed não localizado ou contrato incompatível')
from workspace_server import spatial_available
ports=[8875,8876,8791,8877]+([8784] if video else [])+([8792] if spatial_available(spatial) else [])
for port in ports:
    with socket.socket() as s:
        try:s.bind(('127.0.0.1',port))
        except OSError:sys.exit(f'Porta {port} ocupada; encerre a instância anterior de forma normal.')
children=[]
def start(args,cwd,env=None):
    child=subprocess.Popen([sys.executable,*args],cwd=cwd,start_new_session=True,env=env);children.append(child)
try:
    env={**os.environ,'RD_GIL_ROOT':str(root/'gil'),'RD_WORKSPACE_PARENT':'http://127.0.0.1:8877'}
    start([str(root/'rdstudio/server.py'),'--repo',str(site),'--port','8875','--preview-port','8876'],root/'rdstudio',env)
    env.pop('RD_SPATIALSEED_ROOT',None)
    if spatial:env['RD_SPATIALSEED_ROOT']=str(spatial)
    start([str(root/'gil/tools/local_server.py'),'--port','8791'],root/'gil',env)
    if video:start(['app.py','servir','--port','8784'],video,env)
    start([str(root/'tools/workspace_server.py'),*(['--video'] if video else []),*(['--spatial',str(spatial)] if spatial else [])],root,env)
    print('ABRA NO CHROME: http://127.0.0.1:8877/\nCtrl+C encerra somente os serviços iniciados por este comando.',flush=True)
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
