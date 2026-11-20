"""Provider-neutral, read-only catalog discovered from this Termux installation.

No model downloads, no default voice substitution and no changes to installed tools.
"""
from __future__ import annotations
import json
from pathlib import Path
import re
import importlib.util
import shutil
import subprocess

KOKORO_NAMES = (
 'af_alloy af_aoede af_bella af_heart af_jessica af_kore af_nicole af_nova af_river af_sarah af_sky '
 'am_adam am_echo am_eric am_fenrir am_liam am_michael am_onyx am_puck am_santa '
 'bf_alice bf_emma bf_isabella bf_lily bm_daniel bm_fable bm_george bm_lewis '
 'ef_dora em_alex ff_siwis hf_alpha hf_beta hm_omega hm_psi if_sara im_nicola '
 'jf_alpha jf_gongitsune jf_nezumi jf_tebukuro jm_kumo pf_dora pm_alex pm_santa '
 'zf_xiaobei zf_xiaoni zf_xiaoxiao zf_xiaoyi zm_yunjian zm_yunxi zm_yunxia zm_yunyang em_santa'
).split()
KOKORO_LANG = {'a':'en-US','b':'en-GB','e':'es-ES','f':'fr-FR','h':'hi-IN',
               'i':'it-IT','j':'ja-JP','p':'pt-BR','z':'zh-CN'}
PIPER_ALIAS = {'pt_BR-faber-medium':'faber','pt_BR-edresson-low':'edresson'}
MODEL_RE = re.compile(r'^[a-zA-Z]{2,3}[-_][a-zA-Z0-9_-]+$')

def piper_models(root=None):
    root = Path(root or Path.home()/'piper_tts')
    found = {}
    if not root.is_dir():return found
    for model in sorted(root.glob('*.onnx')):
        if model.is_symlink() or not MODEL_RE.fullmatch(model.stem):continue
        config = Path(str(model)+'.json')
        if config.is_symlink() or not config.is_file():continue
        try:
            spec=json.loads(config.read_text('utf-8'))
            rate=int(spec.get('audio',{}).get('sample_rate',0))
            if not 8000 <= rate <= 48000:continue
        except (ValueError,TypeError,OSError,AttributeError):continue
        ident=PIPER_ALIAS.get(model.stem,re.sub(r'-(medium|low|high|x_low|x-low)$','',model.stem.lower().replace('pt_br-','')))
        locale=model.stem.replace('_','-').split('-',2)
        locale='-'.join(locale[:2]) if len(locale)>1 else 'und'
        found[ident]={'model':model,'rate':rate,'locale':locale,'label':model.stem}
    return found

def kokoro_base(root=None):
    root=Path(root or Path.home()/'kokoro_tts'/'kokoro-multi-lang-v1_0')
    required=('model.onnx','voices.bin','tokens.txt')
    if not root.is_dir() or any(not (root/x).is_file() or (root/x).is_symlink() for x in required):return None
    return root

def kokoro_lexicon(root,locale):
    if locale.startswith('pt'):
        names=('lexicon-pt.txt','lexicon-pt-br.txt','lexicon-pt-BR.txt')
    elif locale.startswith('en-US'):names=('lexicon-us-en.txt','lexicon-en-us.txt')
    elif locale.startswith('en-GB'):names=('lexicon-gb-en.txt','lexicon-en-gb.txt')
    else:
        code=locale[:2]
        names=(f'lexicon-{code}.txt',f'lexicon-{code.lower()}.txt',f'lexicon-{locale}.txt')
    return next((root/n for n in names if (root/n).is_file() and not (root/n).is_symlink()),None)

def installed_catalog(*,piper_root=None,kokoro_root=None,edge_catalog=None,include_espeak=True):
    voices=[];warnings=[]
    models=piper_models(piper_root)
    has_piper=bool(shutil.which('piper'))
    for ident,info in models.items():
        voices.append({'id':'piper:'+ident,'provider':'piper','voice_id':ident,'name':info['label'],
                       'locale':info['locale'],'available':has_piper,'exportable':has_piper,'online':False})
    if not has_piper and models:warnings.append('Modelos Piper presentes, mas wrapper piper indisponível')
    kb=kokoro_base(kokoro_root)
    if kb:
        has_sherpa=importlib.util.find_spec('sherpa_onnx') is not None
        if not has_sherpa:warnings.append('Kokoro encontrado, mas sherpa_onnx não está instalado')
        for sid,name in enumerate(KOKORO_NAMES):
            loc=KOKORO_LANG[name[0]]
            lex=kokoro_lexicon(kb,loc)
            ready=bool(lex and has_sherpa and (kb/'espeak-ng-data').is_dir())
            voices.append({'id':'kokoro:'+name,'provider':'kokoro','voice_id':name,'sid':sid,
                           'name':name,'locale':loc,'available':ready,'exportable':ready,'online':False,
                           'status':'' if ready else 'Léxico ou fonemizador do idioma indisponível'})
    try:
        from .core import Catalog
        edge=edge_catalog if edge_catalog is not None else Catalog.load().normalized()
        edge_ready=importlib.util.find_spec('edge_tts') is not None
        if not edge_ready:warnings.append('edge-tts não está instalado no Python do servidor')
        for e in edge.get('voices',[]):
            item={'id':e['id'],'provider':'edge','voice_id':e['voice_id'],
                  'name':e.get('name',e['voice_id']),'locale':e.get('locale',''),
                  'available':edge_ready,'exportable':edge_ready,'online':True}
            voices.append(item)
    except (ValueError,FileNotFoundError,OSError,KeyError) as exc:
        warnings.append('Catálogo Edge indisponível: '+str(exc)[:160])
    if include_espeak and shutil.which('espeak-ng'):
        try:
            proc=subprocess.run(['espeak-ng','--voices'],capture_output=True,text=True,timeout=5,check=False)
            for line in proc.stdout.splitlines()[1:]:
                cols=line.split()
                if len(cols)>3 and re.fullmatch('[A-Za-z0-9_-]{2,30}',cols[1]):
                    voice=cols[1]
                    voices.append({'id':'espeak:'+voice,'provider':'espeak','voice_id':voice,
                        'name':'eSpeak '+voice,'locale':voice.replace('_','-'),
                        'available':True,'exportable':True,'online':False,'legacy':True})
        except (OSError,subprocess.TimeoutExpired):warnings.append('Não foi possível listar vozes eSpeak')
    # No duplicate IDs if catalog includes alternate entries
    ids=set();distinct=[]
    for v in voices:
        if v['id'] not in ids:distinct.append(v);ids.add(v['id'])
    return {'version':1,'voices':distinct,'count':len(distinct),'warnings':warnings}

def require_voice(voice, *,catalog=None):
    listing=catalog if catalog is not None else installed_catalog()
    match=next((v for v in listing['voices'] if v['id']==voice or
                (v['provider']=='piper' and v['voice_id']==voice)),None)
    if not match:raise ValueError('Voz não encontrada no catálogo instalado: '+str(voice))
    if not match['available']:raise ValueError('Voz indisponível nesta instalação: '+match['id'])
    return match
