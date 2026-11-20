"""Rotas portáveis para o servidor HTTP EXISTENTE do Estúdio.

No BaseHTTPRequestHandler já existente, adicionar UMA chamada ao início de
`do_GET` e `do_POST`: `if rd_voices.api.try_handle(self): return`.
Não cria um segundo servidor ou porta. Não expõe a escuta a origens externas.
"""
from __future__ import annotations
import asyncio
from pathlib import Path
import json
import re
from urllib.parse import urlsplit
from .core import Catalog
from .edge_engine import synthesize_edge, CACHE_DIR

BASE = Path(__file__).resolve().parent
_FILE = re.compile(r'^/api/rd-voices/(audio|metadata)/([0-9a-f]{64})\.(mp3|json)$')
MAX_BODY = 48 * 1024


def _reply(h, status, payload: bytes, mime: str):
    h.send_response(status)
    h.send_header('Content-Type', mime)
    h.send_header('Cache-Control', 'no-store')
    h.send_header('X-Content-Type-Options', 'nosniff')
    h.send_header('Content-Length', str(len(payload)))
    h.end_headers()
    if getattr(h, 'command', '') != 'HEAD':
        h.wfile.write(payload)


def _json(h, status, obj):
    _reply(h, status, json.dumps(obj, ensure_ascii=False).encode('utf-8'),
           'application/json; charset=utf-8')


def _local(h):
    host = h.headers.get('Host', '').lower().split(':')[0].strip('[]')
    # Desenvolvimento no próprio Android. Evita que páginas remotas usem a API.
    if host not in ('localhost', '127.0.0.1', '::1'):
        return False
    origin = h.headers.get('Origin', '')
    if origin:
        from urllib.parse import urlparse
        parsed = urlparse(origin)
        if parsed.scheme not in ('http', 'https') or (parsed.hostname or '').lower() not in ('localhost', '127.0.0.1', '::1'):
            return False
    return True


def try_handle(h) -> bool:
    """True significa rota tratada. As outras rotas continuam intocadas."""
    path = urlsplit(h.path).path
    if not path.startswith('/api/rd-voices/'):
        return False
    try:
        method = getattr(h, 'command', 'GET')
        if path == '/api/rd-voices/installed' and method in ('GET','HEAD'):
            if not _local(h):
                _json(h,403,{'error':'catálogo somente no dispositivo local'});return True
            from .available_voices import installed_catalog
            _json(h,200,installed_catalog());return True
        if path == '/api/rd-voices/catalog' and method in ('GET', 'HEAD'):
            _json(h, 200, Catalog.load().normalized()); return True
        if path == '/api/rd-voices/controls.mjs' and method in ('GET', 'HEAD'):
            _reply(h, 200, (BASE / 'controls.mjs').read_bytes(), 'text/javascript; charset=utf-8'); return True
        if path == '/api/rd-voices/controls.css' and method in ('GET', 'HEAD'):
            _reply(h, 200, (BASE / 'controls.css').read_bytes(), 'text/css; charset=utf-8'); return True
        m = _FILE.fullmatch(path)
        if m and method in ('GET','HEAD'):
            kind, key, ext = m.groups()
            if (kind,ext) not in (('audio','mp3'),('metadata','json')):
                _json(h,404, {'error':'não encontrado'});return True
            f = CACHE_DIR / (key + '.' + ext)
            if not f.is_file():
                _json(h,404, {'error':'arquivo não encontrado'});return True
            _reply(h,200,f.read_bytes(),'audio/mpeg' if ext == 'mp3' else 'application/json; charset=utf-8')
            return True
        if path == '/api/rd-voices/refresh' and method == 'POST':
            if not _local(h):
                _json(h,403,{'error':'somente no dispositivo local'});return True
            try:
                _json(h,200,(asyncio.run(Catalog.refresh())).normalized())
            except Exception as err:
                _json(h,503,{'error':str(err)})
            return True
        if path == '/api/rd-voices/synthesize' and method == 'POST':
            if not _local(h):
                _json(h,403,{'error':'síntese permitida somente no dispositivo local'});return True
            try:
                n = int(h.headers.get('Content-Length','0'))
                if not (2 <= n <= MAX_BODY):
                    raise ValueError('Corpo JSON inválido ou grande demais')
                obj = json.loads(h.rfile.read(n))
                if not isinstance(obj,dict):
                    raise ValueError('Esperado objeto JSON')
                result = asyncio.run(synthesize_edge(obj))
                _json(h,200,result)
            except (ValueError,TypeError) as err:
                _json(h,400,{'error':str(err)})
            except Exception as err:
                _json(h,503,{'error':str(err)})
            return True
        _json(h,405 if method not in ('GET','POST','HEAD') else 404,{'error':'rota ou método não encontrado'})
        return True
    except (BrokenPipeError,ConnectionResetError):
        return True
