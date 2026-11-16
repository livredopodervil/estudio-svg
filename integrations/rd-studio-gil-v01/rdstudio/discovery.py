#!/usr/bin/env python3
"""Discovery: inventário de projetos do HOME, versões e publicações locais.

Sem execução de projetos de terceiros. Escopo de leitura: HOME, sem symlinks,
com limites de profundidade/quantidade e bloqueio de pastas confidenciais.
Escrita: apenas no worktree de teste já autorizado pelo RD Studio.
"""
from __future__ import annotations

from datetime import datetime, timezone
from difflib import unified_diff
from html.parser import HTMLParser
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import tempfile
import time
from urllib.parse import urlsplit, unquote

AVOID = {'.git', '.ssh', '.gnupg', '.config', '.local', '.cache', '.npm', '.termux',
         '.aws', '.kube', '.docker', '.rd-studio', 'node_modules', 'vendor',
         '.venv', 'venv', 'env', '__pycache__', '.next', '.nuxt', '.gradle',
         'site-packages', 'target', 'coverage', 'tmp', 'temp', 'proc', 'sys',
         'storage', 'rd-studio-backups', 'rd-studio'}
PROTECTED_NAMES = {'.env', '.env.local', '.env.production', 'credentials.json',
                   'secrets.json', 'id_rsa', 'id_ed25519', 'key.pem', 'config.json',
                   'service-account.json'}
ALLOWED_FILES = {'.html', '.htm', '.css', '.js', '.mjs', '.json', '.md', '.txt',
                 '.yml', '.yaml', '.xml', '.svg', '.png', '.jpg', '.jpeg',
                 '.webp', '.gif', '.ico', '.pdf', '.woff', '.woff2', '.ttf', '.otf',
                 '.wasm', '.webmanifest', '.mp3', '.ogg', '.mp4'}
TEXT_FILES = {'.html', '.htm', '.js', '.json', '.md', '.css', '.txt', '.svg', '.yml', '.yaml'}
IMAGE_FILES = {'.png', '.jpg', '.jpeg', '.webp'}
MAX_FILES = 600
MAX_BYTES = 80_000_000
MAX_SCAN_DIRS = 1800
MAX_SCAN_TIME = 12.0
ID_PATTERN = re.compile(r'^[a-z0-9][a-z0-9-]{0,70}$')
VERSION_RE = re.compile(r'(?:[-_. ]+(?:v(?:er(?:s(?:ion)?)?)?|versao|release|build|teste|test|backup|old|novo|final|copy|copia|prod|dev))[-_. ]*\d*(?:[._-]\d+)*$', re.I)


def digest(text):
    return hashlib.sha256(text).hexdigest()


class PageMeta(HTMLParser):
    def __init__(self):
        super().__init__()
        self.title = ''
        self.description = ''
        self.ogimage = ''
        self.icon = ''
        self._in_title = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'title': self._in_title = True
        if tag == 'meta':
            key = attrs.get('property', attrs.get('name', '')).lower()
            if key in ('description', 'og:description'): self.description = attrs.get('content', '')[:250]
            if key == 'og:image': self.ogimage = attrs.get('content', '')
        if tag == 'link' and 'icon' in attrs.get('rel', '').lower():
            self.icon = attrs.get('href', '')

    def handle_endtag(self, tag):
        if tag == 'title': self._in_title = False

    def handle_data(self, data):
        if self._in_title: self.title += data[:200]


def clean_slug(text):
    value = re.sub(r'[^a-z0-9]+', '-', text.lower()).strip('-')
    return value[:65] or 'aplicativo'


