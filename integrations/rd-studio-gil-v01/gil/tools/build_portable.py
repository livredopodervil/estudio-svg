"""Empacota a demonstração autocontida: módulos e mídias em data URLs.
Os arquivos fonte e a execução HTTP continuam o caminho canônico de desenvolvimento.
"""
from pathlib import Path
import base64, re, sys
root=Path(__file__).resolve().parents[1]
cache={}
def data(mime, payload):
    return 'data:'+mime+';base64,'+base64.b64encode(payload).decode('ascii')
def module(path):
    path=path.resolve()
    if path in cache:return cache[path]
    assert path.is_relative_to(root)
    source=path.read_text('utf-8')
    if path.name=='ui.mjs':
        source=source.replace("fetch('examples/orbit.gil')", "fetch('"+data('text/plain',(root/'examples/orbit.gil').read_bytes())+"')")
    if path.name=='render-svg.mjs':
        for name in ('helix.svg','snowflake.svg'):
            source=source.replace("'assets/"+name+"'", "'"+data('image/svg+xml',(root/'assets'/name).read_bytes())+"'")
    def repl(m):
        prefix,quote,rel=m.groups()
        return prefix+quote+module(path.parent/rel.split('?')[0])+quote
    # As dependências versionadas deste snapshot usam imports/exports estáticos relativos.
    source=re.sub(r'(\bfrom\s+)([\"\'])(\.{1,2}/[^\"\']+)\2', repl, source)
    cache[path]=data('text/javascript',source.encode('utf-8'))
    return cache[path]
html=(root/'index.html').read_text('utf-8')
# The legacy portable authoring preview has no package composer (HTTP assets).
html=re.sub(r'<section class="panel source" id="publish-page">.*?</section>', '', html, flags=re.S)
html=re.sub(r'<div class="buttons" id="example-selector">.*?</div>', '', html, flags=re.S)
html=html.replace('<script type="module" src="src/page-ui.mjs"></script>', '')
html=html.replace('<link rel="stylesheet" href="style.css">','<style>'+(root/'style.css').read_text('utf-8')+'</style>')
html=html.replace('<script type="module" src="src/ui.mjs"></script>','<script type="module">import "'+module(root/'src/ui.mjs')+'";</script>')
out=Path(sys.argv[1]) if len(sys.argv)>1 else root/'gil_portatil.html'
with out.open('x',encoding='utf-8') as f:f.write(html)
print(out, out.stat().st_size)
