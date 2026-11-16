"""RD Studio: patches AI-localizados, instalação transacional e reversão por arquivo.
Somente arquivos declarados, não executa scripts incluídos no pacote.
"""
from __future__ import annotations
import hashlib
import difflib
import json
import os
import re
import tempfile
import time
import zipfile
from pathlib import Path, PurePosixPath

MAX_ARCHIVE = 12 * 1024 * 1024
MAX_FILE = 8 * 1024 * 1024
MAX_TOTAL = 18 * 1024 * 1024
ID_RE = re.compile(r'^[a-z][a-z0-9-]{2,90}$')
SHA_RE = re.compile(r'^[0-9a-f]{64}$')

class PatchError(Exception):
    pass

def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def safe_rel(rel: str) -> Path:
    if not isinstance(rel,str) or not rel or len(rel)>260 or '\\' in rel or '\x00' in rel:
        raise PatchError('Caminho de patch inválido')
    p=PurePosixPath(rel)
    if p.is_absolute() or any(x in ('','.','..') for x in rel.split('/')) or any(x.startswith('.') for x in p.parts):
        raise PatchError('Caminho relativo inseguro')
    if p.parts[0] in ('admin','patches','.github','.git','node_modules'):
        raise PatchError('Diretório protegido')
    if p.suffix.lower() not in ('.md','.html','.js','.json','.svg','.webp','.png','.jpg','.jpeg','.css','.txt','.mp4') and rel != 'scripts/build_editorial.py':
        raise PatchError('Tipo de arquivo não permitido para patches editoriais')
    return Path(*p.parts)

def atomic_write(path: Path, data: bytes):
    path.parent.mkdir(parents=True,exist_ok=True)
    fd,tmp=tempfile.mkstemp(prefix='.rdtmp-',dir=path.parent)
    try:
        with os.fdopen(fd,'wb') as f:
            f.write(data);f.flush();os.fsync(f.fileno())
        os.replace(tmp,path)
    finally:
        if os.path.exists(tmp):os.unlink(tmp)

