"""Projeto JSON V2.2 e compatibilidade V1/V2.1. Sem dependências externas."""
from __future__ import annotations
from studio_instances import normalize_library, normalize_roots
import json, re, copy, math, hashlib
from spatial_scene import normalize_spatial, default_spatial
from timeline_easing import EASINGS

VERSION='3.0.0-alpha.4'
MODES={'globo','linha','barras','numero','cartoes','arvore','svg','foto','espacial'}
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

def studio_voice_config(value):
    """Preserva seleção por provedor com limites e identidade explícitos.

    Nunca converte voz browser/Piper em Edge de forma silenciosa.
    """
    if value is None or value == '':return None
    from rd_voices.core import normalize_voice, Catalog, edge_parameters, EXPRESSIVE_PRESETS
    raw=normalize_voice(value)
    provider=raw['provider'];vid=raw['voice_id']
    if provider not in ('edge','browser','piper','kokoro'):
        raise ValueError('Provedor de voz desconhecido; use edge:, browser:, piper: ou kokoro:')
    if not 1<=len(vid)<=240 or '\x00' in vid:
        raise ValueError('Identificador de voz inválido')
    if provider=='edge':Catalog.load().require(vid)
    if provider=='piper' and vid not in ('faber','edresson'):
        raise ValueError('Modelo Piper não cadastrado no Estúdio')
    obj={'provider':provider,'voice_id':vid}
    if not isinstance(value,dict):return obj
    prosody=value.get('prosody') or {}
    if not isinstance(prosody,dict):raise ValueError('Prosódia inválida')
    if provider=='edge':
        params=edge_parameters({'prosody':prosody})
        obj['prosody']={'rate_pct':int(params['rate'][:-1]),
                        'pitch_hz':int(params['pitch'][:-2]),
                        'volume_pct':int(params['volume'][:-1])}
    else:
        # O componente comum pode preservar os campos Edge ao alternar provedor.
        # Eles ficam armazenados, mas nunca são enviados ao motor browser/Piper.
        if prosody:
            params=edge_parameters({'prosody':prosody})
            obj['prosody']={'rate_pct':int(params['rate'][:-1]),
                            'pitch_hz':int(params['pitch'][:-2]),
                            'volume_pct':int(params['volume'][:-1])}
    intention=str(value.get('intention') or 'neutro')
    if intention not in EXPRESSIVE_PRESETS:raise ValueError('Intenção expressiva desconhecida')
    obj['intention']=intention
    obj['apply_intention_preset']=value.get('apply_intention_preset') is True
    if provider=='browser':
        raw_browser=value.get('browser') or {}
        if not isinstance(raw_browser,dict):raise ValueError('Parâmetros browser inválidos')
        obj['browser']={k:n(raw_browser.get(k,d),d,lo,hi) for k,d,lo,hi in
          [('rate',1,.1,3),('pitch',1,0,2),('volume',1,0,1)]}
    return obj

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
    result={'voice_text':voice_text,'voice_enabled':bool(v.get('voice_enabled',bool(voice_text))),
            'voice_file':asset(v.get('voice_file','')),'voice_volume':n(v.get('voice_volume',1),1,0,3),
            'voice_delay':n(v.get('voice_delay',.12),.12,0,30),
            'music_file':asset(v.get('music_file','')),'music_volume':n(v.get('music_volume',.16),.16,0,2),
            'duck_music':bool(v.get('duck_music',False)),'muted':bool(v.get('muted',False)),
            'scene_fade_in':n(v.get('scene_fade_in',0),0,0,5),'scene_fade_out':n(v.get('scene_fade_out',0),0,0,5),'tracks':tracks}
    if v.get('voice') is not None:result['voice']=studio_voice_config(v.get('voice'))
    return result

