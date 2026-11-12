import unittest, tempfile, json
from pathlib import Path
from svg_graphic import clean_svg
from schema import normalize

class CoreV26Tests(unittest.TestCase):
    def test_layer_lock_and_safe_save(self):
        with tempfile.TemporaryDirectory() as d:
            svg='''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 720"><g id="layer_A" class="layer" data-name="Texto" data-locked="true"><title>Texto</title><text x="90" y="90" fill="#123456">Legenda</text></g></svg>'''
            output=clean_svg(svg,d,storage=True)
            self.assertIn('data-locked="true"',output)
            self.assertIn('data-name="Texto"',output)
            self.assertIn('Legenda',output)
    def test_script_removed(self):
        with tempfile.TemporaryDirectory() as d:
            xml='<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script><circle r="15" onload="alert(2)"/></svg>'
            output=clean_svg(xml,d,storage=True)
            self.assertNotIn('<script',output)
            self.assertNotIn('onload',output)
            self.assertIn('circle',output)
    def test_legacy_json_compatibility(self):
        from pathlib import Path
        original=json.loads((Path(__file__).resolve().parent/'fixtures'/'legacy_v21.json').read_text())
        project=normalize(original)
        self.assertTrue(len(project['cenas'])>=1)
        self.assertIn('audio',project['cenas'][0])

if __name__=='__main__':unittest.main()
