"""M1P: physical project folders and reversible trash, no media deletion.

Project IDs remain flat and globally unique; moving folders does not rewrite
JSON or cache keys. Paths are constrained to PROJECTS/.pastas/<folder>.
"""
from __future__ import annotations
import json
import os
import re
import time
import uuid
from pathlib import Path
from schema import name

FOLDER_RE = re.compile(r'[A-Za-z0-9_-]{1,60}\Z')


def safe_root(root):
    root = Path(root)
    if not root.is_dir() or root.is_symlink():
        raise ValueError('Diretório de projetos inválido')
    return root


def safe_folder(value):
    if not isinstance(value, str):
        raise ValueError('Pasta inválida')
    if value in ('', 'Projetos'):
        return ''
    if not FOLDER_RE.fullmatch(value) or value.startswith('.'):
        raise ValueError('Pasta: use somente letras, números, _ e - (máximo 60)')
    return value


def parent_of(root, folder, create=False):
    root = safe_root(root)
    folder = safe_folder(folder)
    if not folder:
        return root
    base = root / '.pastas'
    if base.is_symlink():
        raise ValueError('Pasta raiz insegura')
    p = base / folder
    if p.is_symlink():
        raise ValueError('Pasta insegura')
    if create:
        base.mkdir(exist_ok=True)
        p.mkdir(exist_ok=True)
    return p


def _active_paths(root, project):
    root = safe_root(root)
    identifier = name(project)
    candidates = [root / (identifier + '.json')]
    base = root / '.pastas'
    if base.exists():
        if base.is_symlink() or not base.is_dir():
            raise ValueError('Pasta de projetos insegura')
        for p in base.iterdir():
            if p.is_symlink():
                raise ValueError('Subpasta simbólica proibida')
            if p.is_dir() and FOLDER_RE.fullmatch(p.name):
                candidates.append(p / (identifier + '.json'))
    for p in candidates:
        if p.is_symlink():
            raise ValueError('Projeto simbólico proibido')
    return [p for p in candidates if p.is_file()]


def project_path(root, project):
    paths = _active_paths(root, project)
    if len(paths) > 1:
        raise ValueError('Identificador duplicado entre pastas; corrija antes de continuar')
    return paths[0] if paths else safe_root(root) / (name(project) + '.json')


def list_projects(root):
    # M1Q: catálogo tolerante a identificadores legados; não modificar os arquivos.
    root = safe_root(root)
    names = {}
    problems = []
    ambiguous = set()

    def collect(path, folder):
        if path.is_symlink():
            raise ValueError('Projeto simbólico proibido: ' + path.name)
        if not path.is_file():
            return
        try:
            ident = name(path.stem)
        except ValueError:
            problems.append({'arquivo': path.name, 'pasta': folder,
                             'motivo': 'nome fora do padrão; original preservado'})
            return
        if ident in ambiguous:
            return
        if ident in names:
            # Nunca escolher aleatoriamente um dos dois projetos homônimos.
            ambiguous.add(ident)
            names.pop(ident, None)
            problems.append({'arquivo': ident + '.json', 'pasta': folder,
                             'motivo': 'identificador duplicado em mais de uma pasta'})
            return
        names[ident] = folder

    for p in sorted(root.glob('*.json')):
        collect(p, '')
    base = root / '.pastas'
    directories = []
    if base.exists():
        if base.is_symlink() or not base.is_dir():
            raise ValueError('Pasta de projetos insegura')
        for folder in sorted(base.iterdir()):
            if folder.is_symlink():
                raise ValueError('Subpasta simbólica proibida')
            if not folder.is_dir() or not FOLDER_RE.fullmatch(folder.name):
                continue
            directories.append(folder.name)
            for p in sorted(folder.glob('*.json')):
                collect(p, folder.name)
    return {'projects': sorted(names), 'folders': names,
            'directories': directories, 'warnings': problems}



def trash_list(root):
    folder = safe_root(root) / '.lixeira'
    if folder.is_symlink():
        raise ValueError('Lixeira insegura')
    if not folder.exists():
        return []
    result = []
    for p in sorted(folder.glob('*.json')):
        if p.is_symlink():
            raise ValueError('Item simbólico na lixeira')
        meta = p.with_suffix('.meta')
        if not meta.is_file() or meta.is_symlink():
            continue
        data = json.loads(meta.read_text('utf-8'))
        result.append({'token':p.stem, 'name':data['name'], 'folder':data.get('folder', '')})
    return result