def subtitle_dict(value):
    """Configuração declarativa de legendas, sem scripts ou HTML do usuário."""
    v = value if isinstance(value, dict) else {}
    modes = {'phrase', 'karaoke', 'word'}
    effects = {'none', 'fade', 'rise', 'pop', 'slide', 'typewriter'}
    positions = {'bottom', 'center', 'top'}
    raw_cues = v.get('cues', [])
    cues = []
    if isinstance(raw_cues, list):
        for item in raw_cues[:800]:
            if not isinstance(item, dict):
                continue
            try:
                start = float(item['start'])
                end = float(item['end'])
            except (KeyError, ValueError, TypeError):
                continue
            text = str(item.get('text', '')).strip()[:180]
            if not all(map(math.isfinite, (start, end))) or not (0 <= start < end <= 3600) or not text:
                continue
            cues.append({'start': start, 'end': end, 'text': text})
    cues.sort(key=lambda cue: (cue['start'], cue['end']))
    return {
        'enabled': v.get('enabled') is True,
        'mode': v.get('mode') if v.get('mode') in modes else 'karaoke',
        'effect': v.get('effect') if v.get('effect') in effects else 'rise',
        'position': v.get('position') if v.get('position') in positions else 'bottom',
        'font_scale': n(v.get('font_scale', 1), 1, .55, 1.6),
        'max_words': int(n(v.get('max_words', 6), 6, 1, 10)),
        'text_color': color(v.get('text_color'), '#ffffff'),
        'highlight_color': color(v.get('highlight_color'), '#ffe49a'),
        'background_color': color(v.get('background_color'), '#091627'),
        'background_opacity': n(v.get('background_opacity', .80), .80, 0, 1),
        'cues': cues,
    }


def image_dict(v, portrait=False, photo=False):
    if isinstance(v,str):v={'arquivo':v}
    v=v if isinstance(v,dict) else {}
    return {'arquivo':asset(v.get('arquivo','')),
       'fit':v.get('fit','cover') if v.get('fit') in ('contain','cover','stretch','pad','crop') else 'cover',
       'align_x':n(v.get('align_x',.5),.5,0,1),'align_y':n(v.get('align_y',.5),.5,0,1),
       'bg':color(v.get('bg','#241b1a'),'#241b1a'),
       'crop': image_crop(v.get('crop',[])),
       'modo': v.get('modo','fundo' if photo else 'quadro') if v.get('modo') in ('fundo','quadro') else ('fundo' if photo else 'quadro'),
       'x':n(v.get('x',.5 if portrait else .73),.5 if portrait else .73,0,1),
       'y':n(v.get('y',.52 if portrait else .58),.52 if portrait else .58,0,1),
       'w':n(v.get('w',.82 if portrait else .41),.82 if portrait else .41,.08,1),
       'h':n(v.get('h',.34 if portrait else .65),.34 if portrait else .65,.08,1),
       'frame':bool(v.get('frame',True))}


def gil_component_dict(raw):
    if not isinstance(raw,dict):return None
    source=raw.get('source'); digest=raw.get('source_sha256'); original=raw.get('origin_sha256')
    if raw.get('format')!='gil-timeline-0.1' or raw.get('origin') not in ('gil','spatialseed') or not isinstance(source,str) or not 0<len(source.encode('utf8'))<=250000:return None
    if digest!=hashlib.sha256(source.encode('utf8')).hexdigest() or not isinstance(original,str) or not re.fullmatch('[0-9a-f]{64}',original):return None
    duration=raw.get('duration')
    if type(duration) not in (int,float) or not math.isfinite(duration) or not .5<=duration<=61:return None
    return {'format':'gil-timeline-0.1','origin':raw['origin'],'origin_sha256':original,'source':source,'source_sha256':digest,'duration':duration}


