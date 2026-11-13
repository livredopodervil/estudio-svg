"""Estúdio SVG V3 experimental: cena espacial declarativa e projeção SVG determinística.

Este módulo NÃO importa nem copia o runtime do SpatialSeed: é um contrato
mínimo interoperável a ser evoluído após auditoria da API e das licenças.
Python stdlib only; o mesmo SVG chega à prévia e ao pipeline FFmpeg.
"""
from __future__ import annotations
import html
import math
import re
from timeline_easing import EASINGS, progress as timeline_progress

IDENT = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_-]{0,39}$")
HEX = re.compile(r"^#[0-9a-fA-F]{6}$")
TYPES = {'cubo', 'esfera', 'piramide', 'cilindro', 'cone', 'grupo'}
PROPS = {'rotacao_x', 'rotacao_y', 'rotacao_z', 'posicao_x', 'posicao_y', 'posicao_z', 'escala'}
CAMERA_PROPS = {'azimute', 'elevacao', 'distancia'}


def number(raw, default, lo, hi):
    try: val = float(raw)
    except (TypeError, ValueError, OverflowError): return default
    return max(lo, min(hi, val)) if math.isfinite(val) else default


def vector(raw, default, lo, hi):
    if not isinstance(raw, (tuple, list)) or len(raw) != 3: return list(default)
    return [number(x, d, lo, hi) for x, d in zip(raw, default)]


def color(raw, fallback):
    return raw if isinstance(raw, str) and HEX.fullmatch(raw) else fallback


def default_spatial():
    return normalize_spatial({
        'camera': {'azimute': 28, 'elevacao': 18, 'distancia': 9},
        'objetos': [
            {'id': 'centro', 'tipo': 'esfera', 'cor': '#67bfe9', 'posicao': [-1.5, 0, 0]},
            {'id': 'bloco', 'tipo': 'cubo', 'cor': '#e4a46d', 'posicao': [1.3, 0, 0]},
        ],
        'animacoes': [
            {'alvo': 'bloco', 'propriedade': 'rotacao_y', 'inicio': 0, 'fim': 1, 'de': 0, 'ate': 360}
        ]
    })


def normalize_spatial(raw):
    if not isinstance(raw, dict): raw = {}
    camera = raw.get('camera') if isinstance(raw.get('camera'), dict) else {}
    normalized = {'camera': {
        'azimute': number(camera.get('azimute'), 28, -360, 360),
        'elevacao': number(camera.get('elevacao'), 18, -80, 80),
        'distancia': number(camera.get('distancia'), 9, 3, 40),
        'alvo': vector(camera.get('alvo'), [0, 0, 0], -10, 10),
    }, 'objetos': [], 'animacoes': []}
    items = raw.get('objetos', [])
    if not isinstance(items, list): items = []
    if len(items) > 32: raise ValueError('Cena espacial: máximo de 32 objetos')
    used = set()
    for i, obj in enumerate(items):
        if not isinstance(obj, dict): continue
        ident = obj.get('id', 'obj_' + str(i+1))
        if not isinstance(ident, str) or not IDENT.fullmatch(ident) or ident in used:
            raise ValueError('Cena espacial: identificador inválido ou repetido')
        typ = obj.get('tipo', 'cubo')
        if typ not in TYPES: raise ValueError('Cena espacial: geometria inválida')
        used.add(ident)
        normalized['objetos'].append({
            'id': ident, 'tipo': typ,
            'posicao': vector(obj.get('posicao'), [0, 0, 0], -20, 20),
            'rotacao': vector(obj.get('rotacao'), [0, 0, 0], -3600, 3600),
            'escala': number(obj.get('escala'), 1, .1, 5),
            'cor': color(obj.get('cor'), '#64bcdb'),
            'visivel': bool(obj.get('visivel', True)),
            'pai': str(obj.get('pai') or ''),
        })
    # Parent transform graph; check references and cycles before rendering.
    objects={o['id']:o for o in normalized['objetos']}
    for item in objects.values():
        parent=item['pai']
        if parent and parent not in objects:raise ValueError('Cena espacial: objeto-pai inexistente')
        if parent==item['id']:raise ValueError('Cena espacial: pai de si mesmo')
    for item in objects.values():
        current=item;seen=set()
        while current['pai']:
            if current['id'] in seen:raise ValueError('Cena espacial: ciclo na hierarquia de objetos')
            seen.add(current['id']);current=objects[current['pai']]
    tracks = raw.get('animacoes', [])
    if not isinstance(tracks, list): tracks = []
    if len(tracks) > 64: raise ValueError('Cena espacial: máximo de 64 faixas')
    for track in tracks:
        if not isinstance(track, dict): continue
        is_cam=track.get('alvo')=='__camera__'
        prop=track.get('propriedade')
        if (is_cam and prop not in CAMERA_PROPS) or (not is_cam and (track.get('alvo') not in used or prop not in PROPS)):
            raise ValueError('Cena espacial: faixa aponta para objeto ou propriedade desconhecidos')
        start = number(track.get('inicio'), 0, 0, 1)
        end = number(track.get('fim'), 1, 0, 1)
        if not end > start: raise ValueError('Cena espacial: fim de animação deve superar início')
        prop = track['propriedade']
        default_to = 360 if prop.startswith('rotacao_') or prop=='azimute' else 1 if prop == 'escala' else 0
        if is_cam:
            lo,hi = (3,40) if prop=='distancia' else (-80,80) if prop=='elevacao' else (-1080,1080)
        else:
            lo,hi = (.1,5) if prop == 'escala' else (-20,20) if prop.startswith('posicao_') else (-3600,3600)
        normalized['animacoes'].append({
            'alvo': track['alvo'], 'propriedade': prop,
            'inicio': start, 'fim': end,
            'de': number(track.get('de'), 1 if prop == 'escala' else 0, lo, hi),
            'ate': number(track.get('ate'), default_to, lo, hi),
            'easing': track.get('easing') if track.get('easing') in EASINGS else 'suave',
            'repeticoes': int(number(track.get('repeticoes'),0,0,20)),
            'yoyo': bool(track.get('yoyo',False)),
        })
    return normalized


