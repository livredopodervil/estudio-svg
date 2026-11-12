"""V2.7.2 regression coverage: schema, visual animation and uninterrupted music."""
import math
import shutil
import tempfile
import unittest
import wave
import struct
from pathlib import Path
import xml.etree.ElementTree as ET

from schema import normalize
from scene_animation import animate_svg_fragment, progress_at
from graphics import visualize
import studio_core as core


def project(**changes):
    p={'titulo':'teste','video':{'width':720,'height':1280,'fps':24,'draw_fps':2},
       'cenas':[{'tipo':'svg','id':'a','duracao':1,'svg':'<rect id="r1" x="20" y="20" width="80" height="40"/>',
          'animacoes':[{'alvo':'r1','tipo':'translacao','de_x':-100,'ate_x':100,'inicio':0,'fim':1}]}]}
    p.update(changes)
    return normalize(p)


class VisualAnimationTests(unittest.TestCase):
    def test_schema_preserves_animations_and_old_projects(self):
        p=project()
        self.assertEqual(p['cenas'][0]['animacoes'][0]['tipo'],'translacao')
        self.assertFalse(p['trilha_continua'])
        p=project(trilha_continua=True)
        self.assertTrue(p['trilha_continua'])

    def test_svg_translation_and_rotation_and_fade(self):
        raw='<svg xmlns="http://www.w3.org/2000/svg"><rect id="box" x="10" y="20" width="100" height="40" fill="red" opacity=".8"/></svg>'
        animations=[
          {'alvo':'box','tipo':'translacao','inicio':0,'fim':1,'easing':'linear','de_x':0,'ate_x':100,'de_y':-40,'ate_y':40},
          {'alvo':'box','tipo':'rotacao','inicio':0,'fim':1,'easing':'linear','de':0,'ate':180},
          {'alvo':'box','tipo':'escala','inicio':0,'fim':1,'easing':'linear','de':1,'ate':2},
          {'alvo':'box','tipo':'fade','inicio':0,'fim':1,'easing':'linear','de':1,'ate':0},
        ]
        xml=animate_svg_fragment(raw,animations,.5)
        node=next(e for e in ET.fromstring(xml).iter() if e.get('id')=='box')
        self.assertIn('translate(50.0000 0.0000)',node.get('transform'))
        self.assertIn('rotate(90.0000 60.0000 40.0000)',node.get('transform'))
        self.assertIn('scale(1.50000)',node.get('transform'))
        self.assertAlmostEqual(float(node.get('opacity')),0.4,places=3)

    def test_preview_same_svg_at_same_progress(self):
        p=project()
        scene=p['cenas'][0]
        svg=visualize(scene,.5,0,1,Path('/tmp'),720,1280)
        self.assertIn('translate(0.0000 0.0000)',svg)
        self.assertIn('r1',svg)
        svg0=visualize(scene,0,0,1,Path('/tmp'),720,1280)
        self.assertIn('translate(-100.0000 0.0000)',svg0)

    def test_animation_rejects_invalid_target_and_extreme_values(self):
        p=project(cenas=[{'tipo':'svg','svg':'<rect id="r1"/>','animacoes':[
            {'tipo':'rotacao','alvo':'<script>','de':-1e8,'ate':5},
            {'tipo':'rotacao','alvo':'r1','de':-1e8,'ate':1e8}]}])
        animations=p['cenas'][0]['animacoes']
        self.assertEqual(len(animations),1)
        self.assertEqual(animations[0]['de'],-3600)
        self.assertEqual(animations[0]['ate'],3600)


class GlobalMusicTests(unittest.TestCase):
    def test_cache_does_not_invalidate_scene_audio_when_global_track_changes(self):
        pr=project(trilha_continua=True, trilha='A.wav')
        audio=pr['cenas'][0]['audio']
        self.assertEqual(core.audio_key(pr['cenas'][0],pr,1,None),core.audio_key(pr['cenas'][0],{**pr,'trilha':'B.wav'},1,None))

    @unittest.skipUnless(shutil.which('ffmpeg'),'ffmpeg necessário')
    def test_global_ducking_during_voice_interval(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            old_media=core.MEDIA
            core.MEDIA=root
            try:
                for filename,amplitude in [('dry.wav',0),('track.wav',4000)]:
                    with wave.open(str(root/filename),'wb') as f:
                        f.setnchannels(2);f.setsampwidth(2);f.setframerate(48000)
                        for i in range(48000):
                            value=int(amplitude*math.sin(2*math.pi*400*i/48000))
                            f.writeframesraw(struct.pack('<hh',value,value))
                core.apply_continuous_music(root/'dry.wav',root/'out.wav',
                    {'trilha_continua':True,'trilha':'track.wav','volume_musica':1},
                    duck_intervals=[(.3,.7)])
                with wave.open(str(root/'out.wav'),'rb') as f:
                    def peak(sec):
                        f.setpos(int(48000*sec));v=f.readframes(400)
                        return max(abs(x) for x in struct.unpack('<'+'h'*(len(v)//2),v))
                    peak_full=peak(.1);peak_duck=peak(.5);peak_after=peak(.8)
                self.assertLess(peak_duck,peak_full*.5)
                self.assertGreater(peak_after,peak_full*.9)
            finally:
                core.MEDIA=old_media

    @unittest.skipUnless(shutil.which('ffmpeg'),'ffmpeg necessário')
    def test_continuous_song_does_not_restart_at_scene_boundary(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            old_media=core.MEDIA
            core.MEDIA=root
            try:
                # Track switches frequency at exactly 1 second, 220 Hz -> 880 Hz.
                with wave.open(str(root/'track.wav'),'wb') as f:
                    f.setnchannels(2);f.setsampwidth(2);f.setframerate(48000)
                    for i in range(48000*3):
                        hz=220 if i<48000 else 880
                        n=int(5000*math.sin(2*math.pi*hz*(i/48000)))
                        f.writeframesraw(struct.pack('<hh',n,n))
                for num in (1,2):
                    with wave.open(str(root/f'{num}.wav'),'wb') as f:
                        f.setnchannels(2);f.setsampwidth(2);f.setframerate(48000)
                        f.writeframes(b'\0'*(48000*4))
                pr=project(trilha_continua=True,trilha='track.wav',volume_musica=.4)
                out=root/'out.wav'
                core.concat_audio([root/'1.wav',root/'2.wav'],out,pr)
                with wave.open(str(out),'rb') as f:
                    self.assertEqual(f.getnframes(),48000*2)
                    f.setpos(int(.2*48000));data=f.readframes(4800)
                    f.setpos(int(1.2*48000));data2=f.readframes(4800)
                def count_zeros(data):
                    samples=struct.unpack('<'+'h'*(len(data)//2),data)[::2]
                    return sum(samples[i-1]<0<=samples[i] for i in range(1,len(samples)))
                first,second=count_zeros(data),count_zeros(data2)
                self.assertGreater(second, first*2, (first,second))
            finally:
                core.MEDIA=old_media


if __name__=='__main__': unittest.main()