def media_objects_dict(raw):
    """Independent visual overlays, stored without replacing legacy scene media."""
    if not isinstance(raw,list) or len(raw)>16:raise ValueError('Objetos: lista de até 16 camadas')
    out=[]; ids=set()
    for item in raw:
        if not isinstance(item,dict):raise ValueError('Objeto inválido')
        key=name(item.get('id'));kind=item.get('kind')
        if key in ids or kind not in ('image','video','gil'):raise ValueError('ID duplicado ou tipo inválido')
        ids.add(key)
        obj={'id':key,'kind':kind,'label':str(item.get('label',key))[:120]}
        for k,d,lo,hi in [('x',.5,-2,3),('y',.5,-2,3),('w',.7,.02,2),('h',.7,.02,2),('opacity',1,0,1),('start',0,0,600),('end',600,0,600),('offset',0,0,3600)]:
            obj[k]=n(item.get(k,d),d,lo,hi)
        if obj['end']<=obj['start']:raise ValueError('Intervalo do objeto inválido')
        obj['fit']='contain' if item.get('fit')=='contain' else 'cover'
        obj['loop']=item.get('loop',True) is not False;obj['opaque']=item.get('opaque') is True
        motion=item.get('motion','')
        if not isinstance(motion,str) or len(motion.encode('utf8'))>16000:raise ValueError('Fonte de movimento inválida')
        obj['motion']=motion
        obj['rotation']=n(item.get('rotation',0),0,-360,360)
        for k,default,lo,hi in [('corner_radius',0,0,.5),('border_width',0,0,20),('shadow_blur',0,0,60)]:
            obj[k]=n(item.get(k,default),default,lo,hi)
        for k,default in [('border_color','#ffffff'),('shadow_color','#000000')]:
            color=item.get(k,default)
            if not isinstance(color,str) or not re.fullmatch(r'#[0-9a-fA-F]{6}',color):raise ValueError('Cor de moldura inválida: '+k)
            obj[k]=color
        for k,lo,hi in [('shear',-2,2),('pivot_x',-.5,.5),('pivot_y',-.5,.5)]:
            if k in item:obj[k]=n(item[k],0,lo,hi)
        stack=item.get('motion_programs',[])
        if not isinstance(stack,list) or len(stack)>8 or any(not isinstance(v,str) or len(v.encode('utf8'))>16000 for v in stack):raise ValueError('Programas GIL inválidos')
        obj['motion_programs']=stack
        if kind=='gil':
            t=item.get('title_spec')
            if isinstance(t,dict):obj['title_spec']={k:str(t.get(k,''))[:cap] for k,cap in [('text',110),('subtitle',100),('style',30),('entry',32),('exit',32)]}
        if kind=='video':
            obj['audio_enabled']=item.get('audio_enabled',True) is not False
            obj['audio_volume']=n(item.get('audio_volume',1),1,0,3)
            obj['audio_fade_in']=n(item.get('audio_fade_in',.12),.12,0,5)
            obj['audio_fade_out']=n(item.get('audio_fade_out',.12),.12,0,5)
        if kind=='gil':
            g=gil_component_dict(item.get('gil'))
            if not g or g['origin']!='gil':raise ValueError('Fonte GIL inválida')
            obj['gil']=g
        else:
            f=asset(item.get('file'));ext=f.rsplit('.',1)[-1].lower()
            if ext not in (('jpg','jpeg','png','webp') if kind=='image' else ('mp4','webm','ogv','mov','m4v','mkv')):raise ValueError('Tipo de mídia incompatível')
            obj['file']=f
            if kind=='image':
                obj['source_file']=asset(item.get('source_file',f))
                obj['source_crop']=image_crop(item.get('source_crop',[]))
        out.append(obj)
    return out


