#!/usr/bin/env python3
"""Prepare source or demo in a separate Git worktree, then explicitly publish its verified files.
No forced push, no checkout of the user's existing branch, no reading of Git credentials.
"""
from pathlib import Path
import argparse,subprocess,tempfile,json,hashlib,sys,shutil,zipfile,os
ROOT=Path(__file__).resolve().parents[1]
SOURCE_BASE='release/v3-alpha4-rc1';SOURCE_BRANCH='feature/rd-studio-gil-v01';SITE_BRANCH='main'
SOURCE_ORIGIN='livredopodervil/estudio-svg';SITE_ORIGIN='livredopodervil/rogerioduarte.org'
SOURCE_PREFIX='integrations/rd-studio-gil-v01/'
def stop(msg):raise SystemExit(msg)
def run(repo,*args):
    p=subprocess.run(['git','-C',str(repo),*args],capture_output=True,text=True)
    if p.returncode:stop(f'Git {args[0]} falhou (status {p.returncode}); verifique o Git local. Nenhum push forçado.')
    return p.stdout.strip()
def sha(data):return hashlib.sha256(data).hexdigest()
def origin(repo,expected):
    valid={f'git@github.com:{expected}.git',f'git@github.com:{expected}',f'https://github.com/{expected}.git',f'https://github.com/{expected}',f'ssh://git@github.com/{expected}.git'}
    for args in [('remote','get-url','origin'),('remote','get-url','--push','origin')]:
        if run(repo,*args) not in valid:stop('Origin ou URL de push inesperada; revise localmente.')
def remote(repo,branch):
    s=run(repo,'ls-remote','--heads','origin','refs/heads/'+branch)
    return s.split()[0] if s else None
def payload(mode):
    if mode=='source':
        # exact allowlisted package manifest; no working data or private Git config
        manifest=json.loads((ROOT/'PACKAGE.json').read_text())
        result={}
        for name,h in manifest['files'].items():
            if name.startswith('demo/'):continue
            p=ROOT/name
            if p.is_symlink() or not p.is_file() or not p.resolve().is_relative_to(ROOT):stop('Arquivo de pacote inválido: '+name)
            b=p.read_bytes()
            if sha(b)!=h:stop('Pacote alterado: '+name)
            result[SOURCE_PREFIX+name]=b
        # Generate a matching manifest for the source-only payload? include demo for reproducibility.
        for name,h in manifest['files'].items():
            if not name.startswith('demo/'):continue
            b=(ROOT/name).read_bytes()
            if sha(b)!=h:stop('Demo alterada')
            result[SOURCE_PREFIX+name]=b
        result[SOURCE_PREFIX+'PACKAGE.json']=(ROOT/'PACKAGE.json').read_bytes()
        return result
    archives=list((ROOT/'demo').glob('gil-gil-maquina-cinetica-*.rdpatch.zip'))
    if len(archives)!=1:stop('Pacote da demonstração cinética ausente ou ambíguo.')
    archive=archives[0]
    # Use original patch-manager validation, including ftyp/signatures and SHA256.
    sys.path.insert(0,str(ROOT/'rdstudio'));from patches import PatchManager
    with tempfile.TemporaryDirectory() as d,zipfile.ZipFile(archive) as z:
        m=PatchManager(Path(d))._manifest(z)
        if not all(i['operation']=='add' and i['path'].startswith('projetos/gil-maquina-cinetica/') for i in m['files']):stop('Demo fora do escopo')
        return {i['path']:z.read('files/'+i['path']) for i in m['files']}
