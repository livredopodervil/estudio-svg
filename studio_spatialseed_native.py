"""SpatialSeed -> GIL native bridge, without pre-rendered MP4.

Uses the existing GIL converter; this module does not interpret or execute
SpatialSeed program commands. No project or media are changed by conversion.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
from gil_bridge import run

MAX_SOURCE = 250_000
MAX_GIL = 250_000


def convert_spatialseed(source, gil_root, spatial_root):
    if not isinstance(source, str) or not source.strip():
        raise ValueError('Documento SpatialSeed vazio ou inválido')
    original = source.encode('utf-8')
    if len(original) > MAX_SOURCE:
        raise ValueError('Documento SpatialSeed acima de 250 kB')
    try:
        data = json.loads(source)
    except json.JSONDecodeError as exc:
        raise ValueError('Documento SpatialSeed não é JSON válido') from exc
    if not isinstance(data, dict):
        raise ValueError('Documento SpatialSeed deve ser um objeto JSON')
    if not gil_root or not spatial_root:
        raise ValueError('Configure RD_GIL_ROOT e RD_SPATIALSEED_ROOT ao iniciar o servidor')
    if not Path(gil_root).is_dir() or not Path(spatial_root).is_dir():
        raise ValueError('Diretório GIL/SpatialSeed configurado não existe')
    gil = Path(gil_root).resolve(strict=True)
    spatial = Path(spatial_root).resolve(strict=True)
    converter = gil / 'tools' / 'import_spatialseed.mjs'
    if not converter.is_file():
        raise ValueError('Conversor GIL import_spatialseed.mjs não encontrado')
    if not (spatial / 'apps' / 'web').is_dir():
        raise ValueError('RD_SPATIALSEED_ROOT não aponta para o checkout do SpatialSeed')
    with tempfile.TemporaryDirectory(prefix='rd-spatialseed-native-') as tmp:
        root = Path(tmp)
        inp, out = root/'documento.spatialseed', root/'convertido.gil'
        inp.write_bytes(original)
        run(['node', '--max-old-space-size=256', converter, inp, out, spatial], 60)
        if not out.is_file() or not 0 < out.stat().st_size <= MAX_GIL:
            raise ValueError('Conversão não gerou fonte GIL válida (limite 250 kB)')
        compiled = out.read_text('utf-8')
        if not compiled.strip():
            raise ValueError('Fonte GIL convertida está vazia')
    return {
        'source': compiled,
        'source_sha256': hashlib.sha256(compiled.encode('utf-8')).hexdigest(),
        'origin_sha256': hashlib.sha256(original).hexdigest(),
        'converter': 'gil/tools/import_spatialseed.mjs',
    }
