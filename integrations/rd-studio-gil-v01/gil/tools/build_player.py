#!/usr/bin/env python3
"""Build an export template from pinned, relative ES modules. No untrusted code execution."""
from pathlib import Path
import base64,re,sys
ROOT=Path(__file__).resolve().parents[1]
cache={}
def data(mime,b):return 'data:'+mime+';base64,'+base64.b64encode(b).decode('ascii')
def module(p):
    p=p.resolve()
    if p in cache:return cache[p]
    if not p.is_relative_to(ROOT):raise ValueError('module outside source')
    s=p.read_text('utf-8')
    if p.name=='render-svg.mjs':
        for n in ('helix.svg','snowflake.svg'):
            s=s.replace("'assets/"+n+"'", "'"+data('image/svg+xml',(ROOT/'assets'/n).read_bytes())+"'")
    s=re.sub(r'(\bfrom\s+)([\"\'])(\.{1,2}/[^\"\']+)\2',lambda m:m[1]+m[2]+module(p.parent/m[3].split('?')[0])+m[2],s)
    cache[p]=data('text/javascript',s.encode());return cache[p]
html='''<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>GIL · Composição interativa</title><style>
*{box-sizing:border-box}body{margin:0;background:#0c1625;color:#dce9ef;font:14px system-ui,sans-serif;padding:10px}#stage{width:100%;background:#08142b;border-radius:9px;overflow:hidden;display:grid;place-items:center}#stage svg{width:100%;height:100%;display:block}nav{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin:10px 0}button{font:inherit;border:1px solid #4b7589;color:#e4f4f7;background:#203e52;border-radius:7px;padding:8px 13px;min-height:42px}button:disabled{opacity:.5}input[type=range]{width:100%;accent-color:#69c8cb}output,#status{font-size:12px;color:#a9c9d7}#clock{margin-left:auto}</style></head><body><div id="stage" aria-label="Composição interativa"></div><nav><button id="play">Reproduzir</button><button id="pause">Pausar</button><button id="reset">Início</button><label><input type="checkbox" id="sound" checked> Som</label><output id="clock"></output></nav><input id="seek" type="range" min="0" step="0.05" value="0" aria-label="Tempo"><p id="status" role="status">Carregando…</p><script type="text/plain" id="gil-source">__RD_GIL_SOURCE_B64__</script><script type="module">import "__RD_MODULE__";</script></body></html>'''
html=html.replace('__RD_MODULE__',module(ROOT/'src/player.mjs'))
p=Path(sys.argv[1]) if len(sys.argv)>1 else ROOT/'player-template.html'
p.write_text(html,encoding='utf-8');print(p,p.stat().st_size)
