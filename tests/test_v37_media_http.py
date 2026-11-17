import tempfile, threading, unittest, urllib.request, urllib.error
from pathlib import Path
from http.server import ThreadingHTTPServer
from unittest.mock import patch
import app

class MediaHead(unittest.TestCase):
    def test_head_range_and_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            content=b'abcde'*64; (Path(tmp)/'clip.mp4').write_bytes(content)
            srv=ThreadingHTTPServer(('127.0.0.1',0),app.Handler); t=threading.Thread(target=srv.serve_forever,daemon=True);t.start()
            base=f'http://127.0.0.1:{srv.server_port}'
            def request(route,method='GET',headers=None):
                try:
                    with urllib.request.urlopen(urllib.request.Request(base+route,method=method,headers=headers or {}),timeout=5) as r:return r.status,r.headers,r.read()
                except urllib.error.HTTPError as e:return e.code,e.headers,e.read()
            try:
                with patch.object(app,'MEDIA',Path(tmp)):
                    code,headers,body=request('/api/media/clip?file=clip.mp4','HEAD');self.assertEqual(code,200);self.assertEqual(int(headers['Content-Length']),len(content));self.assertEqual(headers['Content-Type'],'video/mp4');self.assertEqual(body,b'')
                    code,headers,body=request('/api/media/clip?file=clip.mp4',headers={'Range':'bytes=7-31'});self.assertEqual(code,206);self.assertEqual(body,content[7:32]);self.assertEqual(headers['Content-Range'],f'bytes 7-31/{len(content)}')
                    self.assertEqual(request('/api/media/clip?file=missing.mp4','HEAD')[0],404)
                    self.assertEqual(request('/api/media/clip?file=../clip.mp4','HEAD')[0],400)
                    code,_,body=request('/timing-v37.js');self.assertEqual(code,200);self.assertIn(b'StudioTimingV37',body)
            finally:srv.shutdown();srv.server_close();t.join(timeout=5)
