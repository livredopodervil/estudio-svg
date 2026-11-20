"""Gera MP3 e alinhamento por palavra usando o catálogo exato do usuário.

Sem síntese em rede durante importação. Saída somente em cache controlado.
"""
from __future__ import annotations
import asyncio
import hashlib
import json
import os
from pathlib import Path
import tempfile
from threading import Lock
from typing import Any, Mapping
from .core import Catalog, normalize_voice, edge_parameters

CACHE_DIR = Path(os.environ.get('RD_VOICES_CACHE', str(Path.home() / '.cache' / 'rd-studio' / 'edge')))
_LOCK = Lock()


def synthesis_key(text: str, voice: str, params: Mapping) -> str:
    raw = json.dumps({'text': text, 'voice': voice, 'params':
                      {k: params[k] for k in ('rate','pitch','volume')}},
                     ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(raw.encode('utf-8')).hexdigest()


async def synthesize_edge(request: Mapping[str, Any], *, cache_dir: Path | None = None,
                          catalog: Catalog | None = None) -> dict:
    catalog = catalog or Catalog.load()
    text = request.get('text', '')
    if not isinstance(text, str) or not text.strip() or len(text) > 10000:
        raise ValueError('Texto deve ter de 1 a 10.000 caracteres')
    voice = normalize_voice(request.get('voice'))
    if voice['provider'] != 'edge':
        raise ValueError('Somente provider=edge é processado pelo motor Edge')
    catalog.require(voice['voice_id'])
    p = edge_parameters(request)
    key = synthesis_key(text, voice['voice_id'], p)
    root = Path(cache_dir or CACHE_DIR)
    # Arquivos temporários e finais estão confinados neste diretório.
    audio = root / (key + '.mp3')
    metadata = root / (key + '.json')
    with _LOCK:
        if audio.is_file() and metadata.is_file() and audio.stat().st_size:
            return json.loads(metadata.read_text(encoding='utf-8'))
    try:
        import edge_tts
    except ImportError:
        raise RuntimeError('Instale edge-tts no Python do Estúdio') from None
    speech = edge_tts.Communicate(text=text, voice=voice['voice_id'], rate=p['rate'],
                                 pitch=p['pitch'], volume=p['volume'])
    chunks = []
    marks = []
    total = 0
    async for chunk in speech.stream():
        kind = chunk.get('type')
        if kind == 'audio':
            data = chunk.get('data', b'')
            total += len(data)
            if total > 32 * 1024 * 1024:
                raise ValueError('Áudio excedeu o limite de 32 MiB')
            chunks.append(data)
        elif kind == 'WordBoundary':
            marks.append({'text': chunk.get('text', ''),
                          'start_sec': chunk.get('offset', 0) / 10_000_000,
                          'duration_sec': chunk.get('duration', 0) / 10_000_000})
    if not chunks or total == 0:
        raise RuntimeError('O Edge TTS não retornou áudio')
    root.mkdir(parents=True, exist_ok=True)
    result = {
        'provider': 'edge', 'voice': voice, 'params': p,
        'audio_url': '/api/rd-voices/audio/' + key + '.mp3',
        'words': marks,
        'cache_key': key,
        'metadata_url': '/api/rd-voices/metadata/' + key + '.json',
        'intention_is_native': False,
    }
    # Um erro não deve sobrescrever o último cache válido.
    with tempfile.NamedTemporaryFile(dir=root, prefix='.' + key + '.', suffix='.mp3', delete=False) as f:
        file_mp3 = Path(f.name)
        f.write(b''.join(chunks))
    with tempfile.NamedTemporaryFile(dir=root, prefix='.' + key + '.', suffix='.json', mode='w', encoding='utf-8', delete=False) as f:
        file_meta = Path(f.name)
        json.dump(result, f, ensure_ascii=False, indent=2)
    try:
        file_mp3.replace(audio)
        file_meta.replace(metadata)
    finally:
        file_mp3.unlink(missing_ok=True)
        file_meta.unlink(missing_ok=True)
    return result