def manage(root, action, identifier='', *, new_name='', folder='', token=''):
    root = safe_root(root)
    if action == 'mkdir':
        wanted = safe_folder(folder)
        if not wanted:
            raise ValueError('Informe uma pasta nova')
        parent_of(root, wanted, create=True)
        return {'ok': True, 'folder': wanted}
    if action == 'restore':
        if not isinstance(token, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,140}', token):
            raise ValueError('Token da lixeira inválido')
        trash = root / '.lixeira'
        if trash.is_symlink():
            raise ValueError('Lixeira insegura')
        src = trash / (token + '.json')
        meta = trash / (token + '.meta')
        if src.is_symlink() or meta.is_symlink() or not src.is_file() or not meta.is_file():
            raise ValueError('Item não encontrado na lixeira')
        info = json.loads(meta.read_text('utf-8'))
        target_name = name(info['name'])
        if _active_paths(root, target_name):
            raise ValueError('Identificador já existe; não sobrescrito')
        dest = parent_of(root, info.get('folder', ''), create=True) / (target_name + '.json')
        if dest.exists():
            raise ValueError('Destino ocupado')
        os.replace(src, dest)
        meta.unlink()
        return {'ok': True, 'name': target_name, 'folder': info.get('folder', '')}
    identifier = name(identifier)
    src = project_path(root, identifier)
    if not src.is_file():
        raise ValueError('Projeto inexistente: ' + identifier)
    current_folder = src.parent.name if src.parent.parent == root / '.pastas' else ''
    if action == 'trash':
        if len(list_projects(root)['projects']) <= 1:
            raise ValueError('Não é permitido remover o último projeto ativo')
        trash = root / '.lixeira'
        if trash.is_symlink():
            raise ValueError('Lixeira insegura')
        trash.mkdir(exist_ok=True)
        token = name(identifier + '__' + uuid.uuid4().hex[:12])
        dest = trash / (token + '.json')
        meta = trash / (token + '.meta')
        metadata = {'name': identifier, 'folder': current_folder, 'at': time.time()}
        with meta.open('x', encoding='utf-8') as out:
            json.dump(metadata, out, ensure_ascii=False)
            out.flush()
            os.fsync(out.fileno())
        try:
            os.replace(src, dest)
        except BaseException:
            meta.unlink(missing_ok=True)
            raise
        return {'ok': True, 'token': token, 'name': identifier}
    if action not in ('move', 'rename'):
        raise ValueError('Operação inválida')
    target_name = name(new_name if action == 'rename' else identifier)
    target_folder = safe_folder(folder if action == 'move' else current_folder)
    if action == 'rename' and target_name != identifier and _active_paths(root, target_name):
        raise ValueError('Identificador já existe; não sobrescrito')
    dest = parent_of(root, target_folder, create=True) / (target_name + '.json')
    if src == dest:
        return {'ok': True, 'name': target_name, 'folder': target_folder, 'unchanged': True}
    if dest.exists() or dest.is_symlink():
        raise ValueError('Destino já ocupado; nada sobrescrito')
    os.replace(src, dest)
    return {'ok': True, 'name': target_name, 'folder': target_folder}


def archive(root, identifier, restore=False):
    root = safe_root(root)
    folder = root / '.arquivados'
    if folder.is_symlink():
        raise ValueError('Arquivo inseguro')
    folder.mkdir(exist_ok=True)
    target = folder / (name(identifier) + '.json')
    if target.is_symlink():
        raise ValueError('Projeto arquivado inseguro')
    if restore:
        if not target.is_file() or _active_paths(root, identifier):
            raise ValueError('Projeto arquivado ausente ou destino ocupado')
        os.replace(target, root / (name(identifier) + '.json'))
    else:
        if len(list_projects(root)['projects']) <= 1:
            raise ValueError('Não é possível arquivar o último projeto')
        src = project_path(root, identifier)
        if not src.is_file() or target.exists():
            raise ValueError('Origem ausente ou arquivo já existente')
        os.replace(src, target)
    return identifier