def video_clip_dict(raw):
    """A video is an independently positioned layer above the scene artwork."""
    v=raw if isinstance(raw,dict) else {}
    return {'arquivo':asset(v.get('arquivo','')),
      'x':n(v.get('x',.5),.5,0,1), 'y':n(v.get('y',.56),.56,0,1),
      'w':n(v.get('w',.70),.70,.08,1),'h':n(v.get('h',.40),.40,.08,1),
      'fit':v.get('fit','cover') if v.get('fit') in ('cover','contain') else 'cover',
      'inicio':n(v.get('inicio',0),0,0,3600),
      'repetir':bool(v.get('repetir',True)),
      'opacidade':n(v.get('opacidade',1),1,0,1),
      'audio_enabled':v.get('audio_enabled',False) is True,
      'audio_volume':n(v.get('audio_volume',1),1,0,3),
      'audio_fade_in':n(v.get('audio_fade_in',.12),.12,0,5),
      'audio_fade_out':n(v.get('audio_fade_out',.12),.12,0,5)}


def image_crop(raw):
    if not isinstance(raw,list) or len(raw)!=4:return []
    values=[n(z,0,0,1) for z in raw]
    x,y,w,h=values
    if w<=.001 or h<=.001:return []
    return [x,y,min(w,1-x),min(h,1-y)] if x<1 and y<1 else []

def animation_dict(raw):
    """Normaliza timelines SVG; grupos alvos+intervalo geram faixas escalonadas."""
    if not isinstance(raw,list):return []
    result=[]
    for a in raw[:32]:
        if not isinstance(a,dict):continue
        kind=a.get('tipo')
        if kind not in ('translacao','rotacao','escala','fade'):continue
        targets=a.get('alvos')
        if not isinstance(targets,list): targets=[a.get('alvo','')]
        if not 1<=len(targets)<=16:continue
        start=n(a.get('inicio',0),0,0,1)
        finish=n(a.get('fim',1),1,0,1)
        if finish<=start:finish=min(1,start+.01)
        if finish<=start:continue
        stagger=n(a.get('intervalo',0),0,0,.5)
        lo,hi= ((0,1) if kind=='fade' else ((-8,8) if kind=='escala' else (-3600,3600)))
        easing=a.get('easing') if a.get('easing') in EASINGS else 'suave'
        for i,raw_target in enumerate(targets):
            target=str(raw_target)[:85]
            if not (target=='__imagem__' or re.fullmatch(r'[A-Za-z_][A-Za-z0-9_.:-]{0,80}',target)):continue
            this_start=min(1.,start+i*stagger)
            this_finish=min(1.,finish+i*stagger)
            if this_finish <= this_start:continue
            result.append({'alvo':target,'tipo':kind,'inicio':this_start,'fim':this_finish,
                'easing':easing,'repeticoes':int(n(a.get('repeticoes',0),0,0,20)),
                'yoyo':bool(a.get('yoyo',False)),
                'de':n(a.get('de',1 if kind=='escala' else 0),1 if kind=='escala' else 0,lo,hi),
                'ate':n(a.get('ate',1 if kind=='escala' else (1 if kind=='fade' else 0)),1 if kind=='escala' else (1 if kind=='fade' else 0),lo,hi),
                'de_x':n(a.get('de_x',0),0,-3500,3500),'de_y':n(a.get('de_y',0),0,-3500,3500),
                'ate_x':n(a.get('ate_x',0),0,-3500,3500),'ate_y':n(a.get('ate_y',0),0,-3500,3500)})
            if len(result)>=32:return result
    return result


VISUAL_LAYERS=('imagem','conteudo','cabecalho','titulo','subtitulo','rodape')

def layers_dict(raw,modo="quadro"):
    if not isinstance(raw,dict):return {}
    out={}
    for key in VISUAL_LAYERS:
        value=raw.get(key)
        if not isinstance(value,dict):continue
        default_z=(10 if modo=='fundo' else 30) if key=='imagem' else {'conteudo':20,'cabecalho':40,'titulo':50,'subtitulo':60,'rodape':70}[key]
        item={'z':int(n(value.get('z',default_z),default_z,-10000,10000)),
              'dx':n(value.get('dx',0),0,-4800,4800),'dy':n(value.get('dy',0),0,-4800,4800),
              'oculta':value.get('oculta') is True}
        out[key]=item
    return out

