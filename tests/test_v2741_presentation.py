"""Regressões V2.7.4.1: vínculo de clipes e apresentação em tela limpa."""
import unittest
from pathlib import Path
from schema import normalize

ROOT = Path(__file__).resolve().parents[1]


class PresentationOverlayContractTests(unittest.TestCase):
    def test_presentation_has_dedicated_video_frame(self):
        html = (ROOT / 'web/captura.html').read_text(encoding='utf-8')
        js = (ROOT / 'web/captura.js').read_text(encoding='utf-8')
        self.assertIn('id="visualFrame"', html)
        self.assertIn('id="stageVideo"', html)
        self.assertIn("function syncVideo(i, sceneTime)", js)
        self.assertIn("/api/media/clip?file=", js)
        self.assertIn("const {i, progress, sceneTime} = sceneAt(t);", js)
        self.assertIn('syncVideo(i, sceneTime);', js)

    def test_presentation_hides_controls_until_explicit_touch(self):
        html = (ROOT / 'web/captura.html').read_text(encoding='utf-8')
        js = (ROOT / 'web/captura.js').read_text(encoding='utf-8')
        self.assertIn('body.presenting #bar{display:none!important}', html)
        self.assertIn('body.presenting #hint{display:none!important}', html)
        self.assertIn("document.body.classList.add('presenting')", js)
        self.assertIn("document.body.classList.remove('presenting', 'controls-visible')", js)

    def test_removing_video_link_does_not_remove_voice_file(self):
        project = normalize({'cenas': [{'tipo': 'svg',
            'video_clipe': {'arquivo': 'camara.mp4', 'x': .3, 'y': .5},
            'audio': {'voice_file': 'camara.mp4', 'voice_enabled': True}}]})
        scene = project['cenas'][0]
        scene['video_clipe']['arquivo'] = ''
        restored = normalize(project)['cenas'][0]
        self.assertEqual(restored['video_clipe']['arquivo'], '')
        self.assertEqual(restored['audio']['voice_file'], 'camara.mp4')
        self.assertTrue(restored['audio']['voice_enabled'])

    def test_editor_exposes_clip_removal(self):
        js = (ROOT / 'web/app.js').read_text(encoding='utf-8')
        self.assertIn('id="removeClip"', js)
        self.assertIn("if(t.id==='removeClip')", js)
        self.assertIn("clip.arquivo='';", js)


if __name__ == '__main__':
    unittest.main()
