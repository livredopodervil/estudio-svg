"""Transactional, bounded ZIP import for an Estúdio SVG project and its referenced assets.

Never extract arbitrary archive paths; only named media explicitly referenced in the
validated project is copied. Existing projects/assets are never overwritten.
"""
from __future__ import annotations

import json
import re
import shutil
import stat
import tempfile
import zipfile
from pathlib import Path, PurePosixPath

from PIL import Image

from project_bundle import referenced_media
from schema import asset, name, normalize

MAX_UPLOAD_BYTES = 250_000_000
MAX_UNPACKED_BYTES = 300_000_000
MAX_MEMBERS = 180
MAX_JSON_BYTES = 6_000_000
IMAGE_EXT = {'.png', '.jpg', '.jpeg', '.webp'}
AUDIO_EXT = {'.mp3', '.wav', '.m4a', '.ogg', '.flac', '.aac', '.webm', '.mp4', '.opus'}
VIDEO_EXT = {'.mp4', '.webm', '.mov', '.mkv', '.m4v'}
ALL_MEDIA_EXT = IMAGE_EXT | AUDIO_EXT | VIDEO_EXT


def _archive_layout(z):
    """Return the single project entry and asset basename -> archive entry map."""
    if len(z.infolist()) > MAX_MEMBERS:
        raise ValueError('ZIP possui arquivos demais (máximo 180)')
    total = 0
    projects = []
    media = {}
    seen = set()
    for entry in z.infolist():
        path = PurePosixPath(entry.filename)
        parts = path.parts
        if (not parts or path.is_absolute() or any(p in ('..', '.') for p in parts)
                or '\\' in entry.filename or '\x00' in entry.filename):
            raise ValueError('ZIP contém caminho proibido')
        if entry.filename in seen:
            raise ValueError('ZIP contém nomes de arquivo duplicados')
        seen.add(entry.filename)
        mode = (entry.external_attr >> 16)
        if stat.S_ISLNK(mode):
            raise ValueError('ZIP contém link simbólico; importação recusada')
        if entry.is_dir():
            continue
        if entry.flag_bits & 1:
            raise ValueError('ZIP criptografado não é suportado')
        if entry.file_size > MAX_UPLOAD_BYTES:
            raise ValueError('Arquivo no ZIP excede 250 MB')
        total += entry.file_size
        if total > MAX_UNPACKED_BYTES:
            raise ValueError('ZIP excede 300 MB após descompactação')
        if entry.file_size > 100_000 and entry.file_size > entry.compress_size * 300:
            raise ValueError('ZIP possui taxa de compressão excessiva')
        if ((len(parts) == 1 or (len(parts) == 2 and parts[0] == 'projetos'))
                and path.suffix.lower() == '.json'):
            projects.append(entry)
            continue
        if ((len(parts) == 1 or (len(parts) == 2 and parts[0] in ('midia', 'media', 'assets')))
                and path.suffix.lower() in ALL_MEDIA_EXT):
            basename = asset(parts[-1])
            if basename in media:
                raise ValueError('Mídia com nome ambíguo em mais de uma pasta: ' + basename)
            media[basename] = entry
    if len(projects) != 1:
        raise ValueError('O ZIP deve conter exatamente um projeto JSON em / ou projetos/')
    if projects[0].file_size > MAX_JSON_BYTES:
        raise ValueError('JSON excede 6 MB')
    return projects[0], media


def _free_name(folder, preferred, kind='asset'):
    if kind == 'project':
        stem = re.sub(r'[^A-Za-z0-9_-]+', '_', str(preferred)).strip('_')[:52] or 'importado'
        extension = '.json'
    else:
        file = asset(preferred)
        extension = Path(file).suffix.lower()
        stem = Path(file).stem[:125]
    for i in range(1, 10001):
        basename = stem + ('' if i == 1 else '_' + str(i)) + extension
        if len(basename) > 160:
            continue
        if not (folder / basename).exists():
            return basename
    raise ValueError('Não foi possível encontrar nome livre')