def _add(a,b):return tuple(x+y for x,y in zip(a,b))
def _sub(a,b):return tuple(x-y for x,y in zip(a,b))
def _mul(a,s):return tuple(x*s for x in a)
def _dot(a,b):return sum(x*y for x,y in zip(a,b))
def _cross(a,b):return (a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])
def _unit(a):return _mul(a,1/max(1e-10,math.sqrt(_dot(a,a))))


def _rotated(v,r):
    x,y,z=v
    for axis,deg in enumerate(r):
        a=math.radians(deg);c=math.cos(a);s=math.sin(a)
        if axis==0:y,z=y*c-z*s,y*s+z*c
        elif axis==1:x,z=x*c+z*s,-x*s+z*c
        else:x,y=x*c-y*s,x*s+y*c
    return (x,y,z)


def camera_pose(camera, tracks, progress):
    result=dict(camera)
    progress=max(0,min(1,float(progress)))
    for track in tracks:
        if track['alvo']!='__camera__':continue
        f=timeline_progress(track,progress)
        result[track['propriedade']]=track['de']+(track['ate']-track['de'])*f
    return result


def pose(obj, tracks, progress):
    """Retorna pose imutável calculada apenas a partir do tempo absoluto [0,1]."""
    position = list(obj['posicao']);rotation = list(obj['rotacao']);scale = obj['escala']
    progress=max(0,min(1,float(progress)))
    for a in tracks:
        if a['alvo']!=obj['id']:continue
        f=timeline_progress(a,progress)
        value=a['de']+(a['ate']-a['de'])*f
        prop=a['propriedade']
        if prop=='escala':scale=value
        elif prop.startswith('posicao_'):position['xyz'.index(prop[-1])]=value
        elif prop.startswith('rotacao_'):rotation['xyz'.index(prop[-1])]=value
    return position, rotation, scale


def _rgb(hexcolor, factor):
    vals=[int(hexcolor[i:i+2],16) for i in (1,3,5)]
    return '#'+''.join(f'{int(max(0,min(255,v*factor))):02x}' for v in vals)


