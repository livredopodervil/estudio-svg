"""Recupera somente mídias de instâncias que importadores legados ignoram.
Nenhum arquivo existente é substituído. Nunca extrai caminhos não referenciados.
"""
from pathlib import Path
import json, re, zipfile, io, os
from PIL import Image

IDENT = re.compile(r'^[A-Za-z0-9_.-]{1,100}$')
SUPPORTED = {'.jpg','.jpeg','.png','.webp'}
MAX_IMAGE_BYTES=12_000_000

def restore_instance_media(bundle, media_root):
    media_root=Path(media_root)
    if media_root.is_symlink() or not media_root.is_dir():raise ValueError('Pasta de mídias insegura')
    restored=[]
    with zipfile.ZipFile(bundle) as z:
        projects=[x for x in z.namelist() if x.startswith('projetos/') and x.endswith('.json') and x.count('/')==1]
        if len(projects)!=1:return restored
        project=json.loads(z.read(projects[0]))
        defs=(project.get('instance_library') or {}).get('definitions',[])
        if not isinstance(defs,list) or len(defs)>64:raise ValueError('Biblioteca de instâncias inválida no ZIP')
        refs=set()
        for d in defs:
            if not isinstance(d,dict) or d.get('kind')!='media':continue
            media=d.get('media') or {}
            if media.get('kind')!='image':continue
            name=media.get('file','')
            if not isinstance(name,str) or not IDENT.fullmatch(name) or Path(name).suffix.lower() not in SUPPORTED:
                raise ValueError('Nome de imagem de instância inseguro')
            refs.add(name)
        for name in sorted(refs):
            member='midia/'+name
            if member not in z.namelist():continue
            out=media_root/name
            if out.is_symlink():raise ValueError('Mídia existente é symlink: '+name)
            if out.exists():continue
            info=z.getinfo(member)
            if info.file_size<=0 or info.file_size>MAX_IMAGE_BYTES:raise ValueError('Imagem de instância muito grande: '+name)
            data=z.read(member)
            if len(data)>MAX_IMAGE_BYTES:raise ValueError('Imagem de instância muito grande')
            with Image.open(io.BytesIO(data)) as im:
                im.verify()
            try:
                with out.open('xb') as stream:
                    stream.write(data);stream.flush();os.fsync(stream.fileno())
            except FileExistsError:continue
            restored.append(name)
    return restored
