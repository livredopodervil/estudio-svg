"""Bridge Edge-TTS -> RD-Audio score. Shares rd_voices catalog/cache/synthesis.

No new TTS engine, no second server, no project writes. The Studio mixer owns
scene timing and final WAVs; this adapter only exposes a stored MP3 filename.
"""
from __future__ import annotations
import asyncio
import os
from pathlib import Path
import shutil
import tempfile
from typing import Mapping
from .core import normalize_voice
from .edge_engine import synthesize_edge


def synthesize_edge_score(text: str, voice: str, params: Mapping,
                          media_dir, cache_dir) -> dict:
    ident = normalize_voice(voice)
    if ident['provider'] != 'edge':
        raise ValueError('Este adaptador aceita apenas vozes Edge')
    # The shared Edge synthesizer validates the chosen voice against the catalog.
    prosody = {
        'rate_pct': int(str(params['rate']).removesuffix('%')),
        'pitch_hz': int(str(params['pitch']).removesuffix('Hz')),
        'volume_pct': int(str(params['volume']).removesuffix('%')),
    }
    root = Path(cache_dir) / 'rd-edge-score'
    try:
        item = asyncio.run(synthesize_edge(
            {'text': text, 'voice': ident, 'prosody': prosody}, cache_dir=root))
    except FileNotFoundError as e:
        raise ValueError('Catálogo Edge ausente: atualize-o antes de gerar a locução') from e
    src = root / (item['cache_key'] + '.mp3')
    dest = Path(media_dir) / ('rd-edge-' + item['cache_key'] + '.mp3')
    if src.is_symlink() or not src.is_file() or not src.stat().st_size:
        raise ValueError('O Edge não entregou um MP3 válido')
    if dest.is_symlink():
        raise ValueError('Destino Edge é um vínculo simbólico')
    cached = dest.is_file() and dest.stat().st_size > 0
    if not cached:
        # Avoid replacement of an existing media file, including a race.
        fd, name = tempfile.mkstemp(prefix='.rd-edge-',suffix='.mp3',dir=cache_dir)
        temp = Path(name)
        try:
            with os.fdopen(fd, 'wb') as output, src.open('rb') as source:
                shutil.copyfileobj(source, output)
            created = False
            try:
                with dest.open('xb') as output:
                    created = True
                    with temp.open('rb') as source:
                        shutil.copyfileobj(source, output)
            except FileExistsError:
                if dest.is_symlink() or not dest.is_file() or not dest.stat().st_size:
                    raise ValueError('Arquivo Edge existente é inválido')
                cached = True
            except Exception:
                if created:
                    dest.unlink(missing_ok=True)
                raise
        finally:
            temp.unlink(missing_ok=True)
    return {'filename': dest.name, 'voice': voice, 'cached': cached,
            'provider': 'edge', 'words': item.get('words', [])}
