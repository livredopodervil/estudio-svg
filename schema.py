"""Projeto JSON V2.2 e compatibilidade V1/V2.1. Sem dependências externas."""
from __future__ import annotations
import json, re, copy, math

VERSION='2.6.0'
MODES={'globo','linha','barras','numero','cartoes','arvore','svg','foto'}
PRESETS={'16:9':(1280,720),'9:16':(720,1280),'1:1':(800,800),'4:5':(800,1000),'21:9':(1260,540)}
COLORS={'fundo':'#241b1a','destaque':'#d99a62','texto':'#fff1da'}
NAME=re.compile(r'^[A-Za-z0-9_-]{1,64}$')
ASSET=re.compile(r'^[A-Za-z0-9_.-]{1,160}$')
HEX=re.compile(r'^#[0-9a-fA-F]{6}$')

def n(v,default,lo,hi):
    try: v=float(v)
    except (ValueError,TypeError):return default
    return max(lo,min(hi,v)) if math.isfinite(v) else default

def name(v):
    if not isinstance(v,str) or not NAME.fullmatch(v):raise ValueError('Identificador inválido: letras, números, _ e -')
    return v

def asset(v):
    if not v:return ''
    if not isinstance(v,str) or not ASSET.fullmatch(v) or v.startswith('.') or '..' in v:raise ValueError('Arquivo de mídia inválido; importe pelo editor')
    return v

def color(v,default):return v if isinstance(v,str) and HEX.fullmatch(v) else default

def scene_id(x,i):
    s=str(x or '').strip()
    return s if NAME.fullmatch(s) else f'cena_{i+1:03d}'

def audio_dict(v,legacy_fala=''):
    v=v if isinstance(v,dict) else {}
    voice_text=str(v.get('voice_text',legacy_fala))[:4000]
    tracks=[]
    for x in v.get('tracks',[])[:20] if isinstance(v.get('tracks',[]),list) else []:
        if not isinstance(x,dict):continue
        file=asset(x.get('file',''))
        if not file:continue
        tracks.append({'file':file,'start':n(x.get('start',0),0,0,3600),'volume':n(x.get('volume',.5),.5,0,3),
            'fade_in':n(x.get('fade_in',0),0,0,60),'fade_out':n(x.get('fade_out',0),0,0,60),'loop':bool(x.get('loop',False))})
    return {'voice_text':voice_text,'voice_enabled':bool(v.get('voice_enabled',bool(voice_text))),
            'voice_file':asset(v.get('voice_file','')),'voice_volume':n(v.get('voice_volume',1),1,0,3),
            'voice_delay':n(v.get('voice_delay',.12),.12,0,30),
            'music_file':asset(v.get('music_file','')),'music_volume':n(v.get('music_volume',.16),.16,0,2),
            'duck_music':bool(v.get('duck_music',False)),'tracks':tracks}

def image_dict(v):
    if isinstance(v,str):v={'arquivo':v}
    v=v if isinstance(v,dict) else {}
    return {'arquivo':asset(v.get('arquivo','')),
       'fit':v.get('fit','cover') if v.get('fit') in ('contain','cover','stretch','pad','crop') else 'cover',
       'align_x':n(v.get('align_x',.5),.5,0,1),'align_y':n(v.get('align_y',.5),.5,0,1),
       'bg':color(v.get('bg','#241b1a'),'#241b1a'),
       'crop': [n(z,0,0,1) for z in v.get('crop',[])][:4] if isinstance(v.get('crop',[]),list) else []}

