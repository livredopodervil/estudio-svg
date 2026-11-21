"""Materialize exact native sources beside the Studio project collection."""
from hashlib import sha256
from pathlib import Path
import tempfile


def spatialseed_files(project):
    for scene in project['cenas']:
        source = scene.get('spatialseed_viewport', {}).get('source')
        if source:
            data = source.encode('utf-8')
            yield sha256(data).hexdigest() + '.spatialseed', data


def _already_stored(path, data):
    if path.is_symlink() or (path.exists() and not path.is_file()):
        raise ValueError('Conflito ao preservar fonte SpatialSeed: ' + path.name)
    try:
        existing = path.read_bytes()
    except FileNotFoundError:
        return False
    if existing != data:
        raise ValueError('Conflito ao preservar fonte SpatialSeed: ' + path.name)
    return True


def store_spatialseed_files(projects, project):
    folder = Path(projects) / 'spatialseed'
    for filename, data in spatialseed_files(project):
        if folder.is_symlink():
            raise ValueError('Diretório SpatialSeed simbólico')
        folder.mkdir(exist_ok=True)
        dest = folder / filename
        if _already_stored(dest, data):
            continue

        # Concurrent Studio writers for this digest publish identical bytes.
        # Stage on the same filesystem and close before the atomic rename.
        staged = tempfile.NamedTemporaryFile(dir=folder, prefix='.fonte-', delete=False)
        temp_path = Path(staged.name)
        try:
            with staged:
                staged.write(data)
            if not _already_stored(dest, data):
                temp_path.replace(dest)
        finally:
            temp_path.unlink(missing_ok=True)
