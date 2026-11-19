"""Renomeação de projetos sem perda de JSON ou mídias compartilhadas."""
from pathlib import Path
import hashlib, os, re

ID = re.compile(r'^[A-Za-z0-9_-]{1,64}$')

def rename_project(root, old, new):
    if not isinstance(old,str) or not ID.fullmatch(old) or not isinstance(new,str) or not ID.fullmatch(new):
        raise ValueError('Identificador inválido')
    if old==new:raise ValueError('Informe outro nome')
    root=Path(root)
    if root.is_symlink() or not root.is_dir():raise ValueError('Pasta de projetos insegura')
    src=root/(old+'.json');dst=root/(new+'.json')
    archived=root/'.arquivados'/(new+'.json')
    if src.is_symlink() or dst.is_symlink() or archived.is_symlink():raise ValueError('Caminho inseguro')
    if not src.is_file():raise ValueError('Projeto não encontrado')
    if dst.exists() or archived.exists():raise ValueError('Nome já utilizado')
    raw=src.read_bytes()
    if len(raw)>12_000_000:raise ValueError('Projeto grande demais para renomeação automática')
    # Reservation with exclusive create; independent of os.link (often unavailable on Android).
    created=False
    try:
        with dst.open('xb') as out:
            created=True
            out.write(raw);out.flush();os.fsync(out.fileno())
        if dst.read_bytes()!=raw or src.read_bytes()!=raw:raise OSError('Cópia diferente da origem')
    except BaseException:
        if created:dst.unlink(missing_ok=True)
        raise
    try:src.unlink()
    except OSError as exc:
        raise OSError('Origem não removida; cópia íntegra preservada. Verifique ambos os projetos.') from exc
    return new
