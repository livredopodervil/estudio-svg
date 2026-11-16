#!/usr/bin/env python3
"""RD Studio: edição e vistoria local de sites estáticos, sem dependências externas.

Servidor de administração e servidor de prévia têm ORIGENS DISTINTAS (portas distintas).
Vincula exclusivamente a 127.0.0.1. Push somente com confirmação explícita e verificações de segurança.
"""
from __future__ import annotations

import argparse
import base64
import binascii
from datetime import datetime, timezone
import hashlib
from html.parser import HTMLParser
import json
import mimetypes
import os
from pathlib import Path, PurePosixPath
import re
import secrets
import shutil
import subprocess
import sys
import tempfile
from threading import Thread
from http.server import BaseHTTPRequestHandler, SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote, urljoin, urlsplit
from patches import PatchManager, PatchError
from discovery import Discovery, ALLOWED_FILES
from spatial import SpatialOps

MAX_TEXT = 2_000_000
MAX_ASSET = 8_000_000
MAX_BODY = 12_000_000
TEXT_SUFFIXES = {'.html', '.htm', '.css', '.js', '.mjs', '.json', '.md', '.txt', '.yml', '.yaml', '.svg', '.xml'}
MEDIA_SUFFIXES = {'.png', '.jpg', '.jpeg', '.webp', '.gif', '.ico', '.pdf', '.woff', '.woff2', '.ttf', '.otf', '.wasm', '.mp3', '.ogg', '.mp4', '.webmanifest'}
EXCLUDED = {'.git', '.github', '.rd-studio', 'node_modules', '.venv', 'venv', '__pycache__', '.cache', 'dist', 'build'}
ID_RE = re.compile(r'^[a-z0-9][a-z0-9-]{0,70}$')


class StudioError(Exception):
    def __init__(self, message: str, status: int = 400):
        self.status = status
        super().__init__(message)


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def cmd(args: list[str], cwd: Path, timeout: int = 20) -> tuple[int, str]:
    try:
        r = subprocess.run(args, cwd=cwd, capture_output=True, text=True, timeout=timeout, encoding='utf-8', errors='replace')
        return r.returncode, (r.stdout + ('\n' + r.stderr if r.stderr else ''))[:100_000]
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 1, str(exc)


def is_git(root: Path) -> bool:
    return cmd(['git', 'rev-parse', '--is-inside-work-tree'], root)[0] == 0


