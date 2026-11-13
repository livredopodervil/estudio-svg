"""Interpolação declarativa independente; conceitos de timelines (sem biblioteca GSAP)."""
from __future__ import annotations
import math

EASINGS = ('linear', 'suave', 'power1.in', 'power1.out', 'power1.inOut',
           'power2.in', 'power2.out', 'power2.inOut', 'power3.inOut',
           'sine.in', 'sine.out', 'sine.inOut', 'expo.out', 'back.out', 'bounce.out')


def ease(t, name='suave'):
    t = max(0.0, min(1.0, float(t)))
    if name == 'linear': return t
    if name == 'suave': return t*t*(3-2*t)
    if name.startswith('power'):
        power = int(name[5]) + 1
        if name.endswith('.inOut'):
            return (2**(power-1)*t**power if t < .5 else 1-((-2*t+2)**power)/2)
        if name.endswith('.out'): return 1-(1-t)**power
        return t**power
    if name == 'sine.in': return 1-math.cos(t*math.pi/2)
    if name == 'sine.out': return math.sin(t*math.pi/2)
    if name == 'sine.inOut': return -(math.cos(math.pi*t)-1)/2
    if name == 'expo.out': return 1 if t >= 1 else 1-2**(-10*t)
    if name == 'back.out':
        v=t-1
        return 1+2.70158*v**3+1.70158*v**2
    if name == 'bounce.out':
        if t < 1/2.75: return 7.5625*t*t
        if t < 2/2.75:
            t-=1.5/2.75;return 7.5625*t*t+.75
        if t < 2.5/2.75:
            t-=2.25/2.75;return 7.5625*t*t+.9375
        t-=2.625/2.75;return 7.5625*t*t+.984375
    return t*t*(3-2*t)


def progress(track, position):
    """Evalua uma faixa entre inicio/fim, com ciclos finitos e yoyo, sem estado."""
    start=float(track['inicio']);end=float(track['fim'])
    if position <= start: return ease(0, track.get('easing','suave'))
    cycles = max(1, min(21, int(track.get('repeticoes', 0)) + 1))
    reverse=bool(track.get('yoyo',False))
    if position >= end:
        last=0.0 if reverse and cycles%2 == 0 else 1.0
        return ease(last,track.get('easing','suave'))
    total=max(0.,min(1.,(position-start)/max(1.e-9,end-start)))*cycles
    index=min(cycles-1,int(total))
    local=total-index
    if reverse and index%2:local=1-local
    return ease(local,track.get('easing','suave'))
