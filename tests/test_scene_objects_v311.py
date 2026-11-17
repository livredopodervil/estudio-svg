import hashlib, unittest
from pathlib import Path
from schema import normalize
from project_bundle import referenced_media
from studio_core import project_render, StudioError
from studio_workspace import inventory

class SceneObjects(unittest.TestCase):
    def project(self):
        source=(Path(__file__).resolve().parents[1]/'examples/components/native-demo.gil').read_text()
        h=hashlib.sha256(source.encode()).hexdigest()
        g={'format':'gil-timeline-0.1','origin':'gil','source':source,'source_sha256':h,'origin_sha256':h,'duration':8}
        return normalize({'cenas':[{'duracao':12,'video_clipe':{'arquivo':'old.mp4'},'imagem':{'arquivo':'old.jpg'},'audio':{'voice_enabled':True,'voice_file':'v.wav','tracks':[{'file':'music.wav'}]},'objetos_midia':[{'id':'a','kind':'image','file':'new.jpg','start':1,'end':8},{'id':'b','kind':'video','file':'new.mp4','start':3,'end':12},{'id':'c','kind':'gil','gil':g,'start':0,'end':10}]}]})
    def test_round_trip_audio_and_legacy(self):
        p=self.project();s=p['cenas'][0]
        self.assertEqual(normalize(p),p);self.assertEqual(len(p['cenas']),1);self.assertEqual(s['duracao'],12)
        self.assertEqual(s['audio']['voice_file'],'v.wav');self.assertEqual(s['audio']['tracks'][0]['file'],'music.wav');self.assertEqual(s['video_clipe']['arquivo'],'old.mp4');self.assertEqual(s['imagem']['arquivo'],'old.jpg')
        self.assertEqual([o['id'] for o in s['objetos_midia']],['a','b','c'])
    def test_asset_inventory(self):
        p=self.project();self.assertEqual(referenced_media(p),['music.wav','new.jpg','new.mp4','old.jpg','old.mp4','v.wav'])
        self.assertTrue(any('objeto' in ' '.join(x['uses']) for x in inventory(p,Path('.')) if x['file']=='new.mp4'))
    def test_invalid_overlays(self):
        for key,value in [('file','../private.jpg'),('end',0),('kind','remote')]:
            p=self.project();p['cenas'][0]['objetos_midia'][0][key]=value
            with self.assertRaises(ValueError):normalize(p)
        p=self.project();p['cenas'][0]['objetos_midia'][1]['id']='a'
        with self.assertRaises(ValueError):normalize(p)
        p=self.project();p['cenas'][0]['objetos_midia'][2]['gil']['source']+='?'
        with self.assertRaises(ValueError):normalize(p)
    def test_protect_legacy(self):
        with self.assertRaises(StudioError):project_render('test',self.project())
