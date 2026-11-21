"""Read-only local RD Suite inventory; no credentials, actions or publication.

Never proxies arbitrary URLs. Probes fixed 127.0.0.1 endpoints and the
already-configured filesystem roots, without scanning media or worktrees.
"""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from urllib.request import Request, build_opener, ProxyHandler


_LOCAL_OPENER = build_opener(ProxyHandler({}))


def _port(env: dict, variable: str, default: int) -> int:
    value = str(env.get(variable, default))
    if not value.isascii() or not value.isdecimal() or not 1 <= int(value) <= 65535:
        raise ValueError(f'Porta inválida: {variable}')
    return int(value)


def _request_json(port: int, path: str, timeout: float = 1.5) -> dict:
    # Fixed local host, fixed endpoint; never use URLs returned by the peer.
    req = Request(f'http://127.0.0.1:{port}{path}',
                  headers={'Accept': 'application/json', 'Cache-Control': 'no-cache'})
    with _LOCAL_OPENER.open(req, timeout=timeout) as response:
        if response.status != 200:
            raise OSError(f'HTTP {response.status}')
        payload = response.read(512_001)
    if len(payload) > 512_000:
        raise ValueError('Resposta administrativa excede 512 KiB')
    value = json.loads(payload)
    if not isinstance(value, dict):
        raise ValueError('Resposta administrativa não é objeto JSON')
    return value


def _request_status(port: int, path: str, timeout: float = 1.5) -> bool:
    req = Request(f'http://127.0.0.1:{port}{path}', headers={'Cache-Control': 'no-cache'})
    with _LOCAL_OPENER.open(req, timeout=timeout) as response:
        return response.status == 200


def _git(root: Path, *args: str) -> str:
    try:
        result = subprocess.run(['git', '-C', str(root), *args], capture_output=True,
                                text=True, timeout=2, check=False)
        return result.stdout.strip() if result.returncode == 0 else ''
    except (OSError, subprocess.TimeoutExpired):
        return ''


def snapshot(root: Path | None = None, env: dict | None = None) -> dict:
    """Describes reachable modules. Never writes or mutates project state."""
    env = os.environ if env is None else env
    root = Path(__file__).resolve().parent if root is None else Path(root)
    items = []
    def put(ident: str, label: str, state: str, detail: str):
        items.append({'id': ident, 'label': label, 'state': state, 'detail': detail})

    put('studio', 'Estúdio SVG M2', 'online',
        'Servidor atual · projeto audiovisual permanece nesta aba')

    try:
        admin_port = _port(env, 'RD_SUITE_ADMIN_PORT', 8885)
        preview_port = _port(env, 'RD_SUITE_PREVIEW_PORT', 8886)
    except ValueError as e:
        admin_port = preview_port = None
        put('admin', 'RD Studio administrativo', 'erro', str(e))
        put('site', 'Prévia rogerioduarte.org', 'erro', str(e))
    else:
        try:
            data = _request_json(admin_port, '/api/state')
            git = data.get('git') if isinstance(data.get('git'), dict) else {}
            branch = str(git.get('branch', 'indefinida'))[:80]
            head = str(git.get('head', 'indefinido'))[:40]
            work = git.get('status', [])
            changes = len(work) if isinstance(work, list) else None
            folder = data.get('root')
            if not isinstance(folder, str) or not folder.startswith('/'):
                raise ValueError('Admin não informou raiz absoluta')
            expected = env.get('RD_SUITE_EXPECTED_SITE_ROOT', '')
            mismatch = bool(expected) and Path(folder).resolve() != Path(expected).expanduser().resolve()
            detail = f'{branch} · {head} · alterações: {changes if changes is not None else "?"}'
            if mismatch:
                detail += ' · ATENÇÃO: checkout diferente da referência configurada'
            if changes:
                detail += ' · mudanças locais existentes'
            put('admin', 'RD Studio administrativo', 'aviso' if mismatch or changes else 'online', detail)
        except (OSError, ValueError, json.JSONDecodeError, TimeoutError) as e:
            put('admin', 'RD Studio administrativo', 'indisponível',
                f'Porta {admin_port} · {type(e).__name__}')
        try:
            ready = _request_status(preview_port, '/laboratorio/')
            put('site', 'Prévia rogerioduarte.org', 'online' if ready else 'indisponível',
                'HTML do laboratório acessível; renderização 3D não verificada')
        except (OSError, ValueError, TimeoutError) as e:
            put('site', 'Prévia rogerioduarte.org', 'indisponível',
                f'Porta {preview_port} · {type(e).__name__}')

    configured = env.get('RD_SPATIALSEED_ROOT', '')
    if configured:
        spatial = Path(configured).expanduser()
        ready = (spatial / 'apps/web/index.html').is_file() and (spatial / 'vendor/three.module.js').is_file()
        if ready:
            rev = _git(spatial, 'rev-parse', '--short', 'HEAD') or 'Git não consultável'
            protected = _git(spatial, 'status', '--porcelain', '--',
                             'packages/game-runtime/src/CollisionWorld.js')
            extra = ' · CollisionWorld.js modificado: preservar' if protected else ''
            put('spatialseed', 'SpatialSeed', 'presente',
                f'checkout {rev}{extra} · cena WebGL não testada')
        else:
            put('spatialseed', 'SpatialSeed', 'indisponível',
                'Checkout configurado sem arquivos essenciais')
    else:
        put('spatialseed', 'SpatialSeed', 'não configurado', 'Defina RD_SPATIALSEED_ROOT')

    gil_dir = env.get('RD_GIL_ROOT', '')
    if gil_dir:
        gil = Path(gil_dir).expanduser()
        gil_ready = (gil / 'src/model.mjs').is_file() and (gil / 'src/timeline.mjs').is_file()
        put('gil', 'GIL', 'presente' if gil_ready else 'indisponível',
            'Runtime encontrado; execução da cena não testada' if gil_ready else 'Runtime incompleto')
    else:
        put('gil', 'GIL', 'não configurado', 'Defina RD_GIL_ROOT')

    audio_ready = (root / 'rd_audio_profiles.py').is_file() and (root / 'studio_audio_score.py').is_file()
    put('audio', 'RD-Audio', 'presente' if audio_ready else 'indisponível',
        'Módulos encontrados; síntese e audição não testadas' if audio_ready else 'Módulos de áudio ausentes')
    return {'schema': 1, 'read_only': True, 'ports': {'admin': admin_port, 'preview': preview_port},
            'services': items}
