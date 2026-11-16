#!/usr/bin/env python3
"""Reviewable fast-forward update of the already published integration branch.
Does not edit the audiovisual checkout or the site. No forced push.
"""
from pathlib import Path
import argparse,json,subprocess,tempfile,sys
from prepare_publication import ROOT,SOURCE_ORIGIN,SOURCE_BRANCH,SOURCE_PREFIX,origin,remote,run,sha,stop
BASE='fde919dc49cbee0385b5990d7546ed89378f1fd5'
OLD_MANIFEST='7dd3b417f3277179559726abeebe0e8e4d7038210ea8229e4b37462f98e03cc2'
MANIFEST=SOURCE_PREFIX+'PACKAGE.json'
def gitbytes(repo,ref,path):
    p=subprocess.run(['git','-C',str(repo),'show',ref+':'+path],capture_output=True)
    if p.returncode:stop('Arquivo esperado ausente na revisão: '+path)
    return p.stdout
def data():
    m=json.loads((ROOT/'PACKAGE.json').read_text());out={}
    if m['version']!='0.2.0':stop('Versão inesperada')
    for name,h in m['files'].items():
        p=ROOT/name
        if p.is_symlink() or not p.is_file() or not p.resolve().is_relative_to(ROOT) or sha(p.read_bytes())!=h:stop('Arquivo alterado: '+name)
        out[SOURCE_PREFIX+name]=p.read_bytes()
    out[MANIFEST]=(ROOT/'PACKAGE.json').read_bytes();return out
def delta(repo,base):
    previous=gitbytes(repo,base,MANIFEST)
    if sha(previous)!=OLD_MANIFEST:stop('Manifesto remoto difere da base auditada; não sobrescrever.')
    old=json.loads(previous);new=data();expected={SOURCE_PREFIX+k:v for k,v in old['files'].items()};expected[MANIFEST]=sha(previous)
    if set(expected)-set(new):stop('Atualização contém exclusões não autorizadas')
    for path,h in expected.items():
        if sha(gitbytes(repo,base,path))!=h:stop('Arquivo remoto divergiu: '+path)
    additions=set(new)-set(expected)
    tracked=set(run(repo,'ls-tree','-r','--name-only',base).splitlines())
    if additions&tracked:stop('Colisão em arquivos novos')
    return {n:b for n,b in new.items() if expected.get(n)!=sha(b)}
def prepare(repo):
    origin(repo,SOURCE_ORIGIN);run(repo,'fetch','--no-tags','origin','refs/heads/'+SOURCE_BRANCH);base=run(repo,'rev-parse','FETCH_HEAD')
    if base!=BASE or remote(repo,SOURCE_BRANCH)!=base:stop('Branch mudou desde fde919dc. Audite a nova base.')
    files=delta(repo,base);parent=Path(tempfile.mkdtemp(prefix='rd-gil-020-',dir=Path.home()));wt=parent/'worktree';run(repo,'worktree','add','--detach',str(wt),base)
    for name,b in files.items():
        p=wt/name
        if not p.resolve().is_relative_to(wt) or any(q.is_symlink() for q in [p,*p.parents] if q.is_relative_to(wt)):stop('Caminho não autorizado')
        p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b)
    run(wt,'add','-f','--',*files);run(wt,'diff','--cached','--check')
    (parent/'publication-v020.json').write_text(json.dumps({'base':base,'files':{n:sha(b) for n,b in files.items()}},indent=2))
    print('WORKTREE:',wt);print(run(wt,'diff','--cached','--stat'));print('Revisar conteúdo e testes. Nada publicado.');print('python',ROOT/'tools/publish_update.py','--publish',wt,'--confirm-rights')
def publish(wt):
    origin(wt,SOURCE_ORIGIN);m=json.loads((wt.parent/'publication-v020.json').read_text())
    if m['base']!=BASE or run(wt,'rev-parse','HEAD')!=BASE or run(wt,'branch','--show-current') or remote(wt,SOURCE_BRANCH)!=BASE:stop('Base ou destino mudou: não publicar.')
    files=delta(wt,BASE)
    if m['files']!={n:sha(b) for n,b in files.items()}:stop('Manifesto de revisão divergiu.')
    if set(run(wt,'diff','--cached','--name-only').splitlines())!=set(files) or run(wt,'diff','--name-only') or run(wt,'ls-files','--others','--exclude-standard'):stop('Worktree contém outras alterações.')
    for n,b in files.items():
        if (wt/n).is_symlink() or (wt/n).read_bytes()!=b:stop('Arquivo alterado: '+n)
        p=subprocess.run(['git','-C',str(wt),'show',':'+n],capture_output=True)
        if p.returncode or p.stdout!=b:stop('Índice divergente: '+n)
    run(wt,'diff','--cached','--check');run(wt,'commit','-m','feat(integration): GIL 0.2 autoria hierarquica e render MP4');head=run(wt,'rev-parse','HEAD');print('COMMIT LOCAL:',head,flush=True);run(wt,'push','origin','HEAD:refs/heads/'+SOURCE_BRANCH)
    if remote(wt,SOURCE_BRANCH)!=head:stop('Remoto não coincide; confira manualmente.')
    print('PUBLICADO:',head)
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);g=p.add_mutually_exclusive_group(required=True);g.add_argument('--prepare',type=Path);g.add_argument('--publish',type=Path);p.add_argument('--confirm-rights',action='store_true');a=p.parse_args()
    if a.prepare:prepare(a.prepare.expanduser().resolve())
    elif a.confirm_rights:publish(a.publish.expanduser().resolve())
    else:stop('Confirme os direitos de publicação somente após revisão.')
