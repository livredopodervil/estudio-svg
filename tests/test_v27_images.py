"""Testes de regressão V2.7: JSON, recorte e composição em diferentes formatos."""
import base64
import tempfile
import unittest
from io import BytesIO
from pathlib import Path
from PIL import Image

from schema import normalize
from graphics import visualize, image_uri


class ImageCompositionTests(unittest.TestCase):
    def test_portrait_image_defaults_and_crop_sanitization(self):
        project=normalize({'video':{'width':720,'height':1280}, 'cenas':[
            {'tipo':'cartoes','imagem':{'arquivo':'prancha.jpg','crop':[.6,.6,.8,.8]}}
        ]})
        im=project['cenas'][0]['imagem']
        self.assertEqual(im['modo'],'quadro')
        self.assertAlmostEqual(im['x'],.5)
        self.assertAlmostEqual(im['y'],.52)
        self.assertEqual(im['crop'],[.6,.6,.4,.4])

    def test_photo_stays_full_background_for_old_json(self):
        project=normalize({'cenas':[{'tipo':'foto','imagem':{'arquivo':'prancha.jpg'}}]})
        self.assertEqual(project['cenas'][0]['imagem']['modo'],'fundo')

    def test_crop_extracts_only_selected_quadrant(self):
        with tempfile.TemporaryDirectory() as folder:
            f=Path(folder)/'atlas.png'
            im=Image.new('RGB',(200,100),'#ed2020')
            im.paste(Image.new('RGB',(100,100),'#20d020'),(100,0))
            im.save(f)
            uri=image_uri(str(f),f.stat().st_mtime_ns,'stretch',.5,.5,'#000000',(.5,0,.5,1),90,90)
            data=base64.b64decode(uri.partition('base64,')[2])
            out=Image.open(BytesIO(data));r,g,b=out.getpixel((45,45))
            self.assertGreater(g,150)
            self.assertLess(r,100)
            self.assertLess(b,100)

    def test_scene_keeps_background_and_portrait_overlay(self):
        with tempfile.TemporaryDirectory() as folder:
            f=Path(folder)/'prancha.jpg'
            Image.new('RGB',(120,80),'#ff7a23').save(f)
            project=normalize({'video':{'width':720,'height':1280},'cenas':[
                {'tipo':'cartoes','titulo':'Notícia','itens':['Economia','Saúde'],
                 'imagem':{'arquivo':'prancha.jpg','modo':'quadro','crop':[.1,.1,.8,.8],'w':.6}}
            ]})
            svg=visualize(project['cenas'][0],.5,0,1,folder,720,1280)
            self.assertIn('viewBox="0 0 1280 2276"',svg)
            self.assertIn('clipPath id="image-frame"',svg)
            self.assertIn('data:image/jpeg;base64',svg)
            self.assertIn('Economia',svg)
            self.assertIn('Notícia',svg)

    def test_image_info_survives_json_roundtrip(self):
        img={'arquivo':'prancha.jpg','modo':'quadro','crop':[.2,.15,.3,.4],
             'x':.4,'y':.55,'w':.7,'h':.3,'frame':False}
        project=normalize({'video':{'width':720,'height':1280},'cenas':[{'tipo':'svg','imagem':img}]})
        again=normalize(project)
        self.assertEqual(again['cenas'][0]['imagem'],project['cenas'][0]['imagem'])

if __name__=='__main__':unittest.main()