class Discovery:
    def __init__(self, studio, error_type):
        self.studio = studio
        self.fail_type = error_type
        self.home = Path.home().resolve()
        self.root = studio.root
        self.backups = self.home / '.rd-studio' / 'substituicoes' / digest(str(self.root).encode())[:12]

    def fail(self, message, status=400):
        raise self.fail_type(message, status)

    def path(self, raw, *, must_dir=True, allow_home=True):
        if raw is None or raw == '': raw = str(self.home)
        if not isinstance(raw, str) or len(raw) > 1400 or '\x00' in raw:
            self.fail('Caminho inválido')
        raw_path = Path(raw).expanduser()
        # Identifica symlinks antes de resolver para impedir entradas que escapem.
        if not raw_path.is_absolute():
            raw_path = self.home / raw_path
        if '..' in raw_path.parts:
            self.fail('Caminhos com .. não são permitidos')
        # Verifica componentes inseridos pelo usuário ANTES de resolver symlinks.
        if raw_path.is_relative_to(self.home):
            component_path=self.home
            for part in raw_path.relative_to(self.home).parts:
                component_path=component_path/part
                if component_path.is_symlink():self.fail('Não é permitido navegar por links simbólicos')
        try:
            target = raw_path.resolve(strict=True)
        except (OSError, RuntimeError):
            self.fail('Diretório não encontrado', 404)
        if not target.is_relative_to(self.home) or (target == self.home and not allow_home):
            self.fail('A navegação fica restrita à pasta HOME do Termux')
        relative = target.relative_to(self.home)
        if any(part in AVOID or part.startswith('.') for part in relative.parts):
            self.fail('Diretório privado, oculto ou protegido')
        # Recusa qualquer parte da rota que seja link simbólico.
        cursor = self.home
        for part in relative.parts:
            cursor = cursor / part
            if cursor.is_symlink():
                self.fail('Links simbólicos não são navegáveis')
        if must_dir and not target.is_dir():
            self.fail('Selecione um diretório')
        return target

    def browse(self, raw=''):
        folder = self.path(raw)
        items = []
        try:
            children = sorted(folder.iterdir(), key=lambda p: (not p.is_dir(), p.name.casefold()))
        except OSError as exc:
            self.fail('Não foi possível abrir a pasta: '+str(exc))
        for item in children[:700]:
            if item.is_symlink() or item.name.startswith('.') or item.name in AVOID or item.name in PROTECTED_NAMES:
                continue
            try:
                st = item.stat()
                if not (item.is_dir() or item.suffix.lower() in ALLOWED_FILES or item.name in {'package.json','Dockerfile'}):
                    continue
            except OSError:
                continue
            items.append({'name':item.name,'path':str(item),'dir':item.is_dir(),
                          'bytes':st.st_size if item.is_file() else None,
                          'candidate':item.is_dir() and (item/'index.html').is_file(),
                          'mtime':int(st.st_mtime)})
        return {'path':str(folder),'parent':str(folder.parent) if folder != self.home else None,
                'items':items,'total_shown':len(items), 'truncated':len(children)>700,
                'home':str(self.home)}

    def _page(self, path):
        p = path / 'index.html'
        out = PageMeta()
        if p.is_file() and not p.is_symlink():
            try: out.feed(p.read_text('utf-8', errors='replace')[:250_000])
            except OSError: pass
        return out

    def summary(self, folder):
        names = set()
        try: names = {p.name for p in folder.iterdir() if not p.is_symlink() and not p.name.startswith('.')}
        except OSError: pass
        static = 'index.html' in names
        node = 'package.json' in names
        python = 'pyproject.toml' in names or 'requirements.txt' in names or any(x in names for x in ('app.py','server.py','main.py'))
        other = 'Dockerfile' in names or 'docker-compose.yml' in names
        if not (static or node or python or other): return None
        page = self._page(folder)
        title = page.title.strip() or folder.name.replace('-', ' ').replace('_',' ')
        kind = 'site HTML' if static else ('app Node' if node else ('app Python' if python else 'container'))
        version_match = re.search(r'(?:[-_ ]v|[-_]version|[-_]build)[-_. ]*(\d+(?:[._-]\w+)*)', folder.name, re.I)
        version = version_match.group(1) if version_match else ''
        key = clean_slug(VERSION_RE.sub('', folder.name))
        # Nome canônico pelo diretório prevalece, não agrupar projetos distintos só por títulos iguais.
        git = (folder/'.git').is_dir() or (folder/'.git').is_file()
        return {'path':str(folder),'name':folder.name,'title':title[:150],
                'id_suggested':key,'group':key,'version_hint':version,'kind':kind,
                'static':static,'node':node,'python':python,'git':git,
                'description':page.description[:220], 'preview_image':page.ogimage or page.icon,
                'file':str(folder/'index.html') if static else '',
                'mtime':int(folder.stat().st_mtime)}

    def scan(self, data):
        root = self.path(data.get('root',''))
        depth = min(8,max(1,int(data.get('depth',4))))
        cutoff = time.monotonic()+MAX_SCAN_TIME
        queue = [(root,0)]
        candidates = []
        visited = 0
        limit = False
        while queue and visited < MAX_SCAN_DIRS and len(candidates)<350 and time.monotonic()<cutoff:
            current,d = queue.pop(0)
            if current.is_symlink(): continue
            visited+=1
            try:
                candidate = self.summary(current)
                if candidate: candidates.append(candidate)
                if d>=depth:continue
                children = sorted(current.iterdir(), key=lambda p:p.name.casefold())
                for p in children:
                    if p.is_dir() and not p.is_symlink() and not p.name.startswith('.') and p.name not in AVOID:
                        queue.append((p,d+1))
            except (OSError, PermissionError):
                continue
        if queue:limit=True
        groups={}
        for c in candidates:groups.setdefault(c['group'],[]).append(c)
        for g in groups.values():
            g.sort(key=lambda c:c['mtime'],reverse=True)
            for i,c in enumerate(g):
                c['group_count']=len(g)
                c['relative_recency']=i+1
        candidates.sort(key=lambda c:(-len(groups[c['group']]),c['group'],-c['mtime']))
        return {'root':str(root),'candidates':candidates,'total':len(candidates),
                'groups':len(groups),'visited_directories':visited,
                'truncated':limit,'depth':depth}

    def _files(self, source, *, allow_site=False):
        """Conjunto que pode ser importado, com mesma exclusão do importador v2.
        Inclui hashes para comparação e proteção contra mudanças entre plano e ação.
        """
        source = self.path(str(source),allow_home=False)
        if source.is_relative_to(self.root) and not allow_site: self.fail('Não use a própria pasta do site como origem')
        records={}
        total=0
        for folder,dirs,files in os.walk(source,followlinks=False):
            dirs[:]=sorted(d for d in dirs if not d.startswith('.') and d not in AVOID and not (Path(folder)/d).is_symlink())
            for name in sorted(files):
                f=Path(folder)/name
                if f.is_symlink() or name.startswith('.') or name in PROTECTED_NAMES or f.suffix.lower() not in ALLOWED_FILES:
                    continue
                stat=f.stat();total+=stat.st_size
                if len(records)>=MAX_FILES or total>MAX_BYTES:
                    self.fail('Limite de importação: 600 arquivos / 80 MB; escolha pasta mais específica')
                if stat.st_size>25_000_000: self.fail('Arquivo individual acima de 25 MB')
                name_rel=f.relative_to(source).as_posix()
                h=hashlib.sha256()
                with f.open('rb') as inp:
                    for block in iter(lambda:inp.read(256*1024),b''):h.update(block)
                records[name_rel]={'bytes':stat.st_size,'sha256':h.hexdigest()}
        return records

    def compare(self, data):
        a=self.path(data.get('a'),allow_home=False)
        b=self.path(data.get('b'),allow_home=False)
        fa,fb=self._files(a,allow_site=True),self._files(b,allow_site=True)
        added=sorted(set(fb)-set(fa));removed=sorted(set(fa)-set(fb))
        changed=sorted(f for f in fa.keys()&fb.keys() if fa[f]['sha256']!=fb[f]['sha256'])
        same=len(fa.keys()&fb.keys())-len(changed)
        focus=data.get('focus','')
        if focus not in changed:focus=next((f for f in changed if Path(f).suffix.lower() in TEXT_FILES), '')
        diff=''
        if focus and Path(focus).suffix.lower() in TEXT_FILES:
            left,right=a/focus,b/focus
            if left.stat().st_size<180_000 and right.stat().st_size<180_000:
                diff=''.join(list(unified_diff(left.read_text('utf-8',errors='replace').splitlines(True),
                         right.read_text('utf-8',errors='replace').splitlines(True),
                         fromfile=str(a/focus),tofile=str(b/focus),n=3))[:250])[:18000]
        return {'a':str(a),'b':str(b),'added':added[:200],'removed':removed[:200],
                'changed':changed[:200],'unchanged':same,'focus':focus,'diff':diff,
                'total_a':len(fa),'total_b':len(fb)}

    def running(self):
        processes=[]
        # ps não revela sempre todos os processos em Android; informações são indicativas.
        try:
            r=subprocess.run(['ps','-ef'],capture_output=True,text=True,timeout=3)
            for line in r.stdout.splitlines()[1:]:
                bits=line.split(None,7)
                if len(bits)<8:continue
                pid=bits[1];command=bits[-1]
                if not re.search(r'python|node|npm|http-server|vite|php\s+-S|busybox\s+httpd|deno|bun|flask|uvicorn',command,re.I):continue
                # Nunca enviar argumentos completos (podem conter credenciais/tokens).
                match=re.search(r'(?:^|\s)(\d{2,5})(?:\s|$)',command)
                paths=re.findall(r'/data/data/com\.termux/files/home/[\w./-]+',command)
                safe_paths=[]
                for item in paths[:5]:
                    try:
                        x=self.path(item,must_dir=False,allow_home=False)
                        if x.is_file() or x.is_dir():safe_paths.append(str(x))
                    except Exception:pass
                processes.append({'pid':pid,'program':re.search(r'\b(python\w*|node|npm|vite|uvicorn|php|deno|bun)\b',command,re.I).group(0) if re.search(r'\b(python\w*|node|npm|vite|uvicorn|php|deno|bun)\b',command,re.I) else 'servidor',
                                  'paths':safe_paths,'port_hint':int(match.group(1)) if match else None})
                if len(processes)>=60:break
        except (OSError,subprocess.TimeoutExpired):pass
        ports=[]
        # Sockets TCP: somente handshake local; nenhum conteúdo HTTP é solicitado.
        options=[3000,3001,4173,4200,5000,5001,5173,5174,5500,8000,8001,8008,8080,8081,8082,8090,8091,8093,8094,8095,8765,8766,8875,8876,9000,9001,9090]
        # ss revela portas arbitrárias, não apenas a lista usual, quando permitido pelo Android.
        try:
            out=subprocess.run(['ss','-ltn'],capture_output=True,text=True,timeout=3)
            for line in out.stdout.splitlines()[1:]:
                if 'LISTEN' not in line:continue
                parts=line.split()
                for part in parts:
                    hit=re.search(r':(\d{1,5})$',part)
                    if hit:
                        port=int(hit.group(1))
                        if 0<port<=65535 and port not in options:options.append(port)
                        break
        except (OSError,subprocess.TimeoutExpired):pass
        options=options[:125]
        for port in options:
            with socket.socket(socket.AF_INET,socket.SOCK_STREAM) as sock:
                sock.settimeout(.085)
                try: active=sock.connect_ex(('127.0.0.1',port))==0
                except OSError:active=False
                if active:ports.append({'port':port,'url':f'http://127.0.0.1:{port}/','kind':'TCP (HTTP não confirmado)'})
        return {'processes':processes,'ports':ports,'note':'Atribuição entre processo e porta pode exigir inspeção manual. Outras portas não são enumeradas.'}

    def visual_plan(self, data):
        ident=data.get('id','')
        if not ID_PATTERN.fullmatch(ident): self.fail('ID inválido')
        root=self.root/'projetos'/ident
        if not root.is_dir() or root.is_symlink():self.fail('O projeto deve estar importado em projetos/ID/')
        page=self._page(root)
        candidates=[]
        og=page.ogimage
        if og:
            p=urlsplit(og)
            if not p.scheme and not og.startswith('//'):
                img=(root/unquote(p.path)).resolve()
                if img.is_relative_to(root) and img.is_file() and img.suffix.lower() in IMAGE_FILES:
                    candidates.append(str(img.relative_to(self.root)))
        for folder, dirs, files in os.walk(root,followlinks=False):
            dirs[:]=[d for d in dirs if not d.startswith('.') and d not in AVOID]
            for n in files:
                p=Path(folder)/n
                if p.is_symlink() or p.suffix.lower() not in IMAGE_FILES:continue
                if p.stat().st_size > 10_000_000:continue
                candidates.append(p.relative_to(self.root).as_posix())
            if len(candidates)>120:break
        candidates=list(dict.fromkeys(candidates))
        candidates.sort(key=lambda n:(0 if re.search(r'cover|preview|screenshot|capa|thumb|og-',n,re.I) else 1,n))
        pil=False
        try:from PIL import Image  # noqa: F401
        except ImportError:pass
        else:pil=True
        return {'id':ident,'title':page.title or ident.replace('-',' ').title(),
                'candidates':candidates[:70], 'default':candidates[0] if candidates else '',
                'pillow':pil,'outputs':[f'assets/previews/{ident}/thumbnail.webp' if pil else f'assets/previews/{ident}/thumbnail.svg',
                         f'assets/previews/{ident}/icon.png' if pil else f'assets/previews/{ident}/icon.svg'],
                'method':'imagem existente' if candidates else 'arte tipográfica (não screenshot)',
                'screenshot_available':bool(shutil.which('chromium') or shutil.which('chromium-browser') or shutil.which('google-chrome'))}

    @staticmethod
    def synthetic(title, square=False):
        import html
        label=html.escape(title[:42])
        w,h=(400,400) if square else (1200,675)
        return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">
