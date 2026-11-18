import unittest
from pathlib import Path
from schema import normalize
ROOT=Path(__file__).resolve().parents[1]

class M1bContracts(unittest.TestCase):
    def test_title_raster_is_existing_image_object(self):
        from schema import media_objects_dict
        item={'id':'titulo01','kind':'image','label':'TÍTULO [editorial] Ensaio', 'file':'titulo.png',
              'x':.5,'y':.5,'w':1,'h':1,'start':0,'end':8,'motion':'', 'motion_programs':[]}
        result=media_objects_dict([item])[0]
        self.assertEqual(result['kind'],'image')
        self.assertEqual(result['file'],'titulo.png')
        self.assertEqual(result['label'],item['label'])
    def test_server_serves_title_and_svg_editor_modules(self):
        src=(ROOT/'app.py').read_text()
        self.assertIn("'/title-gallery.mjs'",src)
        self.assertIn("'/svg-direct-edit.mjs'",src)
    def test_no_hardcoded_editor_gil_port(self):
        html=(ROOT/'web/index.html').read_text()
        self.assertNotIn('http://127.0.0.1:8791/',html)
        app=(ROOT/'web/app.js').read_text()
        self.assertNotIn("location.href='http://127.0.0.1:8791/'",app)
        self.assertIn('objectEditor.editGil()',app)
    def test_legacy_image_promotion_keeps_media_reference(self):
        src=(ROOT/'web/scene-object-editor.mjs').read_text()
        self.assertIn("source_file:original",src)
        self.assertIn("cropImageURL",src)
        self.assertIn("c.imagem={...im,arquivo:''}",src)
        self.assertIn('legacyPromoteImage',src)
