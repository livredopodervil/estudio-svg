import importlib.util, json, tempfile, threading, unittest, urllib.request, urllib.error, time, shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('gil_local_server',ROOT/'gil/tools/local_server.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
class RenderHTTP(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.state=mod.RenderState(self.tmp.name,timeout=90);self.server=mod.Server(('127.0.0.1',0),self.state);self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start();self.url=self.server.origin
    def tearDown(self):
        self.server.shutdown();self.server.server_close();self.thread.join();self.state.close();self.tmp.cleanup()
    def req(self,path,body=None,headers=None):
        h=headers or {};return urllib.request.urlopen(urllib.request.Request(self.url+path,data=body,headers=h),timeout=10)
    def post(self,data,valid=True):
        return self.req('/api/render',json.dumps(data).encode(),{'Content-Type':'application/json','Origin':self.url if valid else 'https://example.invalid','X-GIL-Token':self.server.token})
    def test_static_and_origin_guards(self):
        self.assertEqual(self.req('/').status,200);self.assertEqual(self.req('/src/model.mjs').status,200)
        for path,headers in [('/tools/local_server.py',{}),('/legacy/',{}),('/api/session',{'Host':'evil.test'}),('/api/session',{'Sec-Fetch-Site':'cross-site'})]:
            with self.assertRaises(urllib.error.HTTPError):self.req(path,headers=headers)
        with self.assertRaises(urllib.error.HTTPError) as cm:self.post({},False)
        self.assertEqual(cm.exception.code,403)
        with self.assertRaises(urllib.error.HTTPError) as cm:self.post({'source':'bad','duration':1,'output':'/tmp/forbidden'})
        self.assertEqual(cm.exception.code,400)
    @unittest.skipUnless(all(shutil.which(x) for x in ('node','ffmpeg','ffprobe')) and (shutil.which('rsvg-convert') or importlib.util.find_spec('cairosvg')),'Dependências reais do render ausentes')
    def test_actual_render_and_download(self):
        source=(ROOT/'gil/examples/orbit.gil').read_text();body={'source':source,'duration':.25,'fps':12,'long_side':320,'silent':False};j=json.load(self.post(body))['job'];self.assertEqual(j['status'],'running')
        deadline=time.monotonic()+90
        while time.monotonic()<deadline:
            job=json.load(self.req('/api/render'))['job']
            if job['status']!='running':break
            time.sleep(.2)
        self.assertEqual(job['status'],'done',job)
        path='/api/video/'+job['id']+'.mp4';r=self.req(path,headers={'Range':'bytes=0-11'});self.assertEqual(r.status,206);self.assertEqual(r.read()[4:8],b'ftyp');r=self.req(path+'?download=1');self.assertIn('attachment',r.headers['Content-Disposition']);self.assertEqual(len(r.read()),job['bytes'])

class WavePackage(unittest.TestCase):
    def test_wave_component_native_patch(self):
        import sys,zipfile,hashlib
        sys.path.insert(0,str(ROOT/'rdstudio'));from patches import PatchManager
        archive=next((ROOT/'demo').glob('gil-gil-superposicao-ondas-*.rdpatch.zip'))
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)/'site';root.mkdir();(root/'index.html').write_text('original');manager=PatchManager(root);manager.state=Path(d)/'state';manager._inbox_paths=lambda:[archive.parent]
            plan=manager.plan(archive.name);self.assertTrue(plan['ready']);self.assertEqual(len(plan['files']),5);manager.apply(archive.name,'APLICAR');page=root/'projetos/gil-superposicao-ondas';m=json.loads((page/'component.json').read_text());self.assertEqual(m['render']['source_sha256'],hashlib.sha256((page/'projeto.gil.txt').read_bytes()).hexdigest());self.assertEqual((root/'index.html').read_text(),'original');manager.remove(plan['id'],'REMOVER');self.assertFalse((page/'index.html').exists())