<defs><linearGradient id="a" x2="1" y2="1"><stop stop-color="#063f57"/><stop offset="1" stop-color="#098b9d"/></linearGradient></defs>
<rect width="{w}" height="{h}" rx="16" fill="url(#a)"/>
<circle cx="{int(w*.81)}" cy="{int(h*.24)}" r="{int(min(w,h)*.26)}" fill="#97d7c6" opacity=".20"/>
<circle cx="{int(w*.87)}" cy="{int(h*.75)}" r="{int(min(w,h)*.18)}" fill="#ffffff" opacity=".10"/>
<path d="M 32 {h-62} H {w-32}" stroke="#b4e6b0" stroke-width="3"/>
<text x="32" y="{int(h*.54)}" fill="#fff" font-family="Arial,sans-serif" font-weight="700" font-size="{42 if square else 63}">{label}</text>
<text x="32" y="{h-29}" fill="#b8e8e6" font-size="{16 if square else 23}" font-family="Arial,sans-serif">ROGERIODUARTE.ORG / PORTFÓLIO</text>
</svg>'''.encode('utf-8')

    def visuals_apply(self, data):
        if data.get('confirm')!='GERAR':self.fail('Confirme com GERAR')
        plan=self.visual_plan(data)
        ident=plan['id'];source=data.get('source') or ''
        if source and source not in plan['candidates']:self.fail('Imagem não pertence ao aplicativo escolhido')
        if not source:source=plan['default']
        title=(data.get('title') or plan['title'])[:90]
        output=f'assets/previews/{ident}'
        self.studio.resolve(output+'/dummy.svg',allow_missing=True)
        generated=[]
        if plan['pillow'] and source:
            from PIL import Image, ImageOps
            with Image.open(self.root/source) as im:
                im=ImageOps.exif_transpose(im).convert('RGB')
                thumb=ImageOps.fit(im,(1200,675),Image.Resampling.LANCZOS,centering=(.5,.5))
                icon=ImageOps.fit(im,(400,400),Image.Resampling.LANCZOS)
                with tempfile.TemporaryDirectory() as temp:
                    x=Path(temp)
                    thumb.save(x/'thumb.webp','WEBP',quality=84,method=5)
                    icon.save(x/'icon.png','PNG',optimize=True)
                    for name,file in (('thumbnail.webp','thumb.webp'),('icon.png','icon.png')):
                        rel=f'{output}/{name}';self._save_generated(rel,(x/file).read_bytes());generated.append('/'+rel)
        else:
            if plan['pillow'] and not source:
                from PIL import Image,ImageDraw,ImageFont
                for name,size in [('thumbnail.webp',(1200,675)),('icon.png',(400,400))]:
                    im=Image.new('RGB',size,(8,88,111));d=ImageDraw.Draw(im)
                    d.ellipse((size[0]*.65,-size[1]*.3,size[0]*1.2,size[1]*.6),fill=(20,129,133))
                    # O texto pode usar fonte padrão; fallback SVG preserva acentos.
                    d.text((size[0]*.07,size[1]*.45),title[:25],fill=(255,255,255))
                    with tempfile.TemporaryDirectory() as temp:
                        p=Path(temp)/name;im.save(p)
                        rel=f'{output}/{name}';self._save_generated(rel,p.read_bytes());generated.append('/'+rel)
            else:
                for name,square in [('thumbnail.svg',False),('icon.svg',True)]:
                    rel=f'{output}/{name}';self._save_generated(rel,self.synthetic(title,square));generated.append('/'+rel)
        # Atualiza a prévia no registro, sem apagar demais atributos.
        rec=self.root/'catalog/projects'/f'{ident}.json'
        if rec.is_file():
            try:obj=json.loads(rec.read_text('utf-8'))
            except (OSError,ValueError):obj=None
            if isinstance(obj,dict):
                obj['preview']=generated[0]
                obj['icon']=generated[1]
                obj['preview_method']='imagem existente' if source else 'arte tipográfica'
                self.studio.atomic_write(f'catalog/projects/{ident}.json',
                    (json.dumps(obj,ensure_ascii=False,indent=2)+'\n').encode(),
                    hashlib.sha256(rec.read_bytes()).hexdigest(),allowed_suffixes={'.json'})
        return {'id':ident,'generated':generated,'source':source,
                'message':'Miniatura e ícone gerados na cópia local; podem ser substituídos no editor de mídias.'}

    def _save_generated(self,rel,data):
        p=self.studio.resolve(rel,allow_missing=True)
        old=hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None
        self.studio.atomic_write(rel,data,old,allowed_suffixes={'.svg','.webp','.png'})

    def replacement_plan(self,data):
        ident=data.get('id','');src=data.get('source')
        if not ID_PATTERN.fullmatch(ident):self.fail('ID inválido')
        source=self.path(src,allow_home=False)
        if source.is_relative_to(self.root):self.fail('Origem não pode estar dentro do site')
        new=self._files(source)
        if 'index.html' not in new:self.fail('O novo aplicativo precisa de index.html na raiz')
        target=self.root/'projetos'/ident
        if not target.is_dir() or target.is_symlink():self.fail('Não existe versão instalada para substituir')
        old=self._site_files(target)
        added=sorted(set(new)-set(old));removed=sorted(set(old)-set(new))
        changed=sorted(k for k in new.keys()&old.keys() if new[k]['sha256']!=old[k]['sha256'])
        fingerprint=digest(json.dumps(new,sort_keys=True).encode())
        return {'id':ident,'source':str(source),'dest':f'projetos/{ident}',
                'added':added[:150],'removed':removed[:150],'changed':changed[:150],
                'same':len(old.keys()&new.keys())-len(changed),'files':len(new),
                'fingerprint':fingerprint,'backup_required':True}

    def _site_files(self,root):
        records={}
        total=0
        for folder,dirs,files in os.walk(root,followlinks=False):
            dirs[:]=[d for d in dirs if not d.startswith('.') and d not in AVOID and not (Path(folder)/d).is_symlink()]
            for name in files:
                p=Path(folder)/name
                if p.is_symlink() or name.startswith('.') or p.suffix.lower() not in ALLOWED_FILES:continue
                st=p.stat();total+=st.st_size
                if len(records)>=MAX_FILES or total>MAX_BYTES or st.st_size>25_000_000:
                    self.fail('Versão instalada excede o limite de backup (600 arquivos / 80 MB)')
                h=hashlib.sha256()
                with p.open('rb') as inp:
                    for block in iter(lambda:inp.read(256*1024),b''):h.update(block)
                records[p.relative_to(root).as_posix()]={'sha256':h.hexdigest()}
        return records

    def replacement_apply(self,data):
        ident=data.get('id','')
        if data.get('confirm')!=f'SUBSTITUIR {ident}':self.fail(f'Confirme exatamente SUBSTITUIR {ident}')
        plan=self.replacement_plan(data)
        if plan['fingerprint']!=data.get('fingerprint'):
            self.fail('Origem mudou desde o plano; solicite nova comparação',409)
        source=Path(plan['source']);target=self.root/plan['dest']
        parent=target.parent
        # A cópia preparada é privada dentro do worktree; backup fora do repositório.
        stage=Path(tempfile.mkdtemp(prefix='.rd-stage-',dir=parent))
        stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        backup=self.backups/ident/stamp
        original=None
        try:
            for rel in self._files(source):
                src=source/rel;dest=stage/rel;dest.parent.mkdir(parents=True,exist_ok=True)
                with src.open('rb') as inp,dest.open('wb') as out:
                    shutil.copyfileobj(inp,out,1024*1024)
            self.backups.mkdir(parents=True,exist_ok=True)
            backup.parent.mkdir(parents=True,exist_ok=True)
            # Guarda cópia anterior antes de qualquer substituição.
            shutil.copytree(target,backup,symlinks=True)
            original=parent/(f'.rd-old-{ident}-{stamp}')
            os.replace(target,original)
            try:os.replace(stage,target)
            except Exception:
                os.replace(original,target)
                original=None
                raise
            shutil.rmtree(original);original=None
            self.studio.last_validation=None
            self.studio.validation_fingerprint=None
            return {'id':ident,'backup':str(backup),
                    'message':'Versão substituída SOMENTE no worktree. Backup criado fora do repositório; rode Vistoria antes de commit.'}
        finally:
            if stage.exists():shutil.rmtree(stage)
            if original and original.exists() and not target.exists():os.replace(original,target)

    def capture_plan(self, data):
        ident=data.get('id','')
        if not ID_PATTERN.fullmatch(ident):self.fail('ID inválido')
        path=self.root/'projetos'/ident/'index.html'
        if not path.is_file():self.fail('Nenhuma página local em projetos/ID/index.html')
        browser=next((shutil.which(x) for x in ('chromium','chromium-browser','google-chrome','google-chrome-stable') if shutil.which(x)),None)
        url=f'http://127.0.0.1:{self.studio.preview_port}/projetos/{ident}/'
        return {'id':ident,'url':url,'browser':browser,'available':bool(browser),
                'target':f'assets/previews/{ident}/screenshot.png'}

    def capture_apply(self,data):
        if data.get('confirm')!='CAPTURAR':self.fail('Confirme com CAPTURAR')
        plan=self.capture_plan(data)
        if not plan['browser']:self.fail('Chromium headless não encontrado neste Termux. Use a geração a partir de imagens ou capture em um Linux com Chromium instalado.')
        ident=plan['id']
        with tempfile.TemporaryDirectory(prefix='rd-capture-') as temp:
            output=Path(temp)/'page.png'
            browser=plan['browser']
            args=[browser,'--headless','--disable-gpu','--hide-scrollbars',
                  '--disable-dev-shm-usage','--disable-extensions','--no-first-run',
                  '--no-default-browser-check','--window-size=1200,675',
                  '--virtual-time-budget=3500','--user-data-dir='+str(Path(temp)/'chrome-profile'),
                  '--screenshot='+str(output),plan['url']]
            try:
                result=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=30)
            except (OSError,subprocess.TimeoutExpired) as exc:
                self.fail('Falha na captura: '+str(exc))
            if result.returncode!=0 or not output.is_file() or output.stat().st_size<100:
                self.fail('Chromium não conseguiu capturar a página: '+result.stderr.decode('utf-8',errors='replace')[-1200:])
            rel=plan['target'];self._save_generated(rel,output.read_bytes())
        rec=self.root/'catalog/projects'/f'{ident}.json'
        if rec.is_file():
            record=json.loads(rec.read_text('utf-8'))
            record['preview']='/'+rel;record['preview_method']='captura real Chromium'
            self.studio.atomic_write(f'catalog/projects/{ident}.json',
                (json.dumps(record,ensure_ascii=False,indent=2)+'\n').encode(),
                hashlib.sha256(rec.read_bytes()).hexdigest(),allowed_suffixes={'.json'})
        return {'path':'/'+rel,'message':'Captura real salva na cópia local e vinculada ao catálogo. Não houve publicação.'}

    def portfolio_generate(self,data):
        if data.get('confirm')!='GERAR PORTFOLIO':self.fail('Confirme com GERAR PORTFOLIO')
        import html
        listing=self.studio.catalog()
        projects=[x for x in listing['projects'] if x.get('status') in ('publicado','demonstracao')]
        # Inclui projetos já presentes sem inventar versões ou alterar seus conteúdos.
        registered={x.get('url','').rstrip('/') for x in projects}
        existing=self.root/'projetos/telemedicina/index.html'
        if existing.is_file() and '/projetos/telemedicina' not in registered:
            projects.append({'id':'telemedicina','title':'Telemedicina','summary':'Estudos técnicos e documentação do projeto.',
                             'status':'demonstracao','category':'Saúde digital','url':'/projetos/telemedicina/','preview':''})
        cards=[]
        for p in sorted(projects,key=lambda x:str(x.get('title','')).casefold()):
            url=p.get('url','')
            if not isinstance(url,str) or not (url.startswith('/') and not url.startswith('//') or url.startswith('https://')):continue
            preview=p.get('preview','')
            image=''
            if isinstance(preview,str) and preview.startswith('/') and not preview.startswith('//'):
                f=self.root/preview.lstrip('/')
                if f.is_file() and f.is_relative_to(self.root) and not f.is_symlink():
                    image=f'<img src="{html.escape(preview,quote=True)}" alt="Prévia de {html.escape(str(p.get("title","")),quote=True)}" loading="lazy">'
            if not image:image='<div class="placeholder">◇</div>'
            cards.append(f'''<article class="project">{image}<div class="content">
              <span class="tag">{html.escape(str(p.get('category','Projeto')))}</span>
              <h2>{html.escape(str(p.get('title',p.get('id','Projeto'))))}</h2>
              <p>{html.escape(str(p.get('summary',''))[:350])}</p>
              <a href="{html.escape(url,quote=True)}" rel="noopener">Abrir projeto ↗</a></div></article>''')
        page=f'''<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="index,follow">
