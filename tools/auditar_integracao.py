#!/usr/bin/env python3
"""Read-only audit of the three local checkouts and published web manifest."""
from __future__ import annotations
import argparse
import json
import subprocess
from pathlib import Path


def git(root):
    p=Path(root)
    if not p.exists():
        return {'path':str(p),'ok':False,'error':'diretório não encontrado'}
    def run(*args):
        x=subprocess.run(['git','-C',str(p),*args],capture_output=True,text=True,timeout=10)
        return x.stdout.strip() if not x.returncode else None
    branch=run('branch','--show-current')
    remote=run('remote','get-url','origin')
    head=run('rev-parse','HEAD')
    status=run('status','--porcelain')
    return {'path':str(p.resolve()),'ok':bool(head),'branch':branch,'head':head,
            'remote':remote,'dirty':bool(status) if status is not None else None}


def main():
    pa=argparse.ArgumentParser()
    for name in ['site','studio','spatial']:
        pa.add_argument('--'+name,required=True,type=Path,help='Checkout local existente, sem suposição de caminho')
    pa.add_argument('--published',type=Path,help='Pasta da publicação web, opcional')
    args=pa.parse_args()
    report={name:git(getattr(args,name)) for name in ('site','studio','spatial')}
    expected={"site":"livredopodervil/rogerioduarte.org", "studio":"livredopodervil/estudio-svg", "spatial":"livredopodervil/SpatialSeed"}
    for name, expected_repo in expected.items():
        remote=(report[name].get("remote") or "").rstrip("/")
        # GitHub SSH and HTTPS remotes are both accepted; never infer owner from folder name.
        accepted={f"git@github.com:{expected_repo}.git",f"https://github.com/{expected_repo}.git",f"https://github.com/{expected_repo}"}
        if remote not in accepted:
            report[name]["ok"]=False
            report[name]["error"]="remote GitHub incompatível com " + expected_repo
    site_file=args.site/'modules/manifest.json'
    if site_file.is_file():report['site']['modules_manifest']=str(site_file.relative_to(args.site))
    spatial_build=args.spatial/'apps/web/build-info.json'
    if spatial_build.is_file():
        try:report['spatial']['build_info']=json.loads(spatial_build.read_text())
        except (ValueError,UnicodeDecodeError):report['spatial']['build_info']='inválido'
    if args.published:
        from estudio_web_publish import verify_root
        try:
            names=verify_root(args.published)
            mismatches=[]
            for slug in names:
                manifest=json.loads((args.published/'apresentacoes'/slug/'manifest.json').read_text(encoding='utf-8'))
                source=manifest.get('source',{})
                studio_revision=(source.get('estudio') or {}).get('commit')
                spatial_revision=(source.get('spatialseed') or {}).get('revision')
                if studio_revision and report['studio'].get('head')!=studio_revision:
                    mismatches.append(slug+': revisão de Estúdio diferente da publicação')
                if spatial_revision and report['spatial'].get('head')!=spatial_revision:
                    mismatches.append(slug+': revisão de SpatialSeed diferente da publicação')
            report['publication']={'ok':True,'slugs':names,'revision_warnings':mismatches}
        except Exception as exc:report['publication']={'ok':False,'error':str(exc)}
    print(json.dumps(report,indent=2,ensure_ascii=False))
    return 0 if all(report[k]['ok'] for k in ('site','studio','spatial')) and report.get('publication',{'ok':True})['ok'] else 1

if __name__=='__main__':raise SystemExit(main())