def import_zip(source, preferred_name, projects_dir, media_dir, cache_dir, media_validator=None):
    """Import one project, returning {name, media, scenes}; errors roll back new files.

    Call under the application's import lock. media_validator(path, kind) may validate
    audio/video using ffprobe. `source` must be a completed upload in cache.
    """
    source, projects_dir, media_dir, cache_dir = map(Path, (source, projects_dir, media_dir, cache_dir))
    if not source.is_file() or source.stat().st_size > MAX_UPLOAD_BYTES:
        raise ValueError('ZIP ausente ou maior que 250 MB')
    created = []
    with zipfile.ZipFile(source, 'r') as archive:
        project_entry, media_entries = _archive_layout(archive)
        raw = archive.read(project_entry)
        project = normalize(json.loads(raw.decode('utf-8-sig')))
        required = referenced_media(project)
        absent = [f for f in required if f not in media_entries]
        if absent:
            raise ValueError('ZIP não contém mídia referenciada: ' + ', '.join(absent[:5]))
        project_name = _free_name(projects_dir, preferred_name or Path(project_entry.filename).stem, 'project')[:-5]
        with tempfile.TemporaryDirectory(prefix='import-', dir=cache_dir) as tmp:
            tempdir = Path(tmp)
            mapping = {}
            # MediaRecorder writes audio-only WebM too: infer stream kind from the
            # JSON field, not merely from the filename extension.
            video_files = {scene['video_clipe']['arquivo'] for scene in project['cenas'] if scene['video_clipe']['arquivo']}
            audio_files = ({project['trilha']} if project['trilha'] else set())
            for scene in project['cenas']:
                au = scene['audio']
                audio_files.update(x for x in (au['voice_file'],au['music_file']) if x)
                audio_files.update(track['file'] for track in au['tracks'])
            for filename in required:
                staging = tempdir / filename
                with archive.open(media_entries[filename]) as original, staging.open('xb') as dest:
                    shutil.copyfileobj(original, dest, 256 * 1024)
                suffix = staging.suffix.lower()
                if suffix in IMAGE_EXT:
                    try:
                        with Image.open(staging) as img:
                            img.verify()
                    except (OSError, ValueError) as err:
                        raise ValueError('Imagem inválida no ZIP: '+filename) from err
                elif suffix not in ALL_MEDIA_EXT:
                    raise ValueError('Formato de mídia não permitido: ' + filename)
                if suffix not in IMAGE_EXT and media_validator:
                    if filename in video_files:
                        media_validator(staging, 'video')
                    if filename in audio_files or filename not in video_files:
                        media_validator(staging, 'audio')
                mapping[filename] = _free_name(media_dir, filename)
            updated = json.loads(json.dumps(project))
            def replace(original):
                return mapping.get(original, original)
            updated['trilha'] = replace(updated['trilha'])
            for scene in updated['cenas']:
                scene['imagem']['arquivo'] = replace(scene['imagem']['arquivo'])
                scene['video_clipe']['arquivo'] = replace(scene['video_clipe']['arquivo'])
                a = scene['audio']
                a['voice_file'] = replace(a['voice_file'])
                a['music_file'] = replace(a['music_file'])
                for track in a['tracks']:
                    track['file'] = replace(track['file'])
            updated = normalize(updated)
            try:
                for source_name, final_name in mapping.items():
                    target = media_dir / final_name
                    with (tempdir / source_name).open('rb') as inp, target.open('xb') as out:
                        created.append(target)
                        shutil.copyfileobj(inp, out, 256 * 1024)
                target_project = projects_dir / (project_name + '.json')
                with target_project.open('x', encoding='utf-8') as out:
                    created.append(target_project)
                    json.dump(updated, out, ensure_ascii=False, indent=2)
            except Exception:
                for f in reversed(created):
                    f.unlink(missing_ok=True)
                raise
    return {'name': project_name, 'media': mapping, 'scenes': len(updated['cenas'])}
