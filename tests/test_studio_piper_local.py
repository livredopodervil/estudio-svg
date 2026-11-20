import os
import sys
import tempfile
import unittest
from pathlib import Path
from studio_piper_local import synthesize, PiperError

FAKE=r'''import sys,wave
from pathlib import Path
args=sys.argv
name=next(args[i+1] for i,x in enumerate(args) if x=='--output_file')
rate=22050 if 'faber' in args[args.index('--model')+1] else 16000
with wave.open(name,'wb') as out:
 out.setnchannels(1);out.setsampwidth(2);out.setframerate(rate);out.writeframes(b'\x00\x00'*rate)
'''

class PiperNative(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
  root=Path(self.tmp.name);self.models=root/'models';self.media=root/'media';self.cache=root/'cache'
  for x in (self.models,self.media,self.cache):x.mkdir()
  for n in ('pt_BR-faber-medium.onnx','pt_BR-edresson-low.onnx'):
   (self.models/n).write_bytes(b'fake model')
   # Fixture válida: a descoberta dinâmica exige sample_rate no JSON.
   rate = 22050 if 'faber' in n else 16000
   (self.models/(n+'.json')).write_text(
       '{"audio":{"sample_rate":%d}}' % rate, encoding='utf-8')
  self.bin=root/'fake_piper.py';self.bin.write_text('#!'+sys.executable+'\n'+FAKE);self.bin.chmod(0o755)
 def run_voice(self,**kw):
  return synthesize(kw.pop('text','Texto de teste.'),kw.pop('voice','faber'),kw.pop('length_scale',.94),
                    kw.pop('sentence_silence',.35),self.media,self.cache,model_root=self.models,piper_binary=self.bin,**kw)
 def test_faber_create_and_cache(self):
  a=self.run_voice();self.assertFalse(a['cached']);self.assertEqual(a['seconds'],1)
  b=self.run_voice();self.assertTrue(b['cached']);self.assertEqual(a['filename'],b['filename'])
 def test_edresson(self):
  a=self.run_voice(voice='edresson');self.assertEqual(a['seconds'],1)
 def test_invalid_args_do_not_create_audio(self):
  for values in ({'voice':'../bad'}, {'length_scale':0}, {'text':''},{'sentence_silence':float('nan')}):
   with self.assertRaises(PiperError):self.run_voice(**values)
  self.assertFalse(list(self.media.iterdir()))
 def test_change_voice_changes_key(self):
  self.assertNotEqual(self.run_voice()['filename'],self.run_voice(voice='edresson')['filename'])

if __name__=='__main__':unittest.main()
