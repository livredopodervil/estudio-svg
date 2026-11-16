"""Contratos básicos do Player Web V3 (mídia e publicação)."""
import sys
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from player_v3_compat import patch_player,patch_html

class PlayerMediaContract(unittest.TestCase):
    def test_audio_and_clip_hooks(self):
        js=(ROOT/'web_player/v3/player.js').read_text('utf-8')
        # V3.4: arquivos de cena passam pelo controlador de voz.
        self.assertIn(
            'const nativeMap=window.__voiceSceneFiles||{}', js
        )
        self.assertIn('nativeMap[scene]', js)
        self.assertIn('window.StudioV34.Narrator', js)
        self.assertIn('voiceRuntime.speak({', js)
        self.assertIn('voiceRuntime.stop()', js)
        self.assertIn(
            "voiceRuntime.setMode($('voiceSource').value)", js
        )
        self.assertIn('window.StudioMedia?.scene',js)
        self.assertIn('window.StudioMedia?.pause()',js)
        self.assertIn('window.StudioMedia?.seek(',js)
        self.assertEqual(js.count('ESTUDIO_V3_MEDIA_PATCH_2026_11'),1)

    def test_html_includes_media_before_player(self):
        page=(ROOT/'web_player/v3/index.html').read_text('utf-8')
        self.assertLess(page.index('media_layer.js?v=4'),page.index('player.js?v=4'))
        self.assertIn('window.__voiceSceneFiles={}',page)
        self.assertIn('id="voiceSource"', page)
        self.assertIn('./v34/voice_locale.js', page)
        self.assertLess(
            page.index('./v34/voice_locale.js'),
            page.index('player.js?v=4')
        )

    def test_media_runtime_is_independent(self):
        runtime=(ROOT/'web_player/v3/media_layer.js').read_text('utf-8')
        self.assertIn("document.createElement('video')",runtime)
        self.assertIn('video.playsInline=true',runtime)
        self.assertIn('video.muted=true',runtime)
        self.assertNotIn('fetch(',runtime)

    def test_generated_players_use_compatibility_patch(self):
        gen=(ROOT/'tools/estudio_svg_v3_integrador.py').read_text('utf-8')
        self.assertIn("new_js=(canonical/'player.js').read_text",gen)
        self.assertIn("new_html=(canonical/'index.html').read_text",gen)
        self.assertIn("canonical/'v34'/'voice_locale.js'",gen)
        self.assertIn("'media_layer.js'",gen)

if __name__=='__main__':unittest.main()
