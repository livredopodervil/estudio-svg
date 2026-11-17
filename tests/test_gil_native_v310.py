"""Regression: native GIL is optional, lossless and not a derived video."""
import hashlib, unittest, tempfile, os, threading, urllib.request
from pathlib import Path
from unittest.mock import patch
from http.server import ThreadingHTTPServer
from schema import normalize
import app, studio_core

class NativeGIL(unittest.TestCase):
    def project(self):
        source=(Path(__file__).resolve().parents[1]/'examples/components/field.gil').read_text()
        digest=hashlib.sha256(source.encode()).hexdigest()
        return normalize({'cenas':[{'duracao':12,'video_clipe':{'arquivo':'clip.mp4'},'audio':{'voice_text':'voz','voice_file':'voice.wav','tracks':[{'file':'music.wav'}]},'gil_nativo':{'format':'gil-timeline-0.1','origin':'gil','source':source,'source_sha256':digest,'origin_sha256':digest,'duration':12,'x':.4,'opacidade':.7}}]})
    def test_preserve_source_and_media(self):
        p=self.project();s=p['cenas'][0];self.assertEqual(normalize(p),p)
        self.assertEqual(s['video_clipe']['arquivo'],'clip.mp4');self.assertEqual(s['audio']['voice_file'],'voice.wav');self.assertEqual(s['audio']['tracks'][0]['file'],'music.wav');self.assertEqual(s['gil_nativo']['x'],.4)
        s['video_clipe']['arquivo']='';self.assertIn('gil_nativo',normalize(p)['cenas'][0])
    def test_reject_corrupt_source(self):
        p=self.project();p['cenas'][0]['gil_nativo']['source']+='x'
        with self.assertRaises(ValueError):normalize(p)
    def test_protect_legacy_export(self):
        with self.assertRaisesRegex(studio_core.StudioError,'GIL nativa'):studio_core.project_render('native',self.project())
    def test_runtime_route(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);(root/'src').mkdir();(root/'src/model.mjs').write_text('export const test=1;');(root/'private.txt').write_text('private')
            server=ThreadingHTTPServer(('127.0.0.1',0),app.Handler);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start();base=f'http://127.0.0.1:{server.server_port}'
            try:
                with patch.dict(os.environ,{'RD_GIL_ROOT':td}):
                    for path in ['/gil-native.mjs','/gil-runtime/src/model.mjs']:
                        with urllib.request.urlopen(base+path,timeout=3) as r:self.assertEqual(r.status,200);self.assertIn('javascript',r.headers['Content-Type'])
                    with self.assertRaises(urllib.error.HTTPError) as e:urllib.request.urlopen(base+'/gil-runtime/private.txt',timeout=3)
                    self.assertEqual(e.exception.code,404)
            finally:server.shutdown();server.server_close();thread.join(timeout=3)
if __name__=='__main__':unittest.main()