def render_spatial(spatial, progress, height=720):
    """Geometria 3D projetada no SVG para prévia e exportação idênticas.

    Primeiro marco: polígonos planos com sombreamento simples, não WebGL/PBR.
    """
    camera=camera_pose(spatial['camera'],spatial['animacoes'],progress);yaw=math.radians(camera['azimute']);pitch=math.radians(camera['elevacao'])
    target=tuple(camera['alvo']);d=camera['distancia']
    cpos=_add(target,(d*math.cos(pitch)*math.sin(yaw),d*math.sin(pitch),d*math.cos(pitch)*math.cos(yaw)))
    forward=_unit(_sub(target,cpos));right=_unit(_cross(forward,(0,1,0)));up=_cross(right,forward)
    focal=1100.;center=(640.,height*.55)
    def camera_coordinates(point):
        v=_sub(point,cpos)
        return (_dot(v,right),_dot(v,up),_dot(v,forward))
    def project(point):
        x,y,z=camera_coordinates(point)
        if z<.1:return None
        return (center[0]+focal*x/z,center[1]-focal*y/z,z)
    elements=['<g id="spatial-world">']
    # Chão leve, sem impedir cenas transparentes ou textos sobrepostos.
    for n in range(-4,5):
        for a,b in (((n,-1.7,-4),(n,-1.7,4)),((-4,-1.7,n),(4,-1.7,n))):
            pa=project(a);pb=project(b)
            if pa and pb:
                elements.append(f'<path d="M{pa[0]:.2f} {pa[1]:.2f} L{pb[0]:.2f} {pb[1]:.2f}" stroke="#8696b4" stroke-opacity=".18" stroke-width="2"/>')
    cube_verts=[(x,y,z) for x,y,z in ((-1,-1,-1),(1,-1,-1),(1,1,-1),(-1,1,-1),(-1,-1,1),(1,-1,1),(1,1,1),(-1,1,1))]
    cube_faces=[(0,3,2,1),(4,5,6,7),(0,4,7,3),(1,2,6,5),(3,7,6,2),(0,1,5,4)]
    pyr_verts=[(-1,-1,-1),(1,-1,-1),(1,-1,1),(-1,-1,1),(0,1.4,0)]
    pyr_faces=[(0,3,2,1),(0,1,4),(1,2,4),(2,3,4),(3,0,4)]
    nseg=16
    cylinder_verts=[(math.cos(2*math.pi*i/nseg),y,math.sin(2*math.pi*i/nseg))
                    for y in (-1,1) for i in range(nseg)]
    cylinder_faces=[tuple(range(nseg-1,-1,-1)),tuple(range(nseg,2*nseg))]
    cylinder_faces += [(i,(i+1)%nseg,(i+1)%nseg+nseg,i+nseg) for i in range(nseg)]
    cone_verts=[(math.cos(2*math.pi*i/nseg),-1,math.sin(2*math.pi*i/nseg)) for i in range(nseg)]+[(0,1,0)]
    cone_faces=[tuple(range(nseg-1,-1,-1))]+[(i,(i+1)%nseg,nseg) for i in range(nseg)]
    shapes={'cubo':(cube_verts,cube_faces),'piramide':(pyr_verts,pyr_faces),
            'cilindro':(cylinder_verts,cylinder_faces),'cone':(cone_verts,cone_faces)}
    poses={o['id']:pose(o,spatial['animacoes'],progress) for o in spatial['objetos']}
    objects={o['id']:o for o in spatial['objetos']}
    def world_point(obj,vertex):
        current=obj
        point=vertex
        while current:
            pos,rot,scale=poses[current['id']]
            point=_add(_rotated(_mul(point,scale),rot),pos)
            current=objects.get(current['pai']) if current['pai'] else None
        return point
    def global_scale(obj):
        scale=1.;current=obj
        while current:
            scale*=poses[current['id']][2]
            current=objects.get(current['pai']) if current['pai'] else None
        return scale
    polygons=[]
    for obj in spatial['objetos']:
        if not obj['visivel']:continue
        pos,rot,scale=poses[obj['id']]
        if obj['tipo']=='grupo':continue
        if obj['tipo']=='esfera':
            point=project(world_point(obj,(0,0,0)))
            if point:
                x,y,z=point;r=1100*global_scale(obj)/z
                if r>0:
                    safe=html.escape(obj['id']);c=obj['cor']
                    elements.append(f'<defs><radialGradient id="spg-{safe}" cx="30%" cy="25%"><stop stop-color="{_rgb(c,1.65)}"/><stop offset=".7" stop-color="{c}"/><stop offset="1" stop-color="{_rgb(c,.35)}"/></radialGradient></defs>')
                    polygons.append((z, f'<circle cx="{x:.2f}" cy="{y:.2f}" r="{r:.2f}" fill="url(#spg-{safe})" stroke="{_rgb(c,1.2)}" stroke-width="2"/>'))
            continue
        vertices,faces=shapes[obj['tipo']]
        world=[world_point(obj,v) for v in vertices]
        for face in faces:
            coords=[project(world[j]) for j in face]
            if not all(coords):continue
            a,b,c=[world[j] for j in face[:3]]
            normal=_unit(_cross(_sub(b,a),_sub(c,a)))
            light=max(.24,.52+.43*_dot(normal,_unit((-.35,.8,.55))))
            path=' '.join(f'{p[0]:.2f},{p[1]:.2f}' for p in coords)
            fill=_rgb(obj['cor'],light)
            polygons.append((sum(p[2] for p in coords)/len(coords),f'<polygon points="{path}" fill="{fill}" stroke="{_rgb(obj["cor"],.72)}" stroke-width="2" stroke-linejoin="round"/>'))
    # Painter's order: nearest opaque shapes cover farther shapes.
    elements.extend(mark for _,mark in sorted(polygons,key=lambda v:-v[0]))
    elements.append('</g>')
    return ''.join(elements)