class PatchManager:
    def __init__(self, root: Path):
        self.root=Path(root).resolve(strict=True)
        self.state=Path.home()/'.rd-studio'/'pacotes'/sha(str(self.root).encode())[:20]

    def _destination(self, rel):
        p=safe_rel(rel);out=self.root/p
        if not out.is_relative_to(self.root):raise PatchError('Caminho fora do site')
        q=self.root
        for part in p.parts:
            q=q/part
            if q.is_symlink():raise PatchError('Patch não pode modificar links simbólicos')
        if out.exists() and not out.is_file():raise PatchError('Destino não é arquivo')
        return out

    def _inbox_paths(self):
        return [Path.home()/'storage'/'downloads',Path('/sdcard/Download'),Path.home()/'rd-studio-patches'/'inbox']

    def archives(self):
        found={}
        for folder in self._inbox_paths():
            if not folder.is_dir():continue
            for p in folder.glob('*.rdpatch.zip'):
                if p.is_file() and not p.is_symlink() and p.stat().st_size<=MAX_ARCHIVE:
                    found.setdefault(p.name,p)
        return found

    def installed(self):
        out=[]
        if self.state.exists():
            for f in sorted(self.state.glob('*/installed.json')):
                try:
                    d=json.loads(f.read_text(encoding='utf8'))
                    out.append({'id':d['id'],'title':d.get('title',d['id']),'applied_at':d.get('applied_at'),'paths':[x['path'] for x in d['files']]})
                except (ValueError,KeyError):pass
        return out

    def available(self):
        out=[]
        for name,p in sorted(self.archives().items()):
            try:
                with zipfile.ZipFile(p) as z:
                    m=self._manifest(z)
                out.append({'name':name,'id':m['id'],'title':m['title'],'version':m['version'],'files':len(m['files'])})
            except (OSError,ValueError,zipfile.BadZipFile,PatchError,KeyError):
                out.append({'name':name,'invalid':True})
        return {'available':out,'installed':self.installed(),'repo':str(self.root)}

    def _archive(self,name):
        if not isinstance(name,str) or '/' in name or '\\' in name or not name.endswith('.rdpatch.zip'):
            raise PatchError('Nome do arquivo inválido')
        p=self.archives().get(name)
        if not p:raise PatchError('Pacote não encontrado em Downloads')
        return p

    def _manifest(self,z):
        infos=z.infolist()
        if len(infos)>90:raise PatchError('Pacote contém arquivos demais')
        names=[i.filename for i in infos]
        if len(names)!=len(set(names)):raise PatchError('Entrada duplicada no ZIP')
        if 'patch.json' not in names:raise PatchError('Manifesto patch.json ausente')
        for i in infos:
            if i.file_size>MAX_FILE or i.compress_size>MAX_ARCHIVE:
                raise PatchError('Arquivo excede o tamanho máximo')
            # reject symlinks in a zip; UNIX symlink mode is 0o120000
            if (i.external_attr >> 16) & 0o170000 == 0o120000:
                raise PatchError('Pacote contém links simbólicos')
        if sum(i.file_size for i in infos)>MAX_TOTAL:raise PatchError('Pacote excede limite de conteúdo')
        m=json.loads(z.read('patch.json'))
        if m.get('schema')!=1 or not ID_RE.fullmatch(m.get('id','')):
            raise PatchError('Identificador ou esquema inválido')
        if not isinstance(m.get('title'),str) or len(m['title'])>180 or not isinstance(m.get('version'),str):
            raise PatchError('Metadados inválidos')
        fs=m.get('files')
        if not isinstance(fs,list) or not fs or len(fs)>60:raise PatchError('Lista de arquivos inválida')
        seen=set()
        for item in fs:
            rel=item.get('path');safe_rel(rel)
            if rel in seen:raise PatchError('Caminho repetido no manifesto')
            seen.add(rel)
            if item.get('operation') not in ('add','replace'):raise PatchError('Operação não permitida')
            if not SHA_RE.fullmatch(item.get('sha256','')):raise PatchError('Hash de resultado inválido')
            allow=item.get('allowed_before_sha256',[])
            if item['operation']=='replace' and (not isinstance(allow,list) or not allow or not all(isinstance(v,str) and SHA_RE.fullmatch(v) for v in allow)):
                raise PatchError('Arquivo substituído exige hashes de origem')
            file_name='files/'+rel
            if file_name not in names:raise PatchError('Arquivo declarado ausente: '+rel)
            if sha(z.read(file_name))!=item['sha256']:raise PatchError('Hash não confere: '+rel)
        # MP4 legítimo: estrutura ISO BMFF com marca ftyp na posição padronizada.
        for item in fs:
            if item['path'].lower().endswith('.mp4'):
                blob=z.read('files/'+item['path'])
                if len(blob)<12 or blob[4:8]!=b'ftyp':
                    raise PatchError('Arquivo MP4 inválido: '+item['path'])
        extras=[n for n in names if not n.endswith('/') and n not in ('patch.json','README.md') and n not in {'files/'+x['path'] for x in fs}]
        if extras:raise PatchError('Pacote contém arquivos não declarados')
        return m

    def _stored(self,id):
        if not ID_RE.fullmatch(id):raise PatchError('ID inválido')
        p=self.state/id/'installed.json'
        return json.loads(p.read_text()) if p.is_file() else None

    def plan(self,name):
        p=self._archive(name)
        with zipfile.ZipFile(p) as z:
            m=self._manifest(z)
            payload={x['path']:z.read('files/'+x['path']) for x in m['files']}
        stored=self._stored(m['id'])
        results=[]
        for x in m['files']:
            dest=self._destination(x['path']); exists=dest.is_file()
            current=sha(dest.read_bytes()) if exists else None
            if x['operation']=='add':
                status='ready' if not exists else 'conflict'
            else:
                status='ready' if current in x['allowed_before_sha256'] else 'conflict'
            preview=''
            if dest.suffix.lower() in ('.md','.html','.py','.js','.css','.json','.svg','.txt'):
                try:
                    old_text=dest.read_text(encoding='utf-8') if exists else ''
                    new_text=payload[x['path']].decode('utf-8')
                    diff=difflib.unified_diff(old_text.splitlines(),new_text.splitlines(),fromfile='antes/'+x['path'],tofile='depois/'+x['path'],lineterm='')
                    preview='\n'.join(diff)[:15000]
                except UnicodeError:
                    preview='(arquivo de texto não decodificável)'
            results.append({'path':x['path'],'operation':x['operation'],'state':status,'before':current,'after':x['sha256'],'diff':preview})
        executable=[x['path'] for x in m['files'] if x['path'].endswith(('.js','.py'))]
        warnings=([f'O patch substitui código que poderá ser executado no site/gerador: {p}' for p in executable]
                  if executable else [])
        return {'name':name,'id':m['id'],'title':m['title'],'version':m['version'],'files':results,'ready':all(x['state']=='ready' for x in results) and not stored,'installed':bool(stored),'notes':m.get('notes',''),'warnings':warnings}

    def apply(self,name,confirm):
        if confirm!='APLICAR':raise PatchError('Confirmação APLICAR necessária')
        plan=self.plan(name)
        if not plan['ready']:raise PatchError('Conflito com a versão instalada ou arquivos já modificados; nenhuma alteração realizada')
        with zipfile.ZipFile(self._archive(name)) as z:
            m=self._manifest(z)
            payload={x['path']:z.read('files/'+x['path']) for x in m['files']}
        destdir=self.state/m['id']
        if destdir.exists():raise PatchError('Já existe estado deste pacote')
        destdir.mkdir(parents=True,exist_ok=False)
        records=[];applied=[]
        try:
            for x in m['files']:
                rel=x['path'];dest=self._destination(rel)
                previous=dest.read_bytes() if dest.exists() else None
                current=sha(previous) if previous is not None else None
                if x['operation']=='replace' and current not in x['allowed_before_sha256']:raise PatchError('Arquivo alterado durante instalação: '+rel)
                if x['operation']=='add' and previous is not None:raise PatchError('Arquivo surgiu durante instalação: '+rel)
                if previous is not None:
                    bp=destdir/'backups'/rel
                    atomic_write(bp,previous)
                atomic_write(dest,payload[rel]);applied.append((dest,previous))
                records.append({'path':rel,'operation':x['operation'],'before':current,'after':sha(payload[rel])})
            rec={'schema':1,'id':m['id'],'title':m['title'],'version':m['version'],'applied_at':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'files':records}
            atomic_write(destdir/'installed.json',json.dumps(rec,ensure_ascii=False,indent=2).encode('utf8'))
        except Exception:
            for dest,prev in reversed(applied):
                if prev is None:dest.unlink(missing_ok=True)
                else:atomic_write(dest,prev)
            import shutil
            shutil.rmtree(destdir,ignore_errors=True)
            raise
        return {'ok':True,'id':m['id'],'files':[r['path'] for r in records],'message':'Pacote instalado apenas no worktree; execute Vistoria e revisite o Git antes de publicar.'}

    def removal_plan(self,id):
        rec=self._stored(id)
        if not rec:raise PatchError('Pacote não instalado')
        out=[]
        for item in rec['files']:
            dest=self._destination(item['path']);cur=sha(dest.read_bytes()) if dest.is_file() else None
            status='ready' if cur==item['after'] else 'conflict'
            out.append({'path':item['path'],'operation':'restore' if item['before'] else 'remove','state':status})
        return {'id':id,'title':rec['title'],'files':out,'ready':all(x['state']=='ready' for x in out)}

    def remove(self,id,confirm):
        if confirm!='REMOVER':raise PatchError('Confirmação REMOVER necessária')
        plan=self.removal_plan(id)
        if not plan['ready']:raise PatchError('Arquivo alterado depois da instalação; remoção bloqueada para preservar edições')
        rec=self._stored(id);staged=[]
        try:
            for r in rec['files']:
                dest=self._destination(r['path'])
                previous=dest.read_bytes()
                if sha(previous)!=r['after']:raise PatchError('Alteração concorrente em '+r['path'])
                if r['before']:
                    bp=self.state/id/'backups'/r['path'];data=bp.read_bytes()
                    if sha(data)!=r['before']:raise PatchError('Backup não confere')
                    atomic_write(dest,data)
                else:dest.unlink()
                staged.append((dest,previous))
        except Exception:
            for dest,content in reversed(staged):atomic_write(dest,content)
            raise
        import shutil
        shutil.rmtree(self.state/id)
        return {'ok':True,'id':id,'files':[x['path'] for x in rec['files']],'message':'Arquivos restaurados no worktree. Se o patch foi publicado, faça um NOVO commit e push para reverter no site remoto.'}
