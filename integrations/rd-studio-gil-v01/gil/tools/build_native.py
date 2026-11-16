#!/usr/bin/env python3
"""Use the same relative-module bundling method as build_player.py."""
from pathlib import Path
import re,base64
ROOT=Path(__file__).resolve().parents[1]
cache={}
def data(mime,b):return 'data:'+mime+';base64,'+base64.b64encode(b).decode('ascii')
def module(p):
    p=p.resolve()
    if p in cache:return cache[p]
    if not p.is_relative_to(ROOT):raise ValueError('module outside source')
    s=p.read_text('utf8')
    if p.name=='render-svg.mjs':
        for n in ('helix.svg','snowflake.svg'):s=s.replace("'assets/"+n+"'","'"+data('image/svg+xml',(ROOT/'assets'/n).read_bytes())+"'")
    s=re.sub(r'(\bfrom\s+)(["\'])(\.{1,2}/[^"\']+)\2',lambda m:m[1]+m[2]+module(p.parent/m[3].split('?')[0])+m[2],s)
    cache[p]=data('text/javascript',s.encode());return cache[p]
if __name__=='__main__':
    (ROOT/'native-template.js').write_text('import {defineNative} from "'+module(ROOT/'src/native-element.mjs')+'";\ndefineNative("__GIL_TAG__",new TextDecoder().decode(Uint8Array.from(atob("__GIL_SOURCE__"),x=>x.charCodeAt(0))));\n',encoding='utf8')
