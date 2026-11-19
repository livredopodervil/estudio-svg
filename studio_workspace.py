"""Read-only duration planning and project inventory; reversible archive of JSON.
Shared media remains immutable; no implicit garbage collection or renderer changes.
"""
from pathlib import Path
import math, json
from schema import normalize, name
from project_bundle import referenced_media
from studio_core import voice_source, duration, voice_required_seconds

ARCHIVE_DIR='.arquivados'

def voice_plan(raw, first, last):
    pr=normalize(raw)
    if type(first)!=int or type(last)!=int or not 0<=first<=last<len(pr['cenas']):
        raise ValueError('Intervalo inválido')
    result=[]
    for i in range(first,last+1):
        scene=pr['cenas'][i];au=scene['audio'];old=scene['duracao']
        row={'index':i,'id':scene['id'],'before':old,'title':scene['titulo'],'status':'sem voz habilitada'}
        if au['voice_enabled'] and not au['muted'] and (au['voice_file'] or au['voice_text'].strip()):
            path=voice_source(scene,pr,required=False)
            seconds=duration(path) if path else 0
            if not math.isfinite(seconds) or seconds<=0:
                row['status']='voz ausente ou ilegível; gere/grave primeiro'
            else:
                after=max(.5,math.ceil(voice_required_seconds(scene,seconds)*1000)/1000)
                if after>600:row['status']='duração excede 600 s'
                else:row.update(status='ok',after=after,voice_seconds=seconds,delay=au['voice_delay'],other_audio=bool(au['tracks'] or au['music_file'] or pr['trilha']),clip=bool(scene['video_clipe']['arquivo']))
        result.append(row)
    return result

def archive_path(root,identifier):
    root=Path(root);folder=root/ARCHIVE_DIR
    if folder.is_symlink():raise ValueError('Arquivo de projetos inseguro')
    p=folder/(name(identifier)+'.json')
    if p.is_symlink():raise ValueError('Projeto arquivado inseguro')
    return p

def active_path(root,identifier):
    p=Path(root)/(name(identifier)+'.json')
    if p.is_symlink():raise ValueError('Projeto inseguro')
    return p

def change_archive(root,identifier,restore=False):
    active=active_path(root,identifier);archived=archive_path(root,identifier)
    src,dst=(archived,active) if restore else (active,archived)
    if not src.is_file():raise ValueError('Projeto não encontrado')
    if dst.exists():raise ValueError('Nome já existente; nada sobrescrito')
    if not restore and sum(p.is_file() and not p.is_symlink() for p in Path(root).glob('*.json'))<=1:
        raise ValueError('Crie outro projeto antes de arquivar o último ativo')
    dst.parent.mkdir(parents=True,exist_ok=True)
    # Android/Termux can omit os.link. Reserve the destination exclusively,
    # preserve the raw JSON and never remove the source before verification.
    # The HTTP caller holds PROJECT_LOCK; do not edit these files externally
    # during the operation. A crash may leave both copies, never intentionally
    # delete an unverified original to resolve a conflict.
    import os
    raw=src.read_bytes()
    created=False
    try:
        with dst.open('xb') as out:
            created=True
            out.write(raw)
            out.flush()
            os.fsync(out.fileno())
        if dst.read_bytes()!=raw:
            raise OSError('Cópia do projeto não confere')
        if src.read_bytes()!=raw:
            raise OSError('Projeto alterado durante a transferência')
    except BaseException as exc:
        if created:
            dst.unlink()
        elif isinstance(exc,FileExistsError):
            raise ValueError('Nome já existente; nada sobrescrito') from exc
        raise
    # If removing the source fails, keep the verified destination as well.
    try:src.unlink()
    except OSError as exc:
        raise OSError('Transferência incompleta; cópia preservada. Verifique origem e destino antes de repetir.') from exc
    return identifier

def archived_projects(root):
    folder=archive_path(root,'probe').parent
    return sorted(p.stem for p in folder.glob('*.json') if p.is_file() and not p.is_symlink())

def inventory(raw,media):
    pr=normalize(raw);media=Path(media);uses={n:[] for n in referenced_media(pr)}
    def add(fn,label):
        if fn:uses.setdefault(fn,[]).append(label)
    add(pr['trilha'],'Trilha global')
    for definition in (pr.get('instance_library') or {}).get('definitions',[]):
        if definition.get('kind')=='media':
            media_object=definition.get('media') or {}
            add(media_object.get('file',''),'Definição vinculada: '+definition.get('id',''))
    for i,c in enumerate(pr['cenas'],1):
        prefix=f'Cena {i}: '
        add(c['imagem']['arquivo'],prefix+'imagem/prancha');add(c['video_clipe']['arquivo'],prefix+'clipe')
        for obj in c.get('objetos_midia',[]):add(obj.get('file',''),prefix+'objeto '+obj['label'])
        au=c['audio'];add(au['voice_file'],prefix+'voz');add(au['music_file'],prefix+'música')
        for j,a in enumerate(au['tracks'],1):add(a['file'],prefix+f'faixa {j}')
        # SVG asset: references are local raster resources (not arbitrary URLs).
        import re
        for fn in set(re.findall(r'asset:([0-9a-f]{16}\.(?:png|jpg))',c.get('svg',''))):add(fn,prefix+'SVG')
    files=[]
    for fn,labels in sorted(uses.items()):
        p=media/fn;present=p.is_file() and not p.is_symlink()
        files.append({'file':fn,'uses':labels,'present':present,'bytes':p.stat().st_size if present else 0})
    return files
