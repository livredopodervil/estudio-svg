import json, os, tempfile, threading, unittest, urllib.request
from pathlib import Path
from unittest.mock import patch
from http.server import ThreadingHTTPServer
import app

class NativeDemo(unittest.TestCase):
    def test_demo_http(self):
        with tempfile.TemporaryDirectory() as td, patch.dict(os.environ, {'RD_GIL_ROOT':td}):
            server=ThreadingHTTPServer(('127.0.0.1',0),app.Handler)
            thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
            try:
                url=f'http://127.0.0.1:{server.server_port}/api/workspace/gil-example?id=native-demo'
                with urllib.request.urlopen(url,timeout=3) as res: data=json.load(res)
                self.assertEqual(data['name'],'native-demo.gil')
                self.assertEqual(data['source'],(Path(app.ROOT)/'examples/components/native-demo.gil').read_text())
                self.assertIn('animate ring rz',data['source'])
            finally:server.shutdown();server.server_close();thread.join(timeout=3)
