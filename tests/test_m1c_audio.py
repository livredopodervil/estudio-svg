import unittest,shutil,math,struct,wave,tempfile,subprocess
from pathlib import Path
from unittest.mock import patch
from schema import normalize,media_objects_dict
import studio_core as core
class M1cAudioSchema(unittest.TestCase):
 def test_clip_fades_persist_and_are_bounded(self):
  p=normalize({'cenas':[{'video_clipe':{'arquivo':'clip.mp4','audio_enabled':True,'audio_fade_in':.3,'audio_fade_out':.4},'audio':{'scene_fade_in':.25,'scene_fade_out':.35},'objetos_midia':[{'id':'vid','kind':'video','file':'clip.mp4','start':0,'end':3,'audio_fade_in':1,'audio_fade_out':.8}]}]})
  c=p['cenas'][0];self.assertAlmostEqual(c['audio']['scene_fade_in'],.25);self.assertAlmostEqual(c['video_clipe']['audio_fade_out'],.4);self.assertAlmostEqual(c['objetos_midia'][0]['audio_fade_in'],1)
  clips=core.scene_clip_audio(c,3);self.assertEqual(len(clips),2);self.assertEqual(clips[0][-2:],(.3,.4));self.assertEqual(clips[1][-2:],(1,.8))
 def test_gil_title_spec_and_crop_source_preserved(self):
  items=media_objects_dict([{'id':'crop','kind':'image','file':'crop.png','source_file':'original.jpg','source_crop':[.1,.2,.7,.6],'end':8},{'id':'title','kind':'image','file':'title.png','end':8}]);self.assertEqual(items[0]['source_file'],'original.jpg');self.assertEqual(items[0]['source_crop'],[.1,.2,.7,.6]);self.assertEqual(items[1]['source_file'],'title.png')
 @unittest.skipUnless(shutil.which('ffmpeg'),'FFmpeg indisponível')
 def test_scene_fades_affect_pcm_edges_not_length(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);(root/'audio').mkdir()
   path=root/'tone.wav'
   with wave.open(str(path),'wb') as f:
    f.setparams((2,2,48000,0,'NONE',''))
    samples=bytearray()
    for i in range(48000):
     value=int(10000*math.sin(2*math.pi*440*i/48000));samples+=struct.pack('<hh',value,value)
    f.writeframes(samples)
   c=normalize({'cenas':[{'duracao':1,'audio':{'tracks':[{'file':'tone.wav','volume':1}], 'scene_fade_in':.25,'scene_fade_out':.25}}]})['cenas'][0]
   with patch.object(core,'MEDIA',root),patch.object(core,'CACHE',root):
    result,_=core.make_scene_audio(c,{'trilha_continua':True,'trilha':'','volume_musica':0,'volume_voz':1},1,None)
    with wave.open(str(result),'rb') as f:
     self.assertEqual(f.getnframes(),48000)
     def energy(t):
      f.setpos(int(t*48000));s=f.readframes(800);return sum(abs(v[0]) for v in struct.iter_unpack('<hh',s))
     self.assertLess(energy(0),energy(.45)*.4)
     self.assertLess(energy(.985),energy(.45)*.4)

class M1cShortClipFade(unittest.TestCase):
 @unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'),'FFmpeg ou FFprobe indisponível')
 def test_fade_finishes_at_real_file_end(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);(root/'audio').mkdir()
   file=root/'audio'/'short.mp4'
   subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-nostdin','-f','lavfi','-i','sine=frequency=440:sample_rate=48000:duration=0.8','-c:a','aac','-y',str(file)],check=True)
   c=normalize({'cenas':[{'duracao':2,'video_clipe':{'arquivo':'short.mp4','audio_enabled':True,'audio_fade_in':0,'audio_fade_out':.24,'repetir':False}}]})['cenas'][0]
   with patch.object(core,'MEDIA',root/'audio'),patch.object(core,'CACHE',root):
    path,_=core.make_scene_audio(c,{'trilha_continua':True,'trilha':'','volume_musica':0,'volume_voz':1},2,None)
    with wave.open(str(path),'rb') as sound:
     self.assertEqual(sound.getnframes(),96000)
     def energy(t):
      sound.setpos(int(t*48000));return sum(abs(v[0]) for v in struct.iter_unpack('<hh',sound.readframes(500)))
     self.assertGreater(energy(.38),10000)
     self.assertLess(energy(.77),energy(.38)*.3)
     self.assertEqual(energy(1.0),0)
