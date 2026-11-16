"""V3.6: route recovery, project isolation and persisted layer composition."""
import json, tempfile, threading, unittest, urllib.request, urllib.error
from pathlib import Path
from http.server import ThreadingHTTPServer
from unittest.mock import patch
import xml.etree.ElementTree as ET
from PIL import Image
import app
from schema import normalize
from graphics import visualize

class Layers(unittest.TestCase):
    def test_legacy_normalization_and_layer_roundtrip(self):
        pr=normalize({'cenas':[{'tipo':'foto','imagem':{'arquivo':'foto.jpg'}}]})
        self.assertNotIn('camadas',pr['cenas'][0])
        pr['cenas'][0]['camadas']={'imagem':{'dx':24},'titulo':{'z':85,'oculta':True},'fake':{}}
        again=normalize(pr);c=again['cenas'][0]['camadas']
        self.assertEqual(c['imagem']['z'],10)
        self.assertEqual(c['imagem']['dx'],24)
        self.assertEqual(c['titulo']['oculta'],True)
        self.assertNotIn('fake',c)
        self.assertEqual(normalize(again),again)
    def test_reorder_move_hide_shared_renderer(self):
        with tempfile.TemporaryDirectory() as d:
            Image.new('RGB',(40,40),'blue').save(Path(d)/'foto.jpg')
            pr=normalize({'cenas':[{'tipo':'cartoes','titulo':'Título','subtitulo':'Sub','itens':['Dados'],'imagem':{'arquivo':'foto.jpg','modo':'quadro'},'camadas':{'imagem':{'z':100,'dx':42,'dy':-11},'titulo':{'oculta':True}}}]})
            c=pr['cenas'][0]
            for browser in (False,True):
                for wh in [(1280,720),(720,1280)]:
                    r=ET.fromstring(visualize(c,1,0,1,d,*wh,browser=browser))
                    order=[e.get('data-studio-layer') for e in r if e.get('data-studio-layer')]
                    self.assertEqual(order[-1],'imagem')
                    self.assertNotIn('titulo',order)
                    self.assertEqual(r[-1].get('transform'),'translate(42.0 -11.0)')
                    if browser:self.assertTrue(any(e.get('id')=='__imagem__' for e in r.iter()))
            self.assertEqual(c['imagem']['arquivo'],'foto.jpg')
    def test_native_browser_base_has_markers(self):
        c=normalize({'cenas':[{'tipo':'svg','titulo':'A','svg':'<circle id="obj" cx="10" cy="10" r="3"/>','animacoes':[{'alvo':'obj','tipo':'translacao','ate_x':100}]}]})['cenas'][0]
        raw=visualize(c,1,browser=True);r=ET.fromstring(raw)
        obj=next(e for e in r.iter() if e.get('id')=='obj')
        self.assertIsNone(obj.get('transform'))
        self.assertIn('id="__titulo__"',raw)

class Routes(unittest.TestCase):
    def test_real_handler_project_binding_and_recorder(self):
        project=normalize({'titulo':'PROJETO SELECIONADO','cenas':[{'tipo':'svg','titulo':'CENA REAL','audio':{'voice_enabled':False}}]})
        server=ThreadingHTTPServer(('127.0.0.1',0),app.Handler)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        base=f'http://127.0.0.1:{server.server_port}'
        def get(path):
            try:
                with urllib.request.urlopen(base+path,timeout=5) as res:return res.status,res.read()
            except urllib.error.HTTPError as e:return e.code,e.read()
        try:
            with patch.object(app,'read_project',return_value=project) as read:
                for route in ['/media-recorder-v35.js','/layers-v36.js','/player-v3/?project=selecionado','/player-v3/runtime.js','/player-v3/v34/voice_locale.js','/captura?name=selecionado']:
                    self.assertEqual(get(route)[0],200,route)
                code,raw=get('/api/player-v3?name=selecionado');self.assertEqual(code,200)
                payload=json.loads(raw);read.assert_called_with('selecionado')
                self.assertEqual(payload['project']['titulo'],'PROJETO SELECIONADO')
                self.assertEqual(get('/api/player-v3?name=selecionado&scene=1&revision=invalida')[0],400)
                code,raw=get('/api/player-v3?name=selecionado&scene=1&revision='+payload['revision']);self.assertEqual(code,200);ET.fromstring(raw)
                self.assertIn(b'CENA REAL',raw)
        finally:server.shutdown();server.server_close();thread.join(timeout=5)
if __name__=='__main__':unittest.main()
