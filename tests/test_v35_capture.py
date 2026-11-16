# Regressões estáticas da integração de captura V3.5; não testa hardware real.
import unittest
import subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
class CaptureV35(unittest.TestCase):
    def test_scripts_wired(self):
        html=(ROOT/'web/index.html').read_text()
        self.assertIn('id="makeSceneVoice"',html)
        self.assertIn('id="autoExtendVoice"',html)
        self.assertIn('/media-recorder-v35.js?v=3.5',html)
        self.assertLess(html.index('/media-recorder-v35.js?v=3.5'),html.index('/app.js?v='))
        js=(ROOT/'web/app.js').read_text()
        self.assertIn("begin('audio-cena')",js)
        self.assertIn("project.encaixe_voz='estender'",js)
        self.assertIn('script:String(project.cenas[index]?.audio?.voice_text',js)
    def test_backend(self):
        src=(ROOT/'app.py').read_text()
        self.assertIn("elif mode=='audio-cena':",src)
        self.assertIn("'cenas':[pr['cenas'][scene-1]]",src)
        self.assertIn("res=export_scene_voice(actual_name,pr,scene",src)
        self.assertIn('export_zip=False)',src)
        core=(ROOT/'studio_core.py').read_text()
        self.assertIn('if not export_zip:return None',core)
        compile(core,'studio_core.py','exec')
        compile(src,'app.py','exec')
    def test_recorder(self):
        js=(ROOT/'web/media-recorder-v35.js').read_text()
        for token in ('mergeWav(', 'audioBitsPerSecond', 'echoCancellation:processed',
                      'r35script', 'r35prepare', 'studioRecorderV35', 'onFile'):
            if token=='onFile':
                self.assertIn('onFile,options=',js)
            else:self.assertIn(token,js)
        subprocess.run(['node','--check',str(ROOT/'web/media-recorder-v35.js')],check=True)

if __name__=='__main__':unittest.main()