def normalize(data):
    if not isinstance(data,dict):raise ValueError('O projeto deve ser objeto JSON')
    raw=data.get('cenas')
    if not isinstance(raw,list) or not 1<=len(raw)<=150:raise ValueError('São necessárias entre 1 e 150 cenas')
    video=data.get('video',{}) if isinstance(data.get('video'),dict) else {}
    w=int(video.get('width',data.get('largura',1280)));h=int(video.get('height',data.get('altura',720)))
    if w<320 or h<320 or w>1920 or h>1920 or w%2 or h%2:raise ValueError('Resolução: dimensões pares entre 320 e 1920')
    fps=int(video.get('fps',data.get('fps_saida',24)));draw=int(video.get('draw_fps',data.get('fps_desenho',6)))
    if fps not in (24,25,30):raise ValueError('FPS saída: 24, 25 ou 30')
    if draw not in (1,2,3,4,6,8,10,12,15,24):raise ValueError('FPS desenho inválido')
    out={'versao':VERSION,'titulo':str(data.get('titulo','Novo filme'))[:180],
         'video':{'width':w,'height':h,'fps':fps,'draw_fps':draw,'background':color(video.get('background','#241b1a'),'#241b1a')},
         'voz':str(data.get('voz','pt-BR-AntonioNeural'))[:80], 'velocidade_voz':str(data.get('velocidade_voz','+0%'))[:15],
         'motor_voz':data.get('motor_voz','edge-tts') if data.get('motor_voz','edge-tts') in ('edge-tts','espeak-ng','piper') else 'edge-tts',
         'modelo_piper':asset(data.get('modelo_piper','')),'voz_espeak':str(data.get('voz_espeak','pt-br'))[:50],
         'velocidade_espeak':int(n(data.get('velocidade_espeak',165),165,80,260)),
         'encaixe_voz':data.get('encaixe_voz','estender') if data.get('encaixe_voz') in ('estender','avisar') else 'estender',
         'trilha':asset(data.get('trilha','')),'volume_musica':n(data.get('volume_musica',.16),.16,0,2),
         'volume_voz':n(data.get('volume_voz',1.35),1.35,0,3),'cenas':[]}
    ids=set()
    for i,r in enumerate(raw):
        if not isinstance(r,dict):raise ValueError(f'Cena {i+1} não é um objeto')
        typ={'intro':'globo','indicador':'numero','bibliografia':'cartoes'}.get(r.get('tipo','globo'),r.get('tipo','globo'))
        if typ not in MODES:raise ValueError(f'Cena {i+1}: tipo desconhecido: {typ}')
        sid=scene_id(r.get('id'),i)
        if sid in ids:sid=f'{sid}_{i+1}'
        ids.add(sid)
        cs=r.get('cores',{}) if isinstance(r.get('cores'),dict) else {}
        image=r.get('imagem',{})
        c={'id':sid,'tipo':typ,'duracao':n(r.get('duracao',8),8,.5,600),
            'titulo':str(r.get('titulo',''))[:250],'subtitulo':str(r.get('subtitulo',''))[:400],
            'fala':str(r.get('fala',''))[:4000], 'fonte':str(r.get('fonte',''))[:450],
            'categoria':str(r.get('categoria','ESTÚDIO SVG'))[:120],
            'movimento':r.get('movimento','suave') if r.get('movimento') in ('linear','suave','entrada','saida') else 'suave',
            'dados':r.get('dados',[])[:100] if isinstance(r.get('dados',[]),list) else [],
            'itens':[str(x)[:240] for x in r.get('itens',[])[:20]] if isinstance(r.get('itens',[]),list) else [],
            'valor':str(r.get('valor',''))[:60], 'unidade':str(r.get('unidade',''))[:70],
            'sufixo':str(r.get('sufixo',''))[:400], 'destaque':str(r.get('destaque',''))[:200],
            'svg':str(r.get('svg',''))[:2000000],
            'imagem':image_dict(image),
            'cores':{k:color(cs.get(k),COLORS[k]) for k in COLORS},
            'audio':audio_dict(r.get('audio'),r.get('fala',''))}
        # Explicit scene audio supersedes legacy fala; keep both synchronized for old exports.
        c['fala']=c['audio']['voice_text']
        out['cenas'].append(c)
    return out

def default_project():
    return normalize({'titulo':'Estúdio SVG V2.2 — demonstração','video':{'width':640,'height':360,'fps':24,'draw_fps':4},
      'cenas':[
        {'tipo':'globo','duracao':5,'titulo':'UMA NOVA HISTÓRIA','subtitulo':'Cenas independentes · SVG · voz neural',
          'itens':['ROTEIRO','IMAGEM','SOM'], 'fala':'Um editor audiovisual completo, renderizado localmente no seu celular.'},
        {'tipo':'linha','duracao':6,'titulo':'DADOS EM MOVIMENTO','subtitulo':'Uma visualização programada por cena',
          'dados':[[1,2],[2,3],[3,5],[4,8],[5,13]],'fala':'O sistema produz gráficos animados sem depender de assinaturas.'},
        {'tipo':'foto','duracao':4,'titulo':'IMAGENS FLEXÍVEIS','subtitulo':'Importe uma foto e escolha o enquadramento',
          'imagem':{'fit':'contain'},'fala':'Imagens podem ser ajustadas à proporção do vídeo.'},
        {'tipo':'numero','duracao':5,'titulo':'CACHE POR CENA','valor':'1','unidade':'CENA ALTERADA',
          'fala':'Apenas os segmentos modificados precisam ser renderizados.'}]})
