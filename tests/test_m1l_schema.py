"""M1L: testes de persistência das legendas no normalizador existente."""
import unittest
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from schema import normalize


class SubtitleSchemaTests(unittest.TestCase):
    def base(self, captions):
        return {'titulo': 'Teste M1L', 'video': {'width': 960, 'height': 540},
                'cenas': [{'id': 'a', 'tipo': 'svg', 'duracao': 8,
                           'audio': {'voice_text': 'Olá, mundo'}, 'legendas': captions}]}

    def test_defaults_do_not_activate_existing_scenes(self):
        scene = normalize(self.base({}))['cenas'][0]
        self.assertFalse(scene['legendas']['enabled'])
        self.assertEqual(scene['legendas']['mode'], 'karaoke')
        self.assertEqual(scene['legendas']['cues'], [])

    def test_valid_styles_and_timings_roundtrip(self):
        caps = {'enabled': True, 'mode': 'word', 'effect': 'pop',
                'position': 'top', 'font_scale': 1.2,
                'cues': [{'start': 0.5, 'end': 2.2, 'text': 'Olá mundo'}]}
        pr = normalize(self.base(caps))
        once = pr['cenas'][0]['legendas']
        self.assertEqual(once, normalize(pr)['cenas'][0]['legendas'])
        self.assertTrue(once['enabled'])
        self.assertEqual(once['cues'], caps['cues'])

    def test_invalid_cues_filtered_and_colors_sanitized(self):
        caps = {'enabled': True, 'text_color': '<script>',
                'cues': [{'start': 3, 'end': 2, 'text': 'invalid'},
                         {'start': 0, 'end': 1, 'text': 'válida'}]}
        normalized = normalize(self.base(caps))['cenas'][0]['legendas']
        self.assertEqual(normalized['text_color'], '#ffffff')
        self.assertEqual(normalized['cues'], [{'start': 0.0, 'end': 1.0, 'text': 'válida'}])


if __name__ == '__main__':
    unittest.main()
