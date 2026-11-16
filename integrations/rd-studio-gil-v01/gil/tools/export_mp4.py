#!/usr/bin/env python3
"""Offline export adapter for GIL SVG projection and synthesized sound cues.
No writes to source/project directory. Requires Node, FFmpeg, and CairoSVG or rsvg-convert.
"""
import argparse, array, importlib.util, json, math, os, shutil, subprocess, tempfile, wave
from pathlib import Path
ROOT=Path(__file__).resolve().parent

def audio_wav(plan,path):
    rate=48000; length=round(plan['duration']*rate); samples=array.array('f',[0.])*length
    for cue in plan['cues']:
        start=round(cue['start']*rate); count=min(length-start,round(cue['duration']*rate)); ramp=max(1,round(min(.035,cue['duration']/3)*rate))
        for i in range(max(0,count)):
            phase=(i*cue['frequency']/rate)%1
            kind=cue['wave']; v=math.sin(math.tau*phase) if kind=='sine' else (2/math.pi*math.asin(math.sin(math.tau*phase)) if kind=='triangle' else (1 if phase<.5 else -1) if kind=='square' else 2*phase-1)
            gain=min(1,i/ramp,(count-1-i)/ramp)*cue['gain']; samples[start+i]+=v*gain
    pcm=array.array('h',(round(max(-1,min(1,s))*32767) for s in samples))
    if os.sys.byteorder!='little':pcm.byteswap()
    with wave.open(str(path),'wb') as w:w.setnchannels(1);w.setsampwidth(2);w.setframerate(rate);w.writeframes(pcm.tobytes())

def export(source,dest,fps=24,long_side=960,duration=None,silent=False):
    source=Path(source).resolve();dest=Path(dest).absolute()
    if not source.is_file() or dest.suffix.lower()!='.mp4' or dest.exists() or dest.is_symlink():raise ValueError('Fonte inexistente ou destino MP4 já existe')
    if not 12<=fps<=30 or not 320<=long_side<=1280:raise ValueError('FPS 12–30; resolução 320–1280')
    for executable in ('node','ffmpeg','ffprobe'):
        if not shutil.which(executable):raise RuntimeError('Comando ausente: '+executable)
    rsvg=shutil.which('rsvg-convert'); cairo=importlib.util.find_spec('cairosvg') is not None
    if not rsvg and not cairo:raise RuntimeError('Rasterizador ausente: instale rsvg-convert (librsvg) ou CairoSVG no ambiente escolhido. Nenhum fallback de qualidade desconhecida.')
    dest.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='gil-export-',dir=str(dest.parent)) as tmp:
        t=Path(tmp);subprocess.run(['node',str(ROOT/'export_frames.mjs'),str(source),str(t),str(fps),str(duration) if duration is not None else ''],check=True)
        plan=json.loads((t/'plan.json').read_text()); st=plan['stage']; ratio=long_side/max(st['width'],st['height']);width=max(2,round(st['width']*ratio/2)*2);height=max(2,round(st['height']*ratio/2)*2)
        if not rsvg:import cairosvg
        for i in range(plan['frames']):
            name=f'frame-{i:05d}'; svg=t/(name+'.svg'); png=t/(name+'.png')
            if rsvg:subprocess.run([rsvg,'-w',str(width),'-h',str(height),'-o',str(png),str(svg)],check=True)
            else:cairosvg.svg2png(url=str(svg),write_to=str(png),output_width=width,output_height=height)
            svg.unlink()
            if (i+1)%120==0:print(f'Quadros: {i+1}/{plan["frames"]}',flush=True)
        args=['ffmpeg','-hide_banner','-loglevel','error','-nostdin','-n','-framerate',str(fps),'-i',str(t/'frame-%05d.png')]
        if not silent:
            audio_wav(plan,t/'audio.wav');args+=['-i',str(t/'audio.wav'),'-c:a','aac','-b:a','96k']
        else:args+=['-an']
        result=t/'result.mp4';args+=['-c:v','libx264','-pix_fmt','yuv420p','-preset','fast','-crf','23','-movflags','+faststart',str(result)];subprocess.run(args,check=True)
        probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(result)]));streams=probe['streams'];vid=next(s for s in streams if s['codec_type']=='video');
        if vid['codec_name']!='h264' or vid['width']!=width or vid['height']!=height or (not silent and not any(s['codec_name']=='aac' for s in streams)):raise RuntimeError('FFprobe: saída não corresponde ao contrato')
        # exclusive destination; no overwrite, even if another process created it
        with dest.open('xb') as dst:
            try:
                with result.open('rb') as src:shutil.copyfileobj(src,dst)
                dst.flush()
            except BaseException:
                dst.close();dest.unlink();raise
        print(f'MP4: {dest} | {width}x{height} | {plan["duration"]:.3f} s | {dest.stat().st_size} bytes')
        if dest.stat().st_size>8*1024*1024:print('Aviso: excede o limite individual RD Patch 1.0 (8 MiB).')
    return dest
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('source');p.add_argument('output');p.add_argument('--fps',type=int,default=24);p.add_argument('--long-side',type=int,default=960);p.add_argument('--duration',type=float);p.add_argument('--silent',action='store_true');a=p.parse_args();export(a.source,a.output,a.fps,a.long_side,a.duration,a.silent)
