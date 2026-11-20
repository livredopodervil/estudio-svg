import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from rd_voices.api import try_handle


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if try_handle(self):return
        self.send_response(404);self.end_headers()
    def do_POST(self):
        if try_handle(self):return
        self.send_response(404);self.end_headers()
    def log_message(self,*args):pass


class ApiRoutes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        cls.t=threading.Thread(target=cls.server.serve_forever, daemon=True);cls.t.start()
        cls.root=f'http://127.0.0.1:{cls.server.server_address[1]}'

    @classmethod
    def tearDownClass(cls):cls.server.shutdown();cls.server.server_close();cls.t.join(timeout=2)

    def test_catalog_complete(self):
        with urlopen(self.root+'/api/rd-voices/catalog',timeout=5) as r:
            obj=json.load(r)
            self.assertEqual(obj['count'],318)
            self.assertEqual(len(obj['voices']),318)
            self.assertFalse(obj['capabilities']['native_emotion'])

    def test_js_and_css(self):
        for fname in ('controls.mjs','controls.css'):
            with urlopen(self.root+'/api/rd-voices/'+fname,timeout=5) as r:
                self.assertEqual(r.status,200)
                self.assertGreater(len(r.read()),300)

    def test_invalid_voice_rejected_before_network(self):
        request=Request(self.root+'/api/rd-voices/synthesize',data=json.dumps({'text':'Oi','voice':'edge:INVALID'}).encode(),headers={'Content-Type':'application/json'},method='POST')
        with self.assertRaises(HTTPError) as e:urlopen(request,timeout=5)
        self.assertEqual(e.exception.code,400)

    def test_other_paths_untouched(self):
        with self.assertRaises(HTTPError) as e:urlopen(self.root+'/old-player',timeout=5)
        self.assertEqual(e.exception.code,404)

    def test_missing_file(self):
        with self.assertRaises(HTTPError) as e:urlopen(self.root+'/api/rd-voices/audio/'+'a'*64+'.mp3',timeout=5)
        self.assertEqual(e.exception.code,404)

if __name__=='__main__':unittest.main()
