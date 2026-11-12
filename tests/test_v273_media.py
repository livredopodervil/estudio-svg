"""New regressions for full-height SVG canvas and local video composition."""
import unittest
import tempfile
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

from schema import normalize, video_clip_dict
from svg_graphic import clean_svg
from graphics import visualize
from scene_video import geometry,clip_filter,overlay_clip
from studio_core import convert_svg, run

class MediaV273Tests(unittest.TestCase):
    def test_clip_roundtrip_and_bounds(self):
        project=normalize({'video':{'width':720,'height':1280},'cenas':[{'tipo':'svg','video_clipe':{'arquivo':'ok.webm','x':2,'y':-.5,'w':0,'h':4,'opacidade':2,'fit':'invalid'}}]})
        clip=project['cenas'][0]['video_clipe']
        self.assertEqual(clip['arquivo'],'ok.webm')
        self.assertEqual(clip['x'],1)
        self.assertEqual(clip['y'],0)
        self.assertEqual(clip['w'],.08)
        self.assertEqual(clip['h'],1)
        self.assertEqual(clip['opacidade'],1)
        self.assertEqual(clip['fit'],'cover')
        self.assertEqual(normalize(project)['cenas'][0]['video_clipe'],clip)

    def test_svg_full_portrait_viewport_not_clipped(self):
        with tempfile.TemporaryDirectory() as td:
            svg='<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 -778 1280 2276"><rect x="170" y="-500" width="340" height="320" fill="#00ff00"/></svg>'
            clean=clean_svg(svg,Path(td),storage=False)
            self.assertIn('height="2276"',clean)
            scene=normalize({'video':{'width':720,'height':1280},'cenas':[{'tipo':'svg','svg':svg}]})['cenas'][0]
            final=visualize(scene,.5,0,1,Path(td),720,1280)
            root=ET.fromstring(final)
            children=[x for x in root.iter() if x.tag.endswith('svg')]
            self.assertEqual(len(children),2)
            self.assertEqual(children[-1].get('viewBox'),'0 -778 1280 2276')
            self.assertEqual(children[-1].get('height'),'2276')
            png=convert_svg(final,720,1280)
            self.assertTrue(png.startswith(b'\x89PNG'))

    def test_legacy_720_artwork_is_still_centered(self):
        scene=normalize({'video':{'width':720,'height':1280},'cenas':[{'tipo':'svg','svg':'<circle cx="640" cy="360" r="90" fill="red"/>'}]})['cenas'][0]
        output=visualize(scene,.5,0,1,None,720,1280)
        self.assertIn('translate(0,',output)

    def test_clip_geometry_and_filter(self):
        c=video_clip_dict({'arquivo':'video.mp4','x':.5,'y':.5,'w':.5,'h':.4,'fit':'contain'})
        self.assertEqual(geometry(c,720,1280),(180,384,360,512))
        text=clip_filter(c,720,1280,24)
        self.assertIn('pad=360:512',text)
        self.assertIn('repeatlast=0',text)

    def test_video_overlay_ffmpeg(self):
        with tempfile.TemporaryDirectory() as td:
            td=Path(td);base=td/'base.mp4';source=td/'source.mp4';out=td/'final.mp4'
            for dst,color in [(base,'blue'),(source,'red')]:
                subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-f','lavfi','-i',f'color=c={color}:s=320x240:r=24','-t','1','-c:v','libx264','-pix_fmt','yuv420p',str(dst)],check=True,timeout=20)
            c=video_clip_dict({'arquivo':'source.mp4','w':.5,'h':.5,'x':.5,'y':.5,'repetir':False})
            overlay_clip(base,source,out,c,320,240,24,1.,run)
            self.assertTrue(out.exists())
            self.assertGreater(out.stat().st_size,1000)

if __name__=='__main__': unittest.main()

class HTTPUploadV273Tests(unittest.TestCase):
    def test_chunked_video_upload_and_range(self):
        import io,base64,json,threading,urllib.request,urllib.error
        from http.server import ThreadingHTTPServer
        from app import Handler, UPLOADS
        from studio_core import MEDIA
        with tempfile.TemporaryDirectory() as td:
            sample=Path(td)/'source.mp4'
            subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-f','lavfi','-i','color=c=red:s=160x120:r=12','-t','0.6','-c:v','libx264','-pix_fmt','yuv420p',str(sample)],check=True,timeout=30)
            raw=sample.read_bytes()
            server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
            thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
            base=f'http://127.0.0.1:{server.server_port}'
            def post(data):
                payload=json.dumps(data).encode()
                request=urllib.request.Request(base+'/api/upload/chunks',data=payload,headers={'Content-Type':'application/json'})
                with urllib.request.urlopen(request,timeout=20) as r:return json.loads(r.read())
            target=None
            try:
                upload=post({'op':'start','kind':'video','filename':'camera.mp4','size':len(raw)})['upload_id']
                for i,part in enumerate([raw[:len(raw)//2],raw[len(raw)//2:]]):
                    post({'op':'append','upload_id':upload,'index':i,'data':base64.b64encode(part).decode()})
                fn=post({'op':'finish','upload_id':upload})['filename']
                target=MEDIA/fn
                self.assertEqual(target.read_bytes(),raw)
                req=urllib.request.Request(base+'/api/media/clip?file='+fn,headers={'Range':'bytes=0-15'})
                with urllib.request.urlopen(req,timeout=20) as result:
                    self.assertEqual(result.status,206)
                    self.assertEqual(result.read(),raw[:16])
            finally:
                server.shutdown();server.server_close();thread.join(timeout=5)
                if target:target.unlink(missing_ok=True)
