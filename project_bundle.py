"""Portable project package. No absolute paths or workspace secrets in ZIP.

The bundle includes only media referenced by this project's canonical JSON.
Read-only; does not mutate projects or media. Import is intentionally manual.
"""
from __future__ import annotations
import json
import zipfile
from pathlib import Path
from schema import asset, name, normalize

MAX_BUNDLE_BYTES = 250_000_000
IMAGE_EXT = {'.png', '.jpg', '.jpeg', '.webp'}


def referenced_media(project):
    files=set()
    def add(file):
        if file:files.add(asset(file))
    add(project.get('trilha', ''))
    for scene in project['cenas']:
        add(scene.get('imagem', {}).get('arquivo', ''))
        add(scene.get('video_clipe', {}).get('arquivo', ''))
        au=scene.get('audio', {})
        for key in ('voice_file', 'music_file'):add(au.get(key,''))
        for track in au.get('tracks', []):add(track.get('file', ''))
    return sorted(files)


def bundle_to_file(identifier, raw_project, media_dir, output):
    identifier = name(identifier)
    project = normalize(raw_project)
    media_dir = Path(media_dir)
    referenced = referenced_media(project)
    size = 0
    for filename in referenced:
        path = media_dir / filename
        if not path.is_file() or path.is_symlink():
            raise ValueError(f'Mídia referenciada não encontrada: {filename}')
        size += path.stat().st_size
        if size > MAX_BUNDLE_BYTES:
            raise ValueError('Pacote ultrapassa limite de 250 MB; retire vídeos grandes do projeto')
    output=Path(output)
    try:
        with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED, compresslevel=5) as archive:
            archive.writestr('projetos/' + identifier + '.json',
                json.dumps(project, ensure_ascii=False, indent=2))
            for filename in referenced:
                archive.write(media_dir / filename, 'midia/' + filename)
            archive.writestr('LEIA-ME.txt',
                'Pacote Estúdio SVG V3 experimental\n'
                'Inclui o JSON normalizado e as mídias referenciadas.\n'
                'Para instalar manualmente no Termux, extraia o ZIP NA RAIZ DA WORKTREE V3\n'
                'com unzip -n; revise primeiro os arquivos no ZIP. Não substitua arquivos existentes.\n'
                'O arquivo JSON está em projetos/ e as mídias em midia/.\n')
    except Exception:
        output.unlink(missing_ok=True)
        raise
    return {'files':referenced, 'path':output}
