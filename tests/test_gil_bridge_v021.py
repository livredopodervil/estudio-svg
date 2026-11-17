import unittest,tempfile,os,hashlib,json,threading,urllib.request,urllib.error, subprocess, shutil
from pathlib import Path
from unittest.mock import patch
from http.server import ThreadingHTTPServer
import app,studio_core
from schema import normalize
from gil_bridge import settings,render_component
from project_bundle import bundle_to_file
from project_import import import_zip
SOURCE='''gil timeline 0.1 {
stage {"width":640,"height":360,"duration":1,"background":"#101c2c","camera":"cam"}
resource camR camera {"z":12,"fov":45}
resource cube mesh.box {"size":2,"color":"#66ccff"}
resource click audio.tone {"frequency":880,"gain":0.1,"wave":"sine"}
object cam camR - {}
object box cube - {}
object beep click - {}
animate box ry {"expr":"t*180"}
cue beep {"start":0.15,"duration":0.15}
}
'''
class Bridge(unittest.TestCase):
    def test_validation(self):
        for data in ({'source':'x','format':'../x'},{'source':'x','duration':float('nan')},{'source':'x','fps':True},{'source':'x','extra':'/tmp'},{'source':'x','duration':61}):
            with self.assertRaises(ValueError):settings(data)
        self.assertEqual(settings({'source':SOURCE})[1],'gil')
    def test_roundtrip_voice_and_metadata(self):
        h=hashlib.sha256(SOURCE.encode()).hexdigest();c={'format':'gil-timeline-0.1','origin':'gil','origin_sha256':h,'source_sha256':h,'source':SOURCE,'duration':1}
        pr=normalize({'cenas':[{'fala':'voz','audio':{'voice_text':'voz','voice_file':'voice.wav','tracks':[{'file':'clip.mp4','start':0,'volume':.4}]},'video_clipe':{'arquivo':'clip.mp4'},'componente_gil':c}]});s=pr['cenas'][0];self.assertEqual(s['componente_gil'],c);self.assertEqual(s['audio']['voice_text'],'voz');self.assertEqual(s['audio']['voice_file'],'voice.wav');self.assertEqual(normalize(pr),pr)
        s['componente_gil']['source']+='x';self.assertNotIn('componente_gil',normalize(pr)['cenas'][0])
    @unittest.skipUnless(os.environ.get('RD_GIL_ROOT') and shutil.which('ffmpeg') and shutil.which('node'),'Execute com RD_GIL_ROOT + Node/FFmpeg/rasterizador')
    def test_actual_http_render_bundle_and_audio(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td);media=p/'media';cache=p/'cache';out=p/'out';projects=p/'projects';media.mkdir();out.mkdir();projects.mkdir();cache.mkdir();(cache/'audio').mkdir()
            server=ThreadingHTTPServer(('127.0.0.1',0),app.Handler);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start();base=f'http://127.0.0.1:{server.server_port}'
            def request(origin):
                req=urllib.request.Request(base+'/api/component/gil',data=json.dumps({'source':SOURCE,'duration':.6,'fps':12,'long_side':320,'effects':True}).encode(),headers={'Content-Type':'application/json','Origin':origin})
                with urllib.request.urlopen(req,timeout=150) as r:return json.load(r)
            try:
                with patch.object(app,'CACHE',cache),patch.object(app,'MEDIA',media):
                    with self.assertRaises(urllib.error.HTTPError) as ex:request('https://example.org')
                    self.assertEqual(ex.exception.code,403)
                    r=request(base);self.assertTrue(r['effects']);self.assertEqual(app.inspect_media(media/r['filename'],'video'),r['duration']);app.inspect_media(media/r['filename'],'audio')
                voice=media/'voice.wav';subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','sine=frequency=350:duration=0.4','-c:a','pcm_s16le',str(voice)],check=True)
                pr=normalize({'video':{'width':640,'height':360,'fps':24,'draw_fps':4},'cenas':[{'duracao':1,'titulo':'Voz','audio':{'voice_text':'Teste','voice_file':'voice.wav','voice_enabled':True,'tracks':[{'file':r['filename'],'start':0,'volume':.4}]},'video_clipe':{'arquivo':r['filename'],'repetir':False},'componente_gil':r['component']}]})
                with patch.object(studio_core,'CACHE',cache),patch.object(studio_core,'MEDIA',media):
                    mixed,_=studio_core.make_scene_audio(pr['cenas'][0],pr,1,voice);self.assertTrue(mixed.is_file())
                zipfile=p/'sample.zip';bundle_to_file('test',pr,media,zipfile);dest=p/'dest';dest.mkdir();result=import_zip(zipfile,'imported',projects,dest,cache,app.inspect_media);restored=json.loads((projects/(result['name']+'.json')).read_text());self.assertEqual(restored['cenas'][0]['componente_gil']['source'],SOURCE);self.assertEqual(restored['cenas'][0]['audio']['voice_text'],'Teste');self.assertEqual(len(restored['cenas'][0]['audio']['tracks']),1)
            finally:server.shutdown();server.server_close();thread.join(timeout=5)
if __name__=='__main__':unittest.main()