class HTMLLinks(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.refs: list[str] = []
        self.base: str | None = None
        self.ogs: dict[str, str] = {}

    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        if tag == 'base' and d.get('href'):
            self.base = d['href']
            return  # base é configuração, não um recurso a carregar
        if tag == 'meta' and d.get('property', '').startswith('og:'):
            self.ogs[d['property']] = d.get('content', '')
        for k in ('src', 'href', 'poster'):
            if d.get(k):
                self.refs.append(d[k])
        if d.get('srcset'):
            for item in d['srcset'].split(','):
                self.refs.append(item.strip().split(' ')[0])


class Studio:
    def __init__(self, repo: Path, admin_port: int, preview_port: int):
        self.root = repo.resolve(strict=True)
        if not self.root.is_dir():
            raise StudioError('A raiz do projeto não é um diretório')
        self.admin_port = admin_port
        self.preview_port = preview_port
        self.token = secrets.token_urlsafe(36)
        ident = sha(str(self.root).encode())[:16]
        self.history_root = Path.home() / '.rd-studio' / 'historico' / ident
        self.last_validation: dict | None = None
        self.validation_fingerprint: str | None = None
        self.patches = PatchManager(self.root)
        self.discovery = Discovery(self, StudioError)
        self.spatial = SpatialOps(self, StudioError)

    def resolve(self, rel: str, *, allow_missing: bool = False) -> Path:
        if not isinstance(rel, str) or not rel or len(rel) > 500 or '\\' in rel or '\x00' in rel:
            raise StudioError('Caminho inválido')
        p = PurePosixPath(rel)
        if p.is_absolute() or any(x in ('', '.', '..') for x in rel.split('/')):
            raise StudioError('Caminho fora do projeto')
        for part in p.parts:
            if part in EXCLUDED or (part.startswith('.') and part != '.pages.yml'):
                raise StudioError('Diretório/arquivo protegido')
        # Impede seguir symlinks, inclusive em diretórios existentes.
        current = self.root
        for component in p.parts:
            current = current / component
            if current.is_symlink():
                raise StudioError('Links simbólicos não são editáveis')
        out = self.root.joinpath(*p.parts)
        if not out.is_relative_to(self.root):
            raise StudioError('Caminho fora da raiz')
        if not allow_missing and not out.is_file():
            raise StudioError('Arquivo não encontrado', 404)
        return out

    def file_items(self, q: str = '') -> list[dict]:
        result = []
        q = q.casefold()[:80]
        for folder, subdirs, files in os.walk(self.root, followlinks=False):
            subdirs[:] = sorted(d for d in subdirs if d not in EXCLUDED and not d.startswith('.')
                                and not (Path(folder) / d).is_symlink())
            for name in sorted(files):
                f = Path(folder) / name
                if f.is_symlink() or (name.startswith('.') and name != '.pages.yml'):
                    continue
                if f.suffix.lower() not in TEXT_SUFFIXES | MEDIA_SUFFIXES and name != 'CNAME':
                    continue
                relative = f.relative_to(self.root).as_posix()
                if q and q not in relative.casefold():
                    continue
                result.append({'path': relative, 'size': f.stat().st_size, 'type': 'text' if f.suffix.lower() in TEXT_SUFFIXES or name == 'CNAME' else 'media'})
                if len(result) >= 2500:
                    return result
        return result

    def text_read(self, rel: str) -> dict:
        f = self.resolve(rel)
        if f.suffix.lower() not in TEXT_SUFFIXES and f.name != 'CNAME':
            raise StudioError('Este arquivo deve ser gerenciado como mídia')
        if f.stat().st_size > MAX_TEXT:
            raise StudioError('Arquivo de texto acima do limite de 2 MB')
        raw = f.read_bytes()
        try:
            content = raw.decode('utf-8')
        except UnicodeError:
            raise StudioError('O arquivo não está codificado em UTF-8')
        return {'path': rel, 'content': content, 'sha256': sha(raw), 'bytes': len(raw)}

    def fingerprint(self) -> str:
        rows = []
        for item in self.file_items():
            f = self.root / item['path']
            s = f.stat()
            rows.append(f"{item['path']}:{s.st_size}:{s.st_mtime_ns}")
        return sha('\n'.join(rows).encode())

    def backup(self, rel: str, original: bytes):
        folder = self.history_root / Path(rel).parent
        folder.mkdir(parents=True, exist_ok=True)
        # Id único, sem colisão em edições rápidas.
        name = Path(rel).name
        stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        backup = folder / f'{name}.{stamp}.{sha(original)[:12]}.bak'
        backup.write_bytes(original)

    def atomic_write(self, rel: str, data: bytes, expected: str | None, *, allowed_suffixes: set[str]):
        target = self.resolve(rel, allow_missing=True)
        if target.suffix.lower() not in allowed_suffixes and target.name != 'CNAME':
            raise StudioError('Extensão não permitida')
        if len(data) > (MAX_TEXT if target.suffix.lower() in TEXT_SUFFIXES or target.name == 'CNAME' else MAX_ASSET):
            raise StudioError('Arquivo excede limite de tamanho')
        original = target.read_bytes() if target.is_file() else None
        found = sha(original) if original is not None else None
        if found != expected:
            raise StudioError('Arquivo alterado por outro processo. Recarregue antes de salvar.', 409)
        if original == data:
            return {'path': rel, 'sha256': found, 'unchanged': True}
        target.parent.mkdir(parents=True, exist_ok=True)
        if original is not None:
            self.backup(rel, original)
        fd, temp = tempfile.mkstemp(prefix='.rd-write-', dir=target.parent)
        try:
            with os.fdopen(fd, 'wb') as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
            if original is not None:
                os.chmod(temp, target.stat().st_mode & 0o777)
            os.replace(temp, target)
        finally:
            if os.path.exists(temp):
                os.unlink(temp)
        self.last_validation = None
        self.validation_fingerprint = None
        return {'path': rel, 'sha256': sha(data), 'unchanged': False}

    def save_text(self, data: dict):
        rel = data.get('path')
        body = data.get('content')
        if not isinstance(body, str):
            raise StudioError('Conteúdo textual ausente')
        if rel.endswith('.json'):
            try:
                json.loads(body)
            except ValueError as exc:
                raise StudioError(f'JSON inválido: {exc}')
        expected = data.get('expected_sha256')
        return self.atomic_write(rel, body.encode('utf-8'), expected, allowed_suffixes=TEXT_SUFFIXES)

    def media_info(self, rel: str):
        f = self.resolve(rel, allow_missing=True)
        if f.suffix.lower() not in MEDIA_SUFFIXES:
            raise StudioError('Caminho não é um arquivo de mídia')
        return {'exists': f.is_file(), 'sha256': sha(f.read_bytes()) if f.is_file() else None, 'path': rel}

    def asset_upload(self, data: dict):
        rel = data.get('path', '')
        if not (rel.startswith('assets/') or rel.startswith('images/') or
                (rel.startswith('projetos/') and '/assets/' in rel)):
            raise StudioError('Imagens devem ficar em assets/, images/ ou projetos/*/assets/')
        path = self.resolve(rel, allow_missing=True)
        suffix = path.suffix.lower()
        if suffix not in {'.png', '.jpg', '.jpeg', '.webp', '.gif'}:
            raise StudioError('Formato de imagem não aceito')
        try:
            content = base64.b64decode(data['base64'], validate=True)
        except (binascii.Error, KeyError, TypeError):
            raise StudioError('Imagem Base64 inválida')
        signatures = {
            '.png': content.startswith(b'\x89PNG\r\n\x1a\n'),
            '.jpg': content.startswith(b'\xff\xd8\xff'),
            '.jpeg': content.startswith(b'\xff\xd8\xff'),
            '.webp': content[:4] == b'RIFF' and content[8:12] == b'WEBP',
            '.gif': content[:6] in (b'GIF87a', b'GIF89a'),
        }
        if not signatures[suffix]:
            raise StudioError('O formato interno não corresponde à extensão')
        return self.atomic_write(rel, content, data.get('expected_sha256'), allowed_suffixes=MEDIA_SUFFIXES)

    def catalog(self) -> dict:
        folder = self.root / 'catalog' / 'projects'
        projects = []
        errors = []
        if folder.is_dir():
            for f in sorted(folder.glob('*.json')):
                if f.is_symlink():
                    continue
                try:
                    projects.append(json.loads(f.read_text('utf-8')))
                except (ValueError, UnicodeError) as exc:
                    errors.append(f'{f.name}: {exc}')
        return {'exists': folder.is_dir(), 'projects': projects, 'errors': errors}

    def init_catalog(self) -> dict:
        if (self.root / 'catalog/projects').exists():
            return {'created': False}
        self.atomic_write('catalog/edges.json', json.dumps({'schemaVersion': 1, 'edges': []}, ensure_ascii=False, indent=2).encode() + b'\n', None, allowed_suffixes=TEXT_SUFFIXES)
        (self.root / 'catalog/projects').mkdir(parents=True, exist_ok=True)
        return {'created': True}

    def catalog_save(self, d: dict) -> dict:
        ident = (d.get('id') or '').strip()
        if not ID_RE.fullmatch(ident):
            raise StudioError('ID deve conter apenas letras minúsculas, números e hífens')
        title = (d.get('title') or '').strip()
        if not title:
            raise StudioError('Título obrigatório')
        status = d.get('status')
        if status not in ('publicado', 'demonstracao', 'rascunho'):
            raise StudioError('Estado inválido')
        url = (d.get('url') or '').strip()
        if url and not (url.startswith('/') and not url.startswith('//')):
            u = urlsplit(url)
            if u.scheme != 'https' or not u.netloc:
                raise StudioError('URL deve ser HTTPS ou um caminho interno iniciado por /')
        preview = (d.get('preview') or '').strip()
        if preview and not (preview.startswith('/') and not preview.startswith('//')):
            raise StudioError('Prévia deve ser um caminho local começando com /')
        color = (d.get('color') or '#07899d').strip()
        if not re.fullmatch(r'#[0-9a-fA-F]{6}', color):
            raise StudioError('Cor deve usar #RRGGBB')
        current = self.resolve(f'catalog/projects/{ident}.json', allow_missing=True)
        preserved = {}
        if current.is_file() and not current.is_symlink():
            try:
                preserved = json.loads(current.read_text('utf-8'))
            except (ValueError, UnicodeError) as exc:
                raise StudioError(f'Registro existente inválido: {exc}')
        record = {
            **preserved,
            'id': ident,
            'title': title[:180],
            'summary': (d.get('summary') or '').strip()[:4000],
            'status': status,
            'category': (d.get('category') or '').strip()[:100],
            'url': url,
            'preview': preview,
            'color': color,
            'topics': [x.strip() for x in d.get('topics', []) if isinstance(x, str) and x.strip()][:30],
            'neighbors': [x.strip() for x in d.get('neighbors', []) if isinstance(x, str) and x.strip()][:30],
        }
        rel = f'catalog/projects/{ident}.json'
        return self.atomic_write(rel, (json.dumps(record, ensure_ascii=False, indent=2) + '\n').encode('utf-8'), d.get('expected_sha256'), allowed_suffixes=TEXT_SUFFIXES)

    def history(self, rel: str) -> list[dict]:
        self.resolve(rel, allow_missing=True)
        f = Path(rel)
        folder = self.history_root / f.parent
        if not folder.is_dir():
            return []
        files = sorted(folder.glob(f'{f.name}.*.bak'), reverse=True)[:40]
        return [{'id': x.name, 'bytes': x.stat().st_size} for x in files if x.is_file()]

    def restore(self, d: dict):
        rel, ident = d.get('path', ''), d.get('id', '')
        self.resolve(rel, allow_missing=True)
        if not re.fullmatch(r'[\w.\-]{1,240}\.bak', ident) or '/' in ident:
            raise StudioError('Identificador de versão inválido')
        f = self.history_root / Path(rel).parent / ident
        if f.name not in {x['id'] for x in self.history(rel)}:
            raise StudioError('Versão não encontrada', 404)
        return self.atomic_write(rel, f.read_bytes(), d.get('expected_sha256'), allowed_suffixes=TEXT_SUFFIXES | MEDIA_SUFFIXES)

    def import_plan(self, data: dict) -> dict:
        """Somente diretórios sob HOME; sem substituir arquivos existentes."""
        source_text = data.get('source', '')
        ident = data.get('id', '')
        if not isinstance(source_text, str) or not isinstance(ident, str) or not ID_RE.fullmatch(ident):
            raise StudioError('Informe um diretório e um ID válido (minúsculas e hífens)')
        if not source_text.strip() or len(source_text) > 1000:
            raise StudioError('Informe o diretório existente no Termux')
        source = Path(source_text).expanduser().resolve(strict=False)
        home = Path.home().resolve()
        if not source.is_relative_to(home) or source == home or source.is_relative_to(self.root):
            raise StudioError('A origem deve ser um projeto independente dentro de HOME')
        if source.is_symlink() or not source.is_dir() or any(part.startswith('.') or part in EXCLUDED for part in source.relative_to(home).parts):
            raise StudioError('Diretório ausente, protegido ou não permitido')
        target = self.root / 'projetos' / ident
        if target.exists():
            raise StudioError('O projeto já existe no site: importação não substitui diretórios', 409)
        destination_register = self.root / 'catalog' / 'projects' / f'{ident}.json'
        if destination_register.exists():
            raise StudioError('ID já existe no catálogo', 409)
        assets = []
        size = 0
        for folder, dirs, files in os.walk(source, followlinks=False):
            dirs[:] = sorted(d for d in dirs if not d.startswith('.') and d not in EXCLUDED and not (Path(folder)/d).is_symlink())
            for name in sorted(files):
                f = Path(folder)/name
                if name.startswith('.') or f.is_symlink() or f.suffix.lower() not in ALLOWED_FILES:
                    continue
                rel = f.relative_to(source).as_posix()
                st = f.stat()
                size += st.st_size
                assets.append({'path': rel, 'bytes': st.st_size, 'mtime': st.st_mtime_ns})
                if len(assets) > 600 or size > 80_000_000:
                    raise StudioError('Projeto muito grande (>600 arquivos ou 80 MB); selecione uma pasta mais específica')
        if not any(a['path'] == 'index.html' for a in assets):
            raise StudioError('O diretório selecionado precisa conter index.html na raiz')
        fingerprint = sha(json.dumps(assets, sort_keys=True).encode())
        review_warnings = []
        for asset in assets:
            rel = asset['path']
            if Path(rel).suffix.lower() not in {'.js', '.mjs', '.json', '.html', '.txt', '.yml', '.yaml', '.py'}:
                continue
            if asset['bytes'] > 400_000:
                continue
            try:
                sample = (source / rel).read_text('utf-8', errors='replace')
                if re.search(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----', sample):
                    raise StudioError('Chave privada encontrada em ' + rel + '; remova-a antes de importar')
                if re.search(r'(?i)(api[_-]?key|secret[_-]?key|access[_-]?token|authorization)\s*[:=]\s*[\"\'][A-Za-z0-9_.-]{24,}', sample):
                    review_warnings.append('Possível segredo embutido em ' + rel + '; revise antes de publicar.')
            except UnicodeError:
                continue
        return {'review_warnings': review_warnings[:20], 'source': str(source), 'id': ident, 'dest': f'projetos/{ident}',
                'files': len(assets), 'bytes': size, 'sample': [x['path'] for x in assets[:20]],
                'fingerprint': fingerprint}

    def import_apply(self, data: dict) -> dict:
        if data.get('confirm') != 'IMPORTAR':
            raise StudioError('Confirme com IMPORTAR')
        plan = self.import_plan(data)
        if data.get('fingerprint') != plan['fingerprint']:
            raise StudioError('Arquivos da origem mudaram após a inspeção; refaça o plano.', 409)
        source = Path(plan['source'])
        target = self.root / plan['dest']
        target.parent.mkdir(parents=True, exist_ok=True)
        target.mkdir(exist_ok=False)
        try:
            for folder, dirs, files in os.walk(source, followlinks=False):
                dirs[:] = sorted(d for d in dirs if not d.startswith('.') and d not in EXCLUDED and not (Path(folder)/d).is_symlink())
                for name in files:
                    f = Path(folder) / name
                    if name.startswith('.') or f.is_symlink() or f.suffix.lower() not in ALLOWED_FILES:
                        continue
                    relative = f.relative_to(source)
                    dest = target / relative
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    with f.open('rb') as inp, dest.open('xb') as out:
                        shutil.copyfileobj(inp, out, length=1024*1024)
            if not (self.root / 'catalog/projects').exists():
                self.init_catalog()
            self.catalog_save({'id': plan['id'], 'title': plan['id'].replace('-', ' ').title(),
                               'status': 'demonstracao', 'category': 'aplicativo',
                               'url': '/' + plan['dest'] + '/', 'summary': 'Projeto importado para revisão local.',
                               'expected_sha256': None})
        except Exception:
            shutil.rmtree(target)
            raise
        self.last_validation = None
        self.validation_fingerprint = None
        return {'message': f"Projeto {plan['id']} importado para {plan['dest']} e adicionado ao catálogo, sem Git push.", 'plan': plan}

    def structure(self) -> dict:
        """Mapa declarativo do site em uso: páginas, módulos, projetos e relações."""
        nodes: list[dict] = [{'id': 'site', 'label': 'rogerioduarte.org', 'kind': 'site',
                              'path': 'index.html', 'url': '/'}]
        edges: list[dict] = []
        node_ids = {'site'}

        def add(node: dict, parent: str | None = None):
            if node['id'] in node_ids:
                return
            nodes.append(node)
            node_ids.add(node['id'])
            if parent:
                edges.append({'source': parent, 'target': node['id'], 'kind': 'hierarchy'})

        files = self.file_items()
        html_pages = sorted(x['path'] for x in files if x['path'].lower().endswith(('.html', '.htm')))
        add({'id': 'group:projects', 'label': 'Projetos', 'kind': 'group', 'path': '', 'url': ''}, 'site')
        for path in html_pages[:120]:
            if path == 'index.html':
                continue
            rel = path.removesuffix('/index.html')
            title = 'Laboratório 3D' if path == 'laboratorio/index.html' else (
                'Telemedicina' if path == 'projetos/telemedicina/index.html' else
                rel.split('/')[-1].replace('-', ' ').title())
            url = '/' + (rel + '/' if path.endswith('/index.html') else path)
            parent = 'group:projects' if path.startswith('projetos/') else 'site'
            add({'id': 'page:' + path, 'label': title, 'kind': 'page', 'path': path, 'url': url}, parent)

        manifest_path = self.root / 'modules/manifest.json'
        if manifest_path.is_file():
            try:
                manifest = json.loads(manifest_path.read_text('utf-8'))
                for mod in manifest.get('modules', []):
                    ident = mod.get('id', '')
                    source = (mod.get('src', '') or '').removeprefix('./')
                    if not ID_RE.fullmatch(ident) or not source:
                        continue
                    parent = 'page:laboratorio/index.html' if 'page:laboratorio/index.html' in node_ids else 'site'
                    add({'id': 'module:' + ident, 'label': ident.title(), 'kind': 'module',
                         'path': source, 'url': '/laboratorio/'}, parent)
                for link in manifest.get('links', []):
                    if isinstance(link, list) and len(link) == 2:
                        a, b = 'module:' + str(link[0]), 'module:' + str(link[1])
                        if a in node_ids and b in node_ids:
                            edges.append({'source': a, 'target': b, 'kind': 'spatial'})
            except (ValueError, UnicodeError, OSError):
                pass
        for project in self.catalog()['projects'][:90]:
            ident = project.get('id')
            if not isinstance(ident, str) or not ID_RE.fullmatch(ident):
                continue
            url = project.get('url', '')
            if not isinstance(url, str) or not (url.startswith('/') and not url.startswith('//') or url.startswith('https://')):
                url = ''
            add({'id': 'project:' + ident, 'label': project.get('title', ident)[:100],
                 'kind': 'project', 'path': f'catalog/projects/{ident}.json', 'url': url}, 'group:projects')
            for neighbor in project.get('neighbors', [])[:20]:
                dest = 'project:' + str(neighbor)
                # Adicionado após todos os projetos abaixo.
                edges.append({'source': 'project:' + ident, 'target': dest, 'kind': 'catalog'})
        edges = [e for e in edges if e['source'] in node_ids and e['target'] in node_ids]
        return {'nodes': nodes, 'edges': edges, 'files': files,
                'counts': {'files': len(files), 'pages': len(html_pages),
                           'modules': sum(n['kind'] == 'module' for n in nodes),
                           'projects': sum(n['kind'] == 'project' for n in nodes),
                           'spatial_links': sum(e['kind'] == 'spatial' for e in edges)}}

    def _git_run(self, args: list[str], timeout: int = 55) -> str:
        env = os.environ.copy()
        # Não bloquear o servidor aguardando senha/prompt interativo.
        env['GIT_TERMINAL_PROMPT'] = '0'
        try:
            proc = subprocess.run(['git', *args], cwd=self.root, env=env,
                                  capture_output=True, text=True, timeout=timeout,
                                  encoding='utf-8', errors='replace')
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise StudioError(f'Git não concluiu a operação: {exc}', 503)
        if proc.returncode:
            reason = ((proc.stderr or '') + '\n' + (proc.stdout or '')).strip()[:2000]
            raise StudioError('Git: ' + reason, 409)
        return proc.stdout.strip()

    def _remote(self) -> str:
        if not is_git(self.root):
            raise StudioError('Esta cópia não é um repositório Git')
        url = self._git_run(['remote', 'get-url', 'origin'], timeout=10)
        if not url:
            raise StudioError('Remote origin não configurado')
        return url

    def sync_info(self) -> dict:
        origin = self._remote()
        branch = self._git_run(['branch', '--show-current'], timeout=10)
        local = self._git_run(['rev-parse', 'HEAD'], timeout=10)
        code, remote = cmd(['git', 'rev-parse', '--verify', 'refs/remotes/origin/main'], self.root)
        if code:
            return {'origin': origin, 'branch': branch, 'local': local, 'remote': '',
                    'ahead': None, 'behind': None, 'clean': not bool(self._git_run(['status','--porcelain=v1','--untracked-files=all'], timeout=10)),
                    'incoming': [], 'outgoing': [], 'message': 'Faça a primeira consulta ao GitHub.'}
        remote = remote.strip()
        ahead, behind = map(int, self._git_run(['rev-list','--left-right','--count','HEAD...refs/remotes/origin/main'], timeout=10).split())
        clean = not bool(self._git_run(['status','--porcelain=v1','--untracked-files=all'], timeout=10))
        incoming = self._git_run(['log','--oneline','-8','HEAD..refs/remotes/origin/main'], timeout=10).splitlines()
        outgoing = self._git_run(['log','--oneline','-8','refs/remotes/origin/main..HEAD'], timeout=10).splitlines()
        return {'origin': origin, 'branch': branch, 'local': local, 'remote': remote,
                'ahead': ahead, 'behind': behind, 'clean': clean,
                'incoming': incoming, 'outgoing': outgoing, 'message': ''}

    def sync_fetch(self) -> dict:
        remote = self._remote()
        if not (remote.startswith('git@github.com:') or remote.startswith('https://github.com/') or remote.startswith('ssh://git@github.com/')):
            raise StudioError('Origin não aponta para GitHub; revise no terminal antes de sincronizar')
        output = self._git_run(['fetch','--no-tags','origin','main'], timeout=90)
        r = self.sync_info()
        r['message'] = 'Referências do GitHub atualizadas; seus arquivos locais não foram alterados.'
        return r

    def sync_update(self, data: dict) -> dict:
        if data.get('confirm') != 'ATUALIZAR':
            raise StudioError('Confirme com ATUALIZAR')
        self.sync_fetch()
        info = self.sync_info()
        if not info['clean']:
            raise StudioError('Há arquivos modificados ou novos. Faça commit/backup antes de atualizar; nada foi alterado.', 409)
        if info['behind'] and info['ahead']:
            raise StudioError('Históricos divergentes: sincronização automática bloqueada. Inspecione o Git no terminal.', 409)
        if info['behind']:
            self._git_run(['merge','--ff-only','refs/remotes/origin/main'], timeout=60)
            self.last_validation = None
            self.validation_fingerprint = None
        updated = self.sync_info()
        updated['message'] = 'Cópia local atualizada por fast-forward.' if info['behind'] else 'A cópia local já contém a versão remota.'
        return updated

    def sync_publish(self, data: dict) -> dict:
        if data.get('confirm') != 'PUBLICAR':
            raise StudioError('Confirme com PUBLICAR')
        origin = self._remote()
        if not (origin.startswith('git@github.com:') or origin.startswith('https://github.com/') or origin.startswith('ssh://git@github.com/')):
            raise StudioError('Publicação exige remote GitHub verificado')
        branch = self._git_run(['branch','--show-current'], timeout=10)
        if not branch.startswith('studio/'):
            raise StudioError('Publicação só é permitida a partir de uma branch studio/ de teste')
        if self.validation_fingerprint != self.fingerprint() or not self.last_validation or self.last_validation['errors']:
            raise StudioError('Execute a vistoria aprovada imediatamente antes de publicar')
        if self._git_run(['status','--porcelain=v1','--untracked-files=all'], timeout=10):
            raise StudioError('Arquivos não commitados: faça stage e commit antes do push')
        local_before = self._git_run(['rev-parse','HEAD'], timeout=10)
        expected = data.get('expected_head')
        if expected != local_before:
            raise StudioError('HEAD mudou desde a confirmação. Atualize a tela e confira novamente.', 409)
        if data.get('expected_origin') != origin:
            raise StudioError('Remote origin diferente do apresentado; atualize a tela.', 409)
        expected_remote = data.get('expected_remote')
        self.sync_fetch()
        info = self.sync_info()
        if expected_remote != info['remote']:
            raise StudioError('A versão remota mudou desde a última consulta; publicação interrompida.', 409)
        if info['behind'] or info['ahead'] is None:
            raise StudioError('Seu trabalho não incorpora origin/main; atualize ou reconcilie antes de publicar.', 409)
        if not info['ahead']:
            return {'message': 'Nenhum commit novo para publicar.', 'status': info}
        if info['local'] != local_before:
            raise StudioError('HEAD local mudou durante a verificação.', 409)
        stamp = datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S-%f')
        tag = f'site-pre-rdstudio-{stamp}'
        self._git_run(['tag', tag, info['remote']], timeout=10)
        self._git_run(['push','origin',f'refs/tags/{tag}'], timeout=90)
        self._git_run(['push','origin','HEAD:refs/heads/main'], timeout=90)
        return {'message': f'Push efetuado sem force. Backup remoto: {tag}.', 'status': self.sync_info(), 'backup_tag': tag}

    def git(self):
        if not is_git(self.root):
            return {'enabled': False, 'status': [], 'branch': '', 'head': '', 'commits': [], 'stat': ''}
        _, raw = cmd(['git', 'status', '--porcelain=v1', '--untracked-files=all'], self.root)
        statuses = []
        for line in raw.splitlines():
            if len(line) >= 4:
                statuses.append({'state': line[:2], 'path': line[3:]})
        _, branch = cmd(['git', 'branch', '--show-current'], self.root)
        _, head = cmd(['git', 'rev-parse', '--short', 'HEAD'], self.root)
        _, stat = cmd(['git', 'diff', '--stat'], self.root)
        _, commits = cmd(['git', 'log', '-6', '--pretty=format:%h  %s'], self.root)
        return {'enabled': True, 'status': statuses, 'branch': branch.strip(), 'head': head.strip(), 'stat': stat.strip(), 'commits': commits.splitlines()}

    def git_diff(self, rel: str) -> str:
        self.resolve(rel, allow_missing=True)
        if not is_git(self.root):
            return 'Sem repositório Git.'
        _, text = cmd(['git', 'diff', '--', rel], self.root)
        return text or 'Sem diferenças não adicionadas ao stage (arquivo novo ou já adicionado).'

    def stage(self, paths: list[str]):
        if not is_git(self.root):
            raise StudioError('O projeto atual não é um repositório Git')
        if not isinstance(paths, list) or not paths or len(paths) > 650:
            raise StudioError('Selecione até 650 arquivos (publicações grandes exigem vistoria)')
        for rel in paths:
            self.resolve(rel, allow_missing=True)
        code, msg = cmd(['git', 'add', '-A', '--', *paths], self.root)
        if code:
            raise StudioError('git add: ' + msg)
        code, msg = cmd(['git', 'diff', '--cached', '--check'], self.root)
        if code:
            raise StudioError('Stage criado, mas git diff --check encontrou problemas:\n' + msg)
        return {'message': 'Arquivos adicionados ao stage. Nenhum commit ou push foi executado.'}

    def commit(self, d: dict):
        if d.get('confirm') != 'COMMIT':
            raise StudioError('Digite COMMIT para confirmar')
        message = (d.get('message') or '').strip()
        if not 8 <= len(message) <= 150 or '\n' in message:
            raise StudioError('Mensagem de commit deve ter entre 8 e 150 caracteres, em uma linha')
        if self.validation_fingerprint != self.fingerprint() or not self.last_validation or self.last_validation.get('errors'):
            raise StudioError('Execute e aprove a vistoria novamente antes do commit')
        if not is_git(self.root):
            raise StudioError('Repositório Git não encontrado')
        code, _ = cmd(['git', 'diff', '--cached', '--quiet'], self.root)
        if code == 0:
            raise StudioError('Nenhuma alteração adicionada ao stage')
        code, out = cmd(['git', 'diff', '--cached', '--check'], self.root)
        if code:
            raise StudioError('git diff --cached --check: ' + out)
        code, out = cmd(['git', 'commit', '-m', message], self.root, timeout=45)
        if code:
            raise StudioError('Falha no commit: ' + out)
        self.last_validation = None
        self.validation_fingerprint = None
        return {'message': out.strip()[:3000] + '\nCommit local criado; nenhum push efetuado.'}

    def validate(self) -> dict:
        errors: list[str] = []
        warnings: list[str] = []
        ok: list[str] = []

        def check(condition, good, bad, severity='error'):
            if condition:
                ok.append(good)
            else:
                (errors if severity == 'error' else warnings).append(bad)

        check((self.root / 'index.html').is_file(), 'Página inicial encontrada', 'index.html ausente')
        manifestfile = self.root / 'modules/manifest.json'
        if manifestfile.is_file():
            try:
                manifest = json.loads(manifestfile.read_text('utf-8'))
                mods = manifest.get('modules', [])
                ids = [x.get('id') for x in mods]
                check(len(ids) == len(set(ids)) and ids, f'{len(ids)} módulos únicos', 'Manifesto com IDs duplicados/vazios')
                for m in mods:
                    src = (m.get('src') or '').removeprefix('./')
                    try:
                        path = self.resolve(src)
                        ok.append(f'Módulo: {m.get("id")}')
                    except StudioError:
                        errors.append(f'Módulo ausente: {m.get("id")} / {src}')
                edges = set()
                for e in manifest.get('links', []):
                    if not isinstance(e, list) or len(e) != 2:
                        errors.append(f'Aresta inválida: {e!r}')
                        continue
                    a, b = e
                    pair = tuple(sorted((a, b)))
                    if a == b or a not in ids or b not in ids:
                        errors.append(f'Aresta com nós inválidos: {a} ↔ {b}')
                    if pair in edges:
                        errors.append(f'Aresta repetida: {a} ↔ {b}')
                    edges.add(pair)
                ok.append(f'{len(edges)} ligações declaradas no manifesto')
                graphfile = self.root / 'modules/graph.js'
                if graphfile.is_file():
                    pairs = {tuple(sorted(x)) for x in re.findall(r'\[\s*[\'\"]([\w-]+)[\'\"]\s*,\s*[\'\"]([\w-]+)[\'\"]\s*\]', graphfile.read_text('utf-8'))}
                    if pairs and pairs != edges:
                        warnings.append('modules/graph.js difere de modules/manifest.json (fonte utilizada pelo motor)')
                if set(ids) >= {'nucleo', 'saude', 'telemedicina'}:
                    for a, b in [('nucleo', 'telemedicina'), ('saude', 'telemedicina'), ('sistemas', 'telemedicina')]:
                        check(tuple(sorted([a, b])) in edges, f'Ligação {a} ↔ {b}', f'Falta ligação {a} ↔ {b}', 'warning')
                for m in ids:
                    modulefile=self.root/f'modules/{m}.js'
                    raw=modulefile.read_text('utf-8') if modulefile.is_file() else ''
                    found=re.search(r'(?:\btexturePath|[\"\']texturePath[\"\'])\s*:\s*[\"\']([^\"\']+)',raw)
                    template=found.group(1).removeprefix('./') if found else None
                    for i in range(1, 13):
                        if template and '{n}' in template:
                            rel=template.replace('{n}',f'{i:02d}')
                        else:
                            rel = f'images/face-{i}.jpg' if m == 'nucleo' else f'assets/modules/{m}/face-{i:02d}.jpg'
                        if not (self.root / rel).is_file():
                            warnings.append(f'Textura ausente: {rel}')
                ok.append('Referências de texturas conferidas')
            except (ValueError, OSError, TypeError, AttributeError) as exc:
                errors.append('Manifesto inválido: ' + str(exc))
        else:
            warnings.append('Não foi encontrado modules/manifest.json; não é necessariamente um erro para outros projetos')

        # Links HTML, incluindo <base> e caminhos absolutos do site.
        scanned = 0
        for html in self.root.rglob('*.html'):
            if any(p in EXCLUDED for p in html.relative_to(self.root).parts) or html.is_symlink():
                continue
            scanned += 1
            if scanned > 500:
                warnings.append('Vistoria HTML limitada a 500 páginas')
                break
            try:
                parser = HTMLLinks()
                parser.feed(html.read_text('utf-8'))
                base = urljoin(html.resolve().as_uri(), parser.base) if parser.base else html.resolve().as_uri()
                for ref in parser.refs:
                    if ref.startswith('#') or ref.startswith('//'):
                        continue
                    target = urlsplit(ref)
                    if target.scheme and target.scheme != 'file':
                        continue
                    if ref.startswith('/') and not target.scheme:
                        candidate = self.root / unquote(target.path).lstrip('/')
                    else:
                        result = urlsplit(urljoin(base, ref))
                        if result.scheme != 'file':
                            continue
                        candidate = Path(unquote(result.path))
                    # Impede referências locais fora da raiz, mas não segue symlinks no checker.
                    if not candidate.is_relative_to(self.root):
                        warnings.append(f'Link local fora do projeto: {html.relative_to(self.root)} → {ref}')
                        continue
                    if not candidate.exists():
                        errors.append(f'Recurso ausente: {html.relative_to(self.root)} → {ref}')
                    elif candidate.is_dir() and not (candidate / 'index.html').is_file():
                        warnings.append(f'Diretório sem index.html: {html.relative_to(self.root)} → {ref}')
            except (ValueError, OSError, UnicodeError) as exc:
                errors.append(f'Falha ao ler {html.relative_to(self.root)}: {exc}')
        ok.append(f'{scanned} páginas HTML verificadas')

        home = self.root / 'index.html'
        if home.is_file():
            parser = HTMLLinks()
            parser.feed(home.read_text('utf-8'))
            for key in ['og:title', 'og:description', 'og:image', 'og:url']:
                check(bool(parser.ogs.get(key)), f'{key} presente', f'Falta {key} na página inicial', 'warning')
            image = parser.ogs.get('og:image', '')
            if image:
                parts = urlsplit(image)
                if parts.netloc in {'rogerioduarte.org', 'www.rogerioduarte.org'} and not (self.root / parts.path.lstrip('/')).is_file():
                    errors.append(f'Imagem OG não encontrada localmente: {parts.path}')

        projects = self.catalog()
        if projects['exists']:
            ids = [p.get('id') for p in projects['projects']]
            check(len(ids) == len(set(ids)), f'{len(ids)} projetos únicos no catálogo', 'IDs duplicados no catálogo')
            for p in projects['projects']:
                if p.get('status') not in {'rascunho', 'demonstracao', 'publicado'}:
                    errors.append(f'Estado inválido no catálogo: {p.get("id")}')
                for nbr in p.get('neighbors', []):
                    if nbr not in ids:
                        errors.append(f'Vizinho não existe: {p.get("id")} → {nbr}')
                if p.get('preview', '').startswith('/') and not (self.root / p['preview'].lstrip('/')).is_file():
                    warnings.append(f'Prévia ainda ausente: {p.get("id")} → {p["preview"]}')
            errors.extend(projects['errors'])
            edge_file = self.root / 'catalog/edges.json'
            if edge_file.is_file():
                try:
                    seen = set()
                    for e in json.loads(edge_file.read_text('utf-8')).get('edges', []):
                        pair = tuple(sorted([e['source'], e['target']]))
                        if pair[0] not in ids or pair[1] not in ids or pair[0] == pair[1] or pair in seen:
                            errors.append(f'Aresta inválida/duplicada no catálogo: {pair}')
                        seen.add(pair)
                    ok.append(f'{len(seen)} relações do catálogo verificadas')
                except (ValueError, KeyError, TypeError) as exc:
                    errors.append(f'catalog/edges.json: {exc}')
        result = {'errors': errors[:200], 'warnings': warnings[:200], 'ok': ok[:300], 'count': {'errors': len(errors), 'warnings': len(warnings), 'passed': len(ok)}}
        self.last_validation = result
        self.validation_fingerprint = self.fingerprint() if not errors else None
        return result


class ApiHandler(BaseHTTPRequestHandler):
    studio: Studio
    webroot: Path
    server_version = 'RDStudio/3.0'

    def log_message(self, fmt, *args):
        # Nenhum token nas mensagens de acesso.
        if not self.path.startswith('/api/state'):
            sys.stderr.write('[admin] ' + fmt % args + '\n')

    def _host_allowed(self):
        host = self.headers.get('Host', '')
        return host in {f'127.0.0.1:{self.studio.admin_port}', f'localhost:{self.studio.admin_port}'}

    def send_json(self, obj, status=200):
        payload = json.dumps(obj, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(payload)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Referrer-Policy', 'no-referrer')
        self.end_headers()
        self.wfile.write(payload)

    def html(self, name: str, mime: str):
        content = (self.webroot / name).read_bytes()
        if name == 'index.html':
            content = content.replace(b'__STUDIO_TOKEN__', json.dumps(self.studio.token).encode('utf-8'))
            content = content.replace(b'__PREVIEW_PORT__', str(self.studio.preview_port).encode())
        self.send_response(200)
        self.send_header('Content-Type', mime)
        self.send_header('Content-Length', str(len(content)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Referrer-Policy', 'no-referrer')
        self.send_header('X-Content-Type-Options', 'nosniff')
        if os.environ.get('RD_WORKSPACE_PARENT') == 'http://127.0.0.1:8877':
            self.send_header('Content-Security-Policy', 'frame-ancestors http://127.0.0.1:8877')
        else:
            self.send_header('X-Frame-Options', 'DENY')
        self.end_headers()
        self.wfile.write(content)

    def do_GET(self):
        if not self._host_allowed():
            return self.send_json({'error': 'Host não permitido'}, 403)
        parsed = urlsplit(self.path)
        route = parsed.path
        q = parse_qs(parsed.query)
        try:
            if route in ('/', '/index.html'):
                return self.html('index.html', 'text/html; charset=utf-8')
            if route == '/app.js':
                return self.html('app.js', 'application/javascript; charset=utf-8')
            if route == '/style.css':
                return self.html('style.css', 'text/css; charset=utf-8')
            if route == '/discover.js':
                return self.html('discover.js', 'application/javascript; charset=utf-8')
            if route == '/spatial.js':
                return self.html('spatial.js', 'application/javascript; charset=utf-8')
            if route == '/patches.js':
                return self.html('patches.js', 'application/javascript; charset=utf-8')
            if route == '/api/state':
                state = self.studio.git()
                return self.send_json({'root': str(self.studio.root), 'preview': f'http://127.0.0.1:{self.studio.preview_port}/', 'git': state, 'catalog': self.studio.catalog()})
            if route == '/api/files':
                return self.send_json({'files': self.studio.file_items(q.get('q', [''])[0])})
            if route == '/api/file':
                return self.send_json(self.studio.text_read(q.get('path', [''])[0]))
            if route == '/api/media/info':
                return self.send_json(self.studio.media_info(q.get('path', [''])[0]))
            if route == '/api/catalog':
                return self.send_json(self.studio.catalog())
            if route == '/api/git':
                return self.send_json(self.studio.git())
            if route == '/api/structure':
                return self.send_json(self.studio.structure())
            if route == '/api/spatial':
                return self.send_json(self.studio.spatial.overview())
            if route == '/api/recovery':
                return self.send_json(self.studio.spatial.restore_plan())
            if route == '/api/git/sync':
                return self.send_json(self.studio.sync_info())
            if route == '/api/git/diff':
                return self.send_json({'diff': self.studio.git_diff(q.get('path', [''])[0])})
            if route == '/api/discover/browse':
                return self.send_json(self.studio.discovery.browse(q.get('path', [''])[0]))
            if route == '/api/discover/inspect':
                path = self.studio.discovery.path(q.get('path',[''])[0])
                return self.send_json({'candidate': self.studio.discovery.summary(path)})
            if route == '/api/discover/running':
                return self.send_json(self.studio.discovery.running())
            if route == '/api/discover/capture/plan':
                return self.send_json(self.studio.discovery.capture_plan({'id':q.get('id',[''])[0]}))
            if route == '/api/discover/visual/plan':
                return self.send_json(self.studio.discovery.visual_plan({'id':q.get('id',[''])[0]}))
            if route == '/api/history':
                return self.send_json({'history': self.studio.history(q.get('path', [''])[0])})
            if route == '/api/patches':
                return self.send_json(self.studio.patches.available())
            if route == '/api/patches/remove/plan':
                return self.send_json(self.studio.patches.removal_plan(q.get('id',[''])[0]))
            raise StudioError('Rota não encontrada', 404)
        except StudioError as exc:
            return self.send_json({'error': str(exc)}, exc.status)
        except PatchError as exc:
            return self.send_json({'error': str(exc)}, 400)
        except Exception as exc:
            return self.send_json({'error': f'Erro interno: {type(exc).__name__}: {exc}'}, 500)

    def do_POST(self):
        if not self._host_allowed():
            return self.send_json({'error': 'Host não permitido'}, 403)
        origin = self.headers.get('Origin')
        if origin and origin not in {f'http://127.0.0.1:{self.studio.admin_port}', f'http://localhost:{self.studio.admin_port}'}:
            return self.send_json({'error': 'Origem proibida'}, 403)
        if self.headers.get('X-RD-Token') != self.studio.token:
            return self.send_json({'error': 'Token de sessão inválido'}, 403)
        if not self.headers.get('Content-Type', '').startswith('application/json'):
            return self.send_json({'error': 'Content-Type JSON necessário'}, 415)
        try:
            length = int(self.headers.get('Content-Length', '-1'))
            if not 0 <= length <= MAX_BODY:
                return self.send_json({'error': 'Corpo muito grande'}, 413)
            data = json.loads(self.rfile.read(length))
            if not isinstance(data, dict):
                raise StudioError('Objeto JSON esperado')
            route = urlsplit(self.path).path
            routes = {
                '/api/file/save': lambda: self.studio.save_text(data),
                '/api/catalog/init': lambda: self.studio.init_catalog(),
                '/api/catalog/save': lambda: self.studio.catalog_save(data),
                '/api/validate': lambda: self.studio.validate(),
                '/api/upload': lambda: self.studio.asset_upload(data),
                '/api/history/restore': lambda: self.studio.restore(data),
                '/api/git/stage': lambda: self.studio.stage(data.get('paths')),
                '/api/git/commit': lambda: self.studio.commit(data),
                '/api/git/fetch': lambda: self.studio.sync_fetch(),
                '/api/git/update': lambda: self.studio.sync_update(data),
                '/api/git/publish': lambda: self.studio.sync_publish(data),
                '/api/import/plan': lambda: self.studio.import_plan(data),
                '/api/import/apply': lambda: self.studio.import_apply(data),
                '/api/discover/scan': lambda: self.studio.discovery.scan(data),
                '/api/discover/compare': lambda: self.studio.discovery.compare(data),
                '/api/discover/replace/plan': lambda: self.studio.discovery.replacement_plan(data),
                '/api/discover/replace/apply': lambda: self.studio.discovery.replacement_apply(data),
                '/api/discover/visual/apply': lambda: self.studio.discovery.visuals_apply(data),
                '/api/discover/capture/apply': lambda: self.studio.discovery.capture_apply(data),
                '/api/discover/portfolio/generate': lambda: self.studio.discovery.portfolio_generate(data),
                '/api/spatial/links': lambda: self.studio.spatial.save_links(data),
                '/api/spatial/position': lambda: self.studio.spatial.save_position(data),
                '/api/spatial/settings': lambda: self.studio.spatial.save_settings(data),
                '/api/spatial/mini/repair': lambda: self.studio.spatial.repair_minimap(data),
                '/api/spatial/expose': lambda: self.studio.spatial.expose(data),
                '/api/patches/plan': lambda: self.studio.patches.plan(data.get('name')),
                '/api/patches/apply': lambda: self.studio.patches.apply(data.get('name'), data.get('confirm')),
                '/api/patches/remove': lambda: self.studio.patches.remove(data.get('id'), data.get('confirm')),
                '/api/publish/plan': lambda: self.studio.spatial.publish_plan(),
                '/api/publish/apply': lambda: self.studio.spatial.publish_apply(data),
                '/api/recovery/apply': lambda: self.studio.spatial.restore_apply(data),
                '/api/recovery/fetch': lambda: self.studio.spatial.restore_fetch(),
            }
            if route not in routes:
                raise StudioError('Rota não encontrada', 404)
            return self.send_json(routes[route]())
        except StudioError as exc:
            return self.send_json({'error': str(exc)}, exc.status)
        except PatchError as exc:
            return self.send_json({'error': str(exc)}, 400)
        except (ValueError, TypeError) as exc:
            return self.send_json({'error': f'JSON inválido: {exc}'}, 400)
        except Exception as exc:
            return self.send_json({'error': f'Erro interno: {type(exc).__name__}: {exc}'}, 500)


class PreviewHandler(SimpleHTTPRequestHandler):
    studio: Studio
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(self.studio.root), **kwargs)

    def _allow(self) -> bool:
        if self.headers.get('Host', '') not in {f'127.0.0.1:{self.studio.preview_port}', f'localhost:{self.studio.preview_port}'}:
            self.send_error(403, 'Host não permitido')
            return False
        rawpath = unquote(urlsplit(self.path).path)
        parts = rawpath.split('/')
        if any(p in ('..', '.') or p.startswith('.') for p in parts if p):
            self.send_error(403, 'Caminho oculto ou inválido')
            return False
        current = self.studio.root
        for p in parts:
            if p:
                if p in EXCLUDED:
                    self.send_error(403, 'Diretório protegido')
                    return False
                current = current / p
                if current.is_symlink():
                    self.send_error(403, 'Links simbólicos proibidos')
                    return False
        return True

    def do_GET(self):
        if self._allow():
            super().do_GET()

    def do_HEAD(self):
        if self._allow():
            super().do_HEAD()

    def list_directory(self, path):
        self.send_error(403, 'Listagem de pastas desabilitada')
        return None

    def end_headers(self):
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Referrer-Policy', 'no-referrer')
        super().end_headers()


def handler_with_studio(cls, studio, **kwargs):
    return type(cls.__name__ + 'Bound', (cls,), {'studio': studio, **kwargs})


def main():
    parser = argparse.ArgumentParser(description='Editor e vistoria local RD Studio (somente 127.0.0.1)')
    parser.add_argument('--repo', required=True, type=Path, help='Caminho da cópia de teste do site')
    parser.add_argument('--port', type=int, default=8765, help='Porta do painel (8765)')
    parser.add_argument('--preview-port', type=int, default=8766, help='Porta da prévia isolada (8766)')
    args = parser.parse_args()
    if args.port == args.preview_port:
        parser.error('Administração e prévia exigem portas diferentes')
    studio = Studio(args.repo, args.port, args.preview_port)
    webroot = Path(__file__).parent / 'web'
    admin_cls = handler_with_studio(ApiHandler, studio, webroot=webroot)
    preview_cls = handler_with_studio(PreviewHandler, studio)
    with ThreadingHTTPServer(('127.0.0.1', args.preview_port), preview_cls) as preview, \
         ThreadingHTTPServer(('127.0.0.1', args.port), admin_cls) as admin:
        Thread(target=preview.serve_forever, daemon=True).start()
        print('\nRD Studio iniciado — acesso SOMENTE local')
        print('Painel:  http://127.0.0.1:%d/' % args.port)
        print('Prévia:  http://127.0.0.1:%d/' % args.preview_port)
        print('Projeto:', studio.root)
        print('Alterações do site: só sob comando; push exige PUBLICAR e vistoria.')
        print('Para encerrar: Ctrl+C\n', flush=True)
        try:
            admin.serve_forever()
        except KeyboardInterrupt:
            print('\nServidor encerrado.')
        finally:
            preview.shutdown()


if __name__ == '__main__':
    main()
