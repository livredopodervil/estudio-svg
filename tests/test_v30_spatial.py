"""V3 alpha: regressões do contrato espacial e da renderização por tempo absoluto."""
import io
import json
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest.mock import patch

from schema import normalize
from graphics import visualize
from spatial_scene import default_spatial, normalize_spatial, pose, render_spatial

ROOT = Path(__file__).resolve().parents[1]


class SpatialContractTests(unittest.TestCase):
    def test_old_project_is_unchanged_by_spatial_fields(self):
        p = normalize({'cenas': [{'tipo': 'svg', 'svg': '<circle r="5"/>'}]})
        self.assertEqual(p['cenas'][0]['tipo'], 'svg')
        self.assertNotIn('espacial', p['cenas'][0])
        self.assertEqual(len(p['cenas']), 1)

    def test_switching_to_spatial_provides_default_scene(self):
        p = normalize({'cenas': [{'tipo': 'espacial'}]})
        self.assertEqual([o['tipo'] for o in p['cenas'][0]['espacial']['objetos']], ['esfera', 'cubo'])

    def test_reject_duplicate_id_and_unknown_property(self):
        with self.assertRaisesRegex(ValueError, 'repetido'):
            normalize_spatial({'objetos': [{'id':'a'}, {'id':'a'}]})
        with self.assertRaisesRegex(ValueError, 'desconhecidos'):
            normalize_spatial({'objetos':[{'id':'a'}], 'animacoes':[{'alvo':'a','propriedade':'__proto__'}]})

    def test_reject_oversized_scene(self):
        with self.assertRaisesRegex(ValueError, '32'):
            normalize_spatial({'objetos':[{'id':f'o{i}'} for i in range(33)]})

    def test_pose_is_deterministic_and_interpolated(self):
        s = default_spatial(); obj=s['objetos'][1]
        before=pose(obj,s['animacoes'],0)
        middle=pose(obj,s['animacoes'],.5)
        after=pose(obj,s['animacoes'],1)
        self.assertEqual(before[1][1],0)
        self.assertAlmostEqual(middle[1][1],180)
        self.assertAlmostEqual(after[1][1],360)
        self.assertEqual(middle,pose(obj,s['animacoes'],.5))
        self.assertEqual(obj['rotacao'][1],0, 'Render must not mutate scene')

    def test_spatial_preview_svg_is_well_formed_in_portrait(self):
        example=json.loads((ROOT/'examples/espacial_v3_experimental.json').read_text())
        p=normalize(example);c=p['cenas'][0]
        self.assertEqual((p['video']['width'],p['video']['height']),(720,1280))
        a=visualize(c,0,0,1,None,720,1280)
        b=visualize(c,.5,0,1,None,720,1280)
        self.assertNotEqual(a,b)
        self.assertIn('id="spatial-world"',a)
        self.assertIn('viewBox="0 0 1280 2276"',a)
        ET.fromstring(a);ET.fromstring(b)
        self.assertEqual(b,visualize(c,.5,0,1,None,720,1280))

    def test_converts_spatial_svg_to_png_using_existing_pipeline(self):
        from studio_core import convert_svg
        s=normalize({'cenas':[{'tipo':'espacial'}]})['cenas'][0]
        source=visualize(s,.25,0,1,None,320,568)
        img=convert_svg(source,320,568)
        self.assertTrue(img.startswith(b'\x89PNG\r\n\x1a\n'))
        from PIL import Image
        with Image.open(io.BytesIO(img)) as im:
            self.assertEqual(im.size,(320,568))

    def test_editor_route_and_composition_controls(self):
        html=(ROOT/'web/espacial.html').read_text()
        js=(ROOT/'web/espacial.js').read_text()
        app=(ROOT/'web/app.js').read_text()
        server=(ROOT/'app.py').read_text()
        for marker in ('id="viewport"','id="seek"','id="commands"','id="save"'):
            self.assertIn(marker,html)
        self.assertIn('/api/project/validate',js)
        self.assertNotIn('eval(',js)
        self.assertIn('id="addSpatialScene"',(ROOT/'web/index.html').read_text())
        self.assertIn("'/espacial':'espacial.html'",server)
        self.assertIn("+ 3D",(ROOT/'web/index.html').read_text())
        self.assertIn("$('addSpatialScene').onclick",app)


if __name__=='__main__': unittest.main()