def spatialseed_viewport_dict(raw, duration):
    """Opt-in native WebGL scene; never execute documents as arbitrary JavaScript."""
    if not isinstance(raw, dict):
        raise ValueError('Viewport SpatialSeed deve ser um objeto')
    enabled=raw.get('enabled') is True
    source=raw.get('source','')
    if not isinstance(source,str) or len(source.encode('utf-8'))>900000:
        raise ValueError('Fonte SpatialSeed acima de 900 kB ou inválida')
    if source:
        try: doc=json.loads(source)
        except (ValueError,TypeError): raise ValueError('Fonte SpatialSeed não é JSON')
        if not isinstance(doc,dict): raise ValueError('Documento SpatialSeed deve ser objeto JSON')
    keys=raw.get('camera_keys',[])
    if not isinstance(keys,list) or len(keys)>256:
        raise ValueError('Até 256 keyframes de câmera por cena')
    result=[];prev=-1.
    for index,k in enumerate(keys):
        if not isinstance(k,dict):raise ValueError('Keyframe inválido')
        t=n(k.get('t'),-1,-1,600)
        if t<0 or t>duration or t<=prev:raise ValueError('Keyframes devem estar ordenados por tempo crescente')
        prev=t
        camera=k.get('camera')
        if not isinstance(camera,dict):raise ValueError('Pose de câmera inválida')
        position=camera.get('position');q=camera.get('quaternion')
        if not isinstance(position,list) or len(position)!=3 or not all(isinstance(x,(int,float)) and math.isfinite(x) for x in position):raise ValueError('Posição de câmera inválida')
        if not isinstance(q,list) or len(q)!=4 or not all(isinstance(x,(int,float)) and math.isfinite(x) for x in q):raise ValueError('Quaternion inválido')
        mag=sum(float(v)*float(v) for v in q)**.5
        if mag<1e-12:raise ValueError('Quaternion nulo')
        dist=float(camera.get('focusDistance',0));fov=float(camera.get('fov',0))
        near=float(camera.get('near',0));far=float(camera.get('far',0))
        if not all(math.isfinite(x) for x in (dist,fov,near,far)) or dist<=0 or not 1<=fov<=179 or near<=0 or far<=near:raise ValueError('Óptica de câmera inválida')
        easing=k.get('easing','smoothstep')
        if easing not in ('linear','smoothstep','hold'):raise ValueError('Interpolação de câmera inválida')
        result.append({'t':t,'easing':easing,'camera':{'position':[float(x) for x in position],
                       'quaternion':[float(x)/mag for x in q],
                       'focusDistance':dist,'fov':fov,'near':near,'far':far}})
    return {'enabled':enabled,'source':source,'camera_keys':result}


