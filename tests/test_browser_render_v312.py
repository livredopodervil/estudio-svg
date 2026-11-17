import math, shutil, struct, tempfile, threading, unittest, urllib.request, wave
from pathlib import Path
from http.server import ThreadingHTTPServer
from unittest.mock import patch
import json
import app
import studio_core as core
from schema import normalize

class BrowserMix(unittest.TestCase):
    def fixture(self, path, seconds=0.4):
        with wave.open(str(path),'wb') as w:
            w.setparams((1,2,48000,0,'NONE','not compressed'))
            w.writeframes(b''.join(struct.pack('<h',round(8000*math.sin(2*math.pi*440*i/48000))) for i in range(round(seconds*48000))))

    def test_effective_duration_with_silent_scenes(self):
        p=normalize({'cenas':[{'duracao':1.17},{'duracao':1.23}], 'video':{'draw_fps':2}})
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'audio').mkdir()
            with patch.object(core,'CACHE',root):
                target=core.browser_audio_mix(p,root/'result.wav')
                with wave.open(str(target),'rb') as w:
                    self.assertEqual(w.getnframes(),144000);self.assertEqual(w.getframerate(),48000)

    @unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'),'ffmpeg/ffprobe necessário')
    def test_voice_preserved_at_nominal_offset_and_visual_edit_preserves_cache(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'audio').mkdir();self.fixture(root/'voice.wav')
            p=normalize({'cenas':[{'duracao':1.13,'audio':{'voice_enabled':True,'voice_file':'voice.wav','voice_delay':.2}}, {'duracao':.73}]})
            with patch.object(core,'CACHE',root),patch.object(core,'MEDIA',root):
                path=core.browser_audio_mix(p,root/'result.wav')
                before=sorted((root/'audio').glob('*.wav'))
                p['cenas'][0]['objetos_midia']=[{'id':'visual-only'}]
                core.browser_audio_mix(p,root/'second.wav')
                self.assertEqual(before,sorted((root/'audio').glob('*.wav')))
                self.assertEqual(path.read_bytes(),(root/'second.wav').read_bytes())
                with wave.open(str(path),'rb') as w:
                    self.assertEqual(w.getnframes(),round(sum(core.browser_audio_plan(p)[0])*48000));self.assertEqual(set(w.readframes(9000)),{0});w.setpos(12000);self.assertTrue(any(w.readframes(8000)))
                p['cenas'][0]['duracao']=.5
                lengths,_=core.browser_audio_plan(p);self.assertGreater(lengths[0],.5);core.browser_audio_mix(p,root/'extended.wav')
                p['encaixe_voz']='avisar'
                with self.assertRaisesRegex(core.StudioError,'Narração excede'):core.browser_audio_mix(p,root/'fail.wav')

    def test_missing_voice_fails_loudly(self):
        p=normalize({'cenas':[{'duracao':1,'audio':{'voice_enabled':True,'voice_text':'Locução de teste não gerada'}}]})
        with tempfile.TemporaryDirectory() as d,patch.object(core,'CACHE',Path(d)):
            with self.assertRaisesRegex(core.StudioError,'Falta a locução'):core.browser_audio_mix(p,Path(d)/'fail.wav')

    def test_http_mix_and_module(self):
        p=normalize({'cenas':[{'duracao':.73}]})
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'audio').mkdir()
            srv=ThreadingHTTPServer(('127.0.0.1',0),app.Handler);t=threading.Thread(target=srv.serve_forever,daemon=True);t.start()
            base='http://127.0.0.1:'+str(srv.server_port)
            try:
                with patch.object(core,'CACHE',root),patch.object(app,'read_project',return_value=p):
                    with urllib.request.urlopen(base+'/api/preview/timing?name=test',timeout=5) as r:self.assertEqual(json.load(r)['scenes'],[{'id':p['cenas'][0]['id'],'seconds':core.browser_audio_plan(p)[0][0]}])
                    with urllib.request.urlopen(urllib.request.Request(base+'/api/browser-render/audio',data=json.dumps({'project':p}).encode(),headers={'Content-Type':'application/json'}),timeout=10) as r:
                        self.assertEqual(r.headers['Content-Type'],'audio/wav');self.assertEqual(json.loads(r.headers['X-Estudio-Durations']),core.browser_audio_plan(p)[0]);data=r.read()
                    self.assertEqual(data[:4],b'RIFF')
                    with urllib.request.urlopen(base+'/browser-render.mjs',timeout=5) as r:self.assertIn(b'export async function exportBrowser',r.read())
                    def post(url,body):
                        return urllib.request.urlopen(urllib.request.Request(base+url,data=json.dumps(body).encode(),headers={'Content-Type':'application/json'}),timeout=10)
                    with post('/api/browser-render/audio',{'project':p,'stream':True}) as r:m=json.load(r)
                    self.assertEqual(m['durations'],core.browser_audio_plan(p)[0])
                    with urllib.request.urlopen(urllib.request.Request(base+m['url'],headers={'Range':'bytes=0-43'}),timeout=5) as r:
                        self.assertEqual(r.status,206);self.assertEqual(len(r.read()),44)
                    with urllib.request.urlopen(urllib.request.Request(base+m['url'],method='HEAD'),timeout=5) as r:self.assertGreater(int(r.headers['Content-Length']),44)
                    with post('/api/browser-render/release',{'token':m['token']}) as r:self.assertTrue(json.load(r)['ok'])
                    self.assertFalse((root/'browser-render'/(m['token']+'.wav')).exists())
            finally:srv.shutdown();srv.server_close();t.join(timeout=5)

    def test_ten_minute_plan_preserves_document(self):
        p=normalize({'cenas':[{'duracao':300},{'duracao':300}]})
        before=json.dumps(p)
        self.assertEqual(core.browser_audio_plan(p)[0],[300,300])
        self.assertEqual(json.dumps(p),before)
