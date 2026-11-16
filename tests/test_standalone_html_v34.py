"""Regressão da exportação HTML autônoma V3.4."""
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch
import base64
import json
import re
import subprocess
import shutil

import standalone_html as sh

class TestStandaloneV34(TestCase):
    def test_player_autossuficiente(self):
        page = sh.HTML_TEMPLATE
        self.assertIn('%%VOICE_RUNTIME%%', page)
        self.assertIn('id="voiceMode"', page)
        self.assertIn("select.value=data.audio?'mixed':'browser'", page)
        self.assertIn("mode==='browser'", page)
        self.assertIn('say.busy', page)
        self.assertIn('t>=boundary', page)
        self.assertIn('video.src=data.clips[clipName]', page)
        self.assertIn("mode==='mixed'&&data.audio", page)
        self.assertIn('speechSynthesis', page)

    def test_payload_e_js_integrados(self):
        with TemporaryDirectory() as folder:
            root=Path(folder)
            pr={'titulo':'Teste', 'video':{'width':640,'height':360,'draw_fps':2},
                'cenas':[{'id':'um','titulo':'Primeira','duracao':1,
                  'fala':'Texto a ser narrado','audio':{'voice_enabled':True,'voice_text':'Bom dia','muted':False},
                  'imagem':{'arquivo':''},'video_clipe':{}}]}
            with patch.object(sh,'normalize',side_effect=lambda p:p), \
                 patch.object(sh,'name',side_effect=lambda p:p), \
                 patch.object(sh,'voice_source',return_value=None), \
                 patch.object(sh,'scene_length',return_value=1), \
                 patch.object(sh,'visualize',return_value='<svg xmlns="http://www.w3.org/2000/svg"></svg>'):
                result=sh.export_html('teste',pr,root,root,with_audio=False)
            html=(root/result['html']).read_text(encoding='utf-8')
            self.assertNotIn('%%VOICE_RUNTIME%%',html)
            self.assertIn('global.StudioV34=',html)
            self.assertIn('id="voiceMode"',html)
            encoded=re.search(r"const encoded='([A-Za-z0-9+/=]+)'",html).group(1)
            payload=json.loads(base64.b64decode(encoded))
            self.assertEqual(payload['scenes'][0]['speech'],'Bom dia')
            self.assertTrue(payload['scenes'][0]['voiceEnabled'])
            self.assertEqual(payload['locale'],'pt-BR')
            self.assertFalse(payload['audio'])
            self.assertEqual(len(payload['scenes'][0]['frames']),2)
            scripts=re.findall(r'<script>(.*?)</script>',html,flags=re.DOTALL)
            self.assertEqual(len(scripts),2)
            if shutil.which('node'):
                for i,js in enumerate(scripts):
                    f=root/f'script-{i}.js';f.write_text(js)
                    subprocess.run(['node','--check',str(f)],check=True)