def normalize(data):
    if not isinstance(data,dict):raise ValueError('O projeto deve ser objeto JSON')
    lib_data = normalize_library(data.get('instance_library'), media_objects_dict)
    m1t_library, m1t_counts = lib_data if lib_data is not None else (None, {})
    raw=data.get('cenas')
    if not isinstance(raw,list) or not 1<=len(raw)<=150:raise ValueError('São necessárias entre 1 e 150 cenas')
    video=data.get('video',{}) if isinstance(data.get('video'),dict) else {}
    w=int(video.get('width',data.get('largura',1280)));h=int(video.get('height',data.get('altura',720)))
    if w<320 or h<320 or w>1920 or h>1920 or w%2 or h%2:raise ValueError('Resolução: dimensões pares entre 320 e 1920')
    fps=int(video.get('fps',data.get('fps_saida',24)));draw=int(video.get('draw_fps',data.get('fps_desenho',6)))
    if fps not in (24,25,30):raise ValueError('FPS saída: 24, 25 ou 30')
    if draw not in (1,2,3,4,6,8,10,12,15,24):raise ValueError('FPS desenho inválido')
    out={'versao':VERSION,'titulo':str(data.get('titulo','Novo filme'))[:180],
         'audio_score':str(data.get('audio_score',''))[:30000],
         'video':{'width':w,'height':h,'fps':fps,'draw_fps':draw,'background':color(video.get('background','#241b1a'),'#241b1a')},
         'voz':str(data.get('voz','pt-BR-AntonioNeural'))[:80], 'velocidade_voz':str(data.get('velocidade_voz','+0%'))[:15],
         'motor_voz':data.get('motor_voz','edge-tts') if data.get('motor_voz','edge-tts') in ('edge-tts','espeak-ng','piper') else 'edge-tts',
         'modelo_piper':asset(data.get('modelo_piper','')),'voz_espeak':str(data.get('voz_espeak','pt-br'))[:50],
         'velocidade_espeak':int(n(data.get('velocidade_espeak',165),165,80,260)),
         'encaixe_voz':data.get('encaixe_voz','estender') if data.get('encaixe_voz') in ('estender','avisar') else 'estender',
         'trilha':asset(data.get('trilha','')),'trilha_continua':bool(data.get('trilha_continua',False)),'volume_musica':n(data.get('volume_musica',.16),.16,0,2),
         'volume_voz':n(data.get('volume_voz',1.35),1.35,0,3),'cenas':[]}
    if data.get('voice') is not None:out['voice']=studio_voice_config(data['voice'])
    if m1t_library is not None:out['instance_library']=m1t_library
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
            'animacoes':animation_dict(r.get('animacoes',[])),
            'video_clipe':video_clip_dict(r.get('video_clipe',{})),
            'imagem':image_dict(image,h>w,typ=='foto'),
            'cores':{k:color(cs.get(k),COLORS[k]) for k in COLORS},
            'audio':audio_dict(r.get('audio'),r.get('fala','')),'legendas':subtitle_dict(r.get('legendas'))}
        camadas=layers_dict(r.get('camadas'),c['imagem']['modo'])
        if camadas:c['camadas']=camadas
        component=gil_component_dict(r.get('componente_gil'))
        if component and c['video_clipe']['arquivo']:c['componente_gil']=component
        if 'gil_nativo' in r:
            native=r['gil_nativo']; layer=gil_component_dict(native)
            if layer is None or layer['origin']!='gil':raise ValueError(f'Cena {i+1}: camada GIL nativa inválida')
            layer.update({k:n(native.get(k,d),d,lo,hi) for k,d,lo,hi in [('x',.5,0,1),('y',.5,0,1),('w',1,.08,1),('h',1,.08,1),('opacidade',1,0,1)]})
            layer['opaque']=native.get('opaque') is True
            if 'source_spatialseed' in native:
                original=native['source_spatialseed']
                if not isinstance(original,str) or not 0<len(original.encode('utf-8'))<=250000:
                    raise ValueError(f'Cena {i+1}: documento SpatialSeed original inválido')
                if hashlib.sha256(original.encode('utf-8')).hexdigest()!=layer['origin_sha256']:
                    raise ValueError(f'Cena {i+1}: SHA-256 do SpatialSeed original não corresponde')
                layer['source_spatialseed']=original
            c['gil_nativo']=layer
        if 'objetos_midia' in r:c['objetos_midia']=media_objects_dict(r['objetos_midia'])
        if 'instances' in r:
            if m1t_library is None:raise ValueError('Cena contém instâncias sem biblioteca')
            c['instances']=normalize_roots(r['instances'],m1t_counts,c['duracao'])
        if 'spatialseed_viewport' in r:c['spatialseed_viewport']=spatialseed_viewport_dict(r['spatialseed_viewport'],c['duracao'])
        if typ=='espacial': c['espacial']=normalize_spatial(r.get('espacial',default_spatial()))
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
