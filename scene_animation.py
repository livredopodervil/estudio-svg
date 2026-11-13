"""Time-keyed, deterministic SVG element animation shared by preview and MP4."""
from __future__ import annotations
import math
import xml.etree.ElementTree as ET
from timeline_easing import ease as _ease, progress as _progress


def ease(progress, mode):
    return _ease(progress, mode)


def progress_at(animation, position):
    return _progress(animation, position)


def pivot(element):
    """Geometrical pivot for common shapes (path fallback: canvas centre)."""
    def val(key, default=0):
        try:
            x=float(element.get(key, default))
            return x if math.isfinite(x) else default
        except (ValueError, TypeError):return default
    tag = element.tag.split('}')[-1]
    if tag in ('circle', 'ellipse'):return val('cx',640),val('cy',360)
    if tag in ('rect', 'image'):return val('x')+val('width')/2,val('y')+val('height')/2
    if tag in ('text', 'tspan'):return val('x',640),val('y',360)
    if tag == 'line':return (val('x1')+val('x2'))/2,(val('y1')+val('y2'))/2
    return 640,360


def effects(animations, target, position, center=(640,360)):
    """Return transform prefix and alpha for one target; original transforms survive."""
    transforms=[]
    opacity=1.
    x,y=center
    for a in animations:
        if a['alvo'] != target:continue
        t=progress_at(a,position)
        kind=a['tipo']
        if kind=='translacao':
            dx=a['de_x']+(a['ate_x']-a['de_x'])*t
            dy=a['de_y']+(a['ate_y']-a['de_y'])*t
            transforms.append(f'translate({dx:.4f} {dy:.4f})')
        elif kind=='rotacao':
            ang=a['de']+(a['ate']-a['de'])*t
            transforms.append(f'rotate({ang:.4f} {x:.4f} {y:.4f})')
        elif kind=='escala':
            factor=a['de']+(a['ate']-a['de'])*t
            transforms.append(f'translate({x:.4f} {y:.4f}) scale({factor:.5f}) translate({-x:.4f} {-y:.4f})')
        elif kind=='fade':
            opacity *= max(0.,min(1.,a['de']+(a['ate']-a['de'])*t))
    return ' '.join(transforms), opacity


def animate_svg_fragment(fragment, animations, position):
    if not animations:return fragment
    root=ET.fromstring(fragment)
    targets={a['alvo'] for a in animations if a['alvo']!='__imagem__'}
    for element in root.iter():
        target=element.get('id')
        if not target or target not in targets:continue
        transform,opacity=effects(animations,target,position,pivot(element))
        if transform:element.set('transform',(transform+' '+(element.get('transform') or '')).strip())
        if opacity!=1.:
            try:original=float(element.get('opacity',1))
            except ValueError:original=1.
            element.set('opacity',f'{max(0.,min(1.,original*opacity)):.4f}')
    return ET.tostring(root,encoding='unicode')


def animate_markup(markup, animations, position, target, center):
    if not markup:return ''
    transform,opacity=effects(animations,target,position,center)
    if not transform and opacity==1.:return markup
    return f'<g transform="{transform}" opacity="{opacity:.4f}">{markup}</g>'


def animate_image_markup(markup, animations, position, center):
    return animate_markup(markup,animations,position,'__imagem__',center)
