import math, shutil, struct, tempfile, unittest, wave
from pathlib import Path
from unittest.mock import patch
from schema import normalize
import studio_core as core

@unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'),'ffmpeg/ffprobe')
class ClipAudioTests(unittest.TestCase):
    def test_real_mixed_clip_audio_interval_and_cache(self):
        with tempfile.TemporaryDirectory() as tmp:
            r=Path(tmp);(r/'audio').mkdir()
            # Clip with a tone, and a silent video, to test optional audio streams.
            core.run(['ffmpeg','-v','error','-y','-f','lavfi','-i','color=c=black:s=32x32:r=10:d=2','-f','lavfi','-i','sine=frequency=880:sample_rate=48000:duration=2','-c:v','mpeg4','-c:a','aac','-shortest',r/'clip.mp4'])
            core.run(['ffmpeg','-v','error','-y','-f','lavfi','-i','color=c=black:s=32x32:r=10:d=2','-c:v','mpeg4',r/'silent.mp4'])
            with wave.open(str(r/'voice.wav'),'wb') as f:
                f.setparams((1,2,48000,0,'NONE',''));f.writeframes(b''.join(struct.pack('<h',int(3000*math.sin(2*math.pi*440*i/48000))) for i in range(9600)))
            p=normalize({'cenas':[{'duracao':4,'audio':{'voice_enabled':True,'voice_file':'voice.wav','voice_delay':0},'objetos_midia':[{'id':'one','kind':'video','file':'clip.mp4','start':1,'end':2.5,'offset':.3,'loop':False},{'id':'two','kind':'video','file':'silent.mp4','start':0,'end':4}]}]})
            c=p['cenas'][0]
            with patch.object(core,'MEDIA',r),patch.object(core,'CACHE',r):
                path=core.prepare_preview_audio(p,0);out=core.browser_audio_mix(p,r/'out.wav')
                self.assertEqual(path.read_bytes(),out.read_bytes())
                with wave.open(str(path),'rb') as f:
                    self.assertEqual(f.getnframes(),192000)
                    def peak(t):
                        f.setpos(int(t*48000));return max(map(abs,struct.unpack('<9600h',f.readframes(4800))))
                    self.assertGreater(peak(.05),100);self.assertLess(peak(.5),10);self.assertGreater(peak(1.4),100);self.assertLess(peak(3),10)
                c['objetos_midia'][0]['rotation']=45
                c['objetos_midia'][0]['shear']=.4
                c['objetos_midia'][0]['pivot_x']=.2
                self.assertEqual(path,core.prepare_preview_audio(p,0))
                c['objetos_midia'][0]['audio_enabled']=False
                self.assertNotEqual(path,core.prepare_preview_audio(p,0))
    def test_camera_not_doubled_and_legacy_opt_in(self):
        c=normalize({'cenas':[{'duracao':3,'video_clipe':{'arquivo':'clip.mp4','audio_enabled':True},'audio':{'voice_file':'clip.mp4','voice_enabled':True}}]})['cenas'][0]
        self.assertEqual(core.scene_clip_audio(c,3),[])
        c['audio']['voice_enabled']=False
        self.assertEqual(len(core.scene_clip_audio(c,3)),1)
        c['video_clipe']['audio_enabled']=False
        self.assertEqual(core.scene_clip_audio(c,3),[])