<title>Projetos · Rogério Duarte</title><meta name="description" content="Catálogo de projetos, aplicativos e experimentos.">
<style>:root{{--cyan:#087e96;--ink:#163743;--green:#3f8865}}*{{box-sizing:border-box}}
body{{margin:0;background:#f7fafb;color:var(--ink);font:18px/1.6 Georgia,'EB Garamond',serif}}
a{{color:var(--cyan)}}header,main,footer{{max-width:1120px;padding:25px 20px;margin:auto}}
header{{display:flex;align-items:center;justify-content:space-between;gap:14px;border-bottom:1px solid #cfe7eb}}
header a{{font:600 13px system-ui;text-decoration:none}}h1,h2,.tag{{font-family:system-ui,sans-serif}}
h1{{font-size:clamp(36px,6vw,72px);letter-spacing:-.05em;line-height:1.12;margin:34px 0 15px}}
.lead{{max-width:720px;color:#52747c}}.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,290px),1fr));gap:23px;margin-top:30px}}
.project{{background:white;box-shadow:0 10px 35px #164a5810;border:1px solid #dcecef;border-radius:17px;overflow:hidden}}
.project img,.placeholder{{display:block;width:100%;aspect-ratio:16/9;object-fit:cover;background:linear-gradient(120deg,#e2f2f4,#daebe2)}}
.placeholder{{display:grid;place-items:center;color:var(--green);font:100px system-ui}}
.content{{padding:22px}}h2{{font-size:21px;margin:8px 0;letter-spacing:-.025em}}.content p{{color:#4e6972;min-height:60px;font-size:16px}}
.content a{{font:700 13px system-ui;text-decoration:none}}.tag{{font-size:10px;text-transform:uppercase;letter-spacing:.15em;color:var(--green);font-weight:700}}
footer{{border-top:1px solid #d9e7e8;margin-top:40px;color:#708891;font:12px system-ui}}
</style></head><body><header><a href="/">RD · ROGÉRIO DUARTE</a><nav><a href="/laboratorio/">Laboratório 3D</a></nav></header>
<main><p class="tag">Portfólio modular</p><h1>Projetos e experimentos.</h1>
<p class="lead">Ferramentas, estudos e aplicativos organizados para exploração independente.</p>
<div class="grid">{''.join(cards) if cards else '<p>Nenhum projeto público cadastrado ainda.</p>'}</div></main>
<footer>Rogério Duarte · Catálogo atualizado a partir dos registros do RD Studio</footer></body></html>'''
        path='projetos/index.html'
        target=self.studio.resolve(path,allow_missing=True)
        expected=digest(target.read_bytes()) if target.exists() else None
        self.studio.atomic_write(path,page.encode('utf-8'),expected,allowed_suffixes={'.html'})
        linked=False
        warning=''
        if data.get('link_home'):
            index=self.root/'index.html'
            old=index.read_text('utf-8')
            link='<a href="./projetos/">Portfólio</a>'
            if link in old:linked=True
            elif '<a href="#projetos">Projetos</a>' in old:
                new=old.replace('<a href="#projetos">Projetos</a>', '<a href="#projetos">Projetos</a>'+link,1)
                self.studio.atomic_write('index.html',new.encode('utf-8'),digest(old.encode('utf-8')),allowed_suffixes={'.html'})
                linked=True
            else:warning='A home tem outra estrutura; link não inserido automaticamente.'
        return {'projects':len(cards),'page':'/projetos/','linked_home':linked,'warning':warning,
                'message':f'Catálogo público gerado: {len(cards)} projeto(s). Apenas worktree local; prévia em /projetos/.'}
