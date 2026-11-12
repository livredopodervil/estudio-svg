"""Render one optional local video clip over a scene's vector output.

A clip is a rectangular overlay in normalized video-frame coordinates.
Audio is not duplicated: it can be referenced independently as voice_file.
"""
from __future__ import annotations
from pathlib import Path
import subprocess


def geometry(clip, width, height):
    w=max(2, 2*round(width*clip['w']/2))
    h=max(2, 2*round(height*clip['h']/2))
    x=round(width*clip['x']-w/2)
    y=round(height*clip['y']-h/2)
    return x,y,w,h


def clip_filter(clip, width, height, fps):
    x,y,w,h=geometry(clip,width,height)
    if clip['fit']=='contain':
        resize=(f'scale={w}:{h}:force_original_aspect_ratio=decrease,'
            f'pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:color=black')
    else:
        resize=(f'scale={w}:{h}:force_original_aspect_ratio=increase,'
            f'crop={w}:{h}')
    alpha=clip['opacidade']
    return (f'[1:v]fps={fps},{resize},format=yuva420p,'
            f'colorchannelmixer=aa={alpha:.4f}[clip];'
            f'[0:v][clip]overlay=x={x}:y={y}:shortest=0:'
            'repeatlast=0:eof_action=pass:format=auto[v]')


def overlay_clip(base, source, target, clip, width, height, fps, seconds, run):
    args=['ffmpeg','-hide_banner','-loglevel','error','-nostdin','-y',
          '-i',str(base)]
    if clip['repetir']:args+=['-stream_loop','-1']
    if clip['inicio']>0:args+=['-ss',f"{clip['inicio']:.4f}"]
    args+=['-i',str(source),'-filter_complex',clip_filter(clip,width,height,fps),
           '-map','[v]','-t',f'{seconds:.5f}', '-an',
           '-c:v','libx264','-threads','2','-preset','veryfast','-crf','25',
           '-pix_fmt','yuv420p','-movflags','+faststart',str(target)]
    run(args,timeout=max(120,int(seconds*8)))
