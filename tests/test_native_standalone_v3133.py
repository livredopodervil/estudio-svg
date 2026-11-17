"""Regressions for a portable GIL timeline page and native presentation."""
import base64
import json
import re
import tempfile
import threading
import urllib.request
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

import app
import standalone_html as html
import standalone_native as native


class StandaloneNative(unittest.TestCase):
    def test_assets_are_embedded_and_paths_restricted(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root/'asset.png').write_bytes(base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVQIHWP4z8DwHwAFgAI/ScL/nwAAAABJRU5ErkJggg=='))
            project={'cenas':[{'objetos_midia':[{'kind':'image','file':'asset.png'}]}]}
            assets=native.embed_media(project, root)
            self.assertIn('asset.png',assets)
            self.assertTrue(assets['asset.png'].startswith('data:image/png;base64,'))
            project['cenas'][0]['objetos_midia'][0]['file']='../private.png'
            with self.assertRaises(ValueError):native.embed_media(project,root)

    def test_portable_native_bootstrap_and_legacy_template_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            scene={'id':'x','titulo':'x','duracao':1,'fala':'','audio':{'voice_enabled':False,'muted':True},'imagem':{'arquivo':''},'video_clipe':{},'gil_nativo':{'source':'example.gil','duration':1},'objetos_midia':[]}
            project={'titulo':'Teste','video':{'width':640,'height':360,'draw_fps':2},'cenas':[scene]}
            with patch.object(html,'normalize',side_effect=lambda p:p),patch.object(html,'name',side_effect=lambda p:p),patch.object(html,'voice_source',return_value=None),patch.object(html,'scene_length',return_value=1),patch.object(html,'visualize',return_value='<svg xmlns="http://www.w3.org/2000/svg"/>'),patch.object(native,'embed_modules',return_value='<script type="importmap">{"imports":{}}</script>'):
                result=html.export_html('example',project,root,root,with_audio=False)
            page=(root/result['html']).read_text()
            self.assertIn('window.__RD_NATIVE_FRAME?.(i,time,playing)',page)
            self.assertIn("import {syncObjects,pauseObjects}",page)
            match=re.search(r"const encoded='([A-Za-z0-9+/=]+)'",page)
            payload=json.loads(base64.b64decode(match.group(1)))
            self.assertEqual(payload['scenes'][0]['gil_native']['source'],'example.gil')
            self.assertEqual(payload['scenes'][0]['objects'],[])

    def test_native_presentation_endpoint_and_capture_script(self):
        scene={'id':'x','duracao':1,'titulo':'x','gil_nativo':{'source':'example'},'objetos_midia':[{'kind':'gil'}]}
        project={'titulo':'x','cenas':[scene], 'video':{'width':640,'height':360}}
        srv=ThreadingHTTPServer(('127.0.0.1',0),app.Handler)
        worker=threading.Thread(target=srv.serve_forever,daemon=True);worker.start()
        try:
            with patch.object(app,'read_project',return_value=project),patch.object(app,'presentation_mix_status',return_value=([1],None)):
                with urllib.request.urlopen(f'http://127.0.0.1:{srv.server_port}/api/presentation?name=example',timeout=5) as response:
                    payload=json.load(response)
                    self.assertEqual(payload['project']['cenas'][0]['objetos_midia'][0]['kind'],'gil')
            with urllib.request.urlopen(f'http://127.0.0.1:{srv.server_port}/captura-record.js',timeout=5) as response:
                self.assertIn(b'getDisplayMedia',response.read())
        finally:
            srv.shutdown();srv.server_close();worker.join(timeout=3)