def prepare(mode,repo):
    expected=SOURCE_ORIGIN if mode=='source' else SITE_ORIGIN; origin(repo,expected)
    base_branch=SOURCE_BASE if mode=='source' else SITE_BRANCH; dest_branch=SOURCE_BRANCH if mode=='source' else SITE_BRANCH
    if mode=='source' and remote(repo,dest_branch):stop('Branch de integração já existe. Não sobrescreva; próxima atualização deve partir dela.')
    run(repo,'fetch','--no-tags','origin','refs/heads/'+base_branch);base=run(repo,'rev-parse','FETCH_HEAD')
    if remote(repo,base_branch)!=base:stop('Remoto avançou; execute novamente.')
    if mode=='source':
        if run(repo,'branch','--show-current')!=SOURCE_BASE or run(repo,'rev-parse','HEAD')!=base or run(repo,'status','--porcelain','--untracked-files=no'):
            stop('Base audiovisual local não coincide com a branch remota limpa. Consolide V3.6 antes de criar a integração.')
        tracked=set(run(repo,'ls-tree','-r','--name-only',base).splitlines())
        if not {'web/layers-v36.js','web/media-recorder-v35.js','tests/test_v36_integration.py'}<=tracked:stop('A base remota não contém V3.6; não preparar uma integração sobre a V3.1.')
    parent=Path(tempfile.mkdtemp(prefix='rd-gil-'+mode+'-',dir=Path.home()));wt=parent/'worktree'
    files=payload(mode)
    run(repo,'worktree','add','--detach',str(wt),base)
    if mode=='demo' and ((wt/'CNAME').read_text().strip()!='rogerioduarte.org' or not (wt/'.nojekyll').is_file()):stop('Configuração de site inesperada.')
    # Verify every destination before writing any.
    for name in files:
        target=wt/name
        if target.exists() or target.is_symlink() or any(q.is_symlink() for q in target.parents if q!=wt and q.is_relative_to(wt)):stop('Conflito de arquivo: '+name)
    for name,b in files.items():
        target=wt/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(b)
    (parent/'publication.json').write_text(json.dumps({'mode':mode,'base':base,'base_branch':base_branch,'branch':dest_branch,'origin':expected,'files':{n:sha(b) for n,b in files.items()}},indent=2))
    print('WORKTREE:',wt);print('BASE:',base);print('DESTINO:',dest_branch);print('ARQUIVOS:',len(files));print('Nada publicado. Revise e teste o worktree antes de --publish.')
    print('python',ROOT/'tools/prepare_publication.py','--publish',wt,'--confirm-rights')
def publish(wt):
    wt=wt.resolve();meta=json.loads((wt.parent/'publication.json').read_text());mode=meta['mode']
    expected=SOURCE_ORIGIN if mode=='source' else SITE_ORIGIN;origin(wt,expected)
    if meta['origin']!=expected or meta['branch']!=(SOURCE_BRANCH if mode=='source' else SITE_BRANCH):stop('Metadados inválidos.')
    if run(wt,'rev-parse','HEAD')!=meta['base'] or run(wt,'branch','--show-current'):stop('Worktree mudou; publicação interrompida.')
    if run(wt,'diff','--name-only') or run(wt,'diff','--cached','--name-only'):stop('Alterações rastreadas inesperadas.')
    if meta['files']!={n:sha(b) for n,b in payload(mode).items()}:stop('Manifesto de publicação divergiu do pacote original.')
    if set(run(wt,'ls-files','--others','--exclude-standard').splitlines())-set(meta['files']):stop('Arquivos novos inesperados. Revise o worktree.')
    for n,h in meta['files'].items():
        p=wt/n
        if p.is_symlink() or not p.is_file() or not p.resolve().is_relative_to(wt) or sha(p.read_bytes())!=h:stop('Arquivo modificado: '+n)
    if mode=='demo' and remote(wt,'main')!=meta['base']:stop('Main avançou (inclusive atualizações automáticas). Prepare outro worktree; não force.')
    if mode=='source' and (remote(wt,SOURCE_BRANCH) or remote(wt,SOURCE_BASE)!=meta['base']):stop('Branch de destino existe ou a base audiovisual avançou. Prepare novamente.')
    # Explicitly include only manifest-reviewed new files even if the base ignores ZIPs.
    run(wt,'add','-f','--',*meta['files']);run(wt,'diff','--cached','--check')
    if set(run(wt,'diff','--cached','--name-only').splitlines())!=set(meta['files']):stop('Stage divergente.')
    msg='feat(integration): RD Studio e GIL Timeline v0.1.2' if mode=='source' else 'feat(site): máquina cinética GIL com vídeo e manifesto'
    run(wt,'commit','-m',msg);head=run(wt,'rev-parse','HEAD');print('COMMIT LOCAL:',head,flush=True)
    run(wt,'push','origin','HEAD:refs/heads/'+meta['branch'])
    if remote(wt,meta['branch'])!=head:stop('Remoto não coincide com commit: confira antes de repetir.')
    print('PUBLICADO:',head)
    if mode=='demo':print('URL esperada após deploy: https://rogerioduarte.org/projetos/gil-maquina-cinetica/')
if __name__=='__main__':
    ap=argparse.ArgumentParser();g=ap.add_mutually_exclusive_group(required=True);g.add_argument('--prepare-source',type=Path);g.add_argument('--prepare-demo',type=Path);g.add_argument('--publish',type=Path);ap.add_argument('--confirm-rights',action='store_true');a=ap.parse_args()
    if a.publish:
        if not a.confirm_rights:stop('Revise autoria, licenças e arquivos públicos e informe --confirm-rights somente após aprovação.')
        publish(a.publish)
    else:prepare('source' if a.prepare_source else 'demo',(a.prepare_source or a.prepare_demo).expanduser().resolve())
