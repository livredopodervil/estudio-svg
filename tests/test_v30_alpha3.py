"""V3 Alpha 3 regressions: ZIP import, narration preservation and offline HTML."""
import base64
import io
import json
import shutil
import struct
import subprocess
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
import wave
import zipfile
from pathlib import Path
from unittest.mock import patch

from PIL import Image

import app
import studio_core
from project_import import import_zip
from standalone_html import export_html
from schema import normalize


def png():
    stream=io.BytesIO()
    Image.new('RGB',(64,80),(45,112,185)).save(stream,format='PNG')
    return stream.getvalue()


def sample_zip(project, files, project_path='projetos/filme.json'):
    content=io.BytesIO()
    with zipfile.ZipFile(content,'w',zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(project_path,json.dumps(project,ensure_ascii=False))
        for file,raw in files.items():
            archive.writestr(file,raw)
    return content.getvalue()


class ProjectZipImportTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.root=Path(self.tmp.name)
        self.projects=self.root/'projetos';self.media=self.root/'midia';self.cache=self.root/'cache'
        for p in (self.projects,self.media,self.cache):p.mkdir()

    def tearDown(self):self.tmp.cleanup()

    def write_zip(self,content):
        path=self.root/'import.zip';path.write_bytes(content);return path

    def test_import_with_assets_keeps_references_and_text(self):
        p={'cenas':[{'tipo':'foto','titulo':'A prancha','imagem':{'arquivo':'board.png'},
          'audio':{'voice_text':'Texto original','voice_enabled':True}}]}
        source=self.write_zip(sample_zip(p,{'midia/board.png':png()}))
        result=import_zip(source,'pacote_fiscal',self.projects,self.media,self.cache)
        self.assertEqual(result['name'],'pacote_fiscal')
        saved=json.loads((self.projects/'pacote_fiscal.json').read_text())
        self.assertEqual(saved['cenas'][0]['audio']['voice_text'],'Texto original')
        self.assertEqual(saved['cenas'][0]['imagem']['arquivo'],'board.png')
        self.assertEqual((self.media/'board.png').read_bytes(),png())

    def test_collision_renames_project_and_media_without_overwriting(self):
        (self.media/'board.png').write_bytes(b'existing-private')
        (self.projects/'pacote_fiscal.json').write_text('OLD')
        p={'trilha':'music.wav','cenas':[{'tipo':'cartoes','imagem':{'arquivo':'board.png'},
            'audio':{'music_file':'music.wav','voice_text':'continuar roteiro'}}]}
        # A real WAV file, with 1 s silence, is accepted by optional ffprobe validators.
        wav=io.BytesIO()
        with wave.open(wav,'wb') as a:
            a.setframerate(16000);a.setnchannels(1);a.setsampwidth(2)
            a.writeframes(bytes(32000))
        z=self.write_zip(sample_zip(p,{'assets/board.png':png(),'assets/music.wav':wav.getvalue()}))
        result=import_zip(z,'pacote_fiscal',self.projects,self.media,self.cache)
        self.assertEqual(result['name'],'pacote_fiscal_2')
        self.assertEqual((self.projects/'pacote_fiscal.json').read_text(),'OLD')
        self.assertEqual((self.media/'board.png').read_bytes(),b'existing-private')
        saved=json.loads((self.projects/'pacote_fiscal_2.json').read_text())
        self.assertEqual(saved['cenas'][0]['imagem']['arquivo'],'board_2.png')
        self.assertEqual(saved['cenas'][0]['audio']['music_file'],'music.wav')
        self.assertEqual(saved['cenas'][0]['audio']['voice_text'],'continuar roteiro')
        self.assertEqual(saved['trilha'],'music.wav')

    @unittest.skipUnless(shutil.which('ffmpeg') is not None,'FFmpeg required')
    def test_audio_only_webm_archive_accepts_narration_file(self):
        source=self.root/'voice.webm'
        subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-f','lavfi',
            '-i','sine=frequency=440:sample_rate=48000:duration=1', '-c:a','libopus',str(source)],
            check=True)
        p={'cenas':[{'tipo':'numero','audio':{'voice_text':'Manter texto','voice_enabled':True,
            'voice_file':'voice.webm'}}]}
        z=self.write_zip(sample_zip(p,{'midia/voice.webm':source.read_bytes()}))
        imported=import_zip(z,'voz',self.projects,self.media,self.cache,app.inspect_media)
        saved=json.loads((self.projects/(imported['name']+'.json')).read_text())
        self.assertEqual(saved['cenas'][0]['audio']['voice_text'],'Manter texto')
        self.assertEqual(saved['cenas'][0]['audio']['voice_file'],'voice.webm')

    def test_refuse_missing_media_atomically(self):
        p={'cenas':[{'tipo':'foto','imagem':{'arquivo':'not_here.png'}}]}
        with self.assertRaisesRegex(ValueError,'não contém mídia'):
            import_zip(self.write_zip(sample_zip(p,{})),'teste',self.projects,self.media,self.cache)
        self.assertEqual(list(self.projects.iterdir()),[])
        self.assertEqual(list(self.media.iterdir()),[])

    def test_refuse_traversal_symlinks_and_duplicates(self):
        p={'cenas':[{'tipo':'cartoes'}]}
        for filename in ('../escape.txt','midia/../../escape.png'):
            content=sample_zip(p,{filename:b'bad'})
            with self.subTest(filename=filename),self.assertRaisesRegex(ValueError,'caminho proibido'):
                import_zip(self.write_zip(content),'teste',self.projects,self.media,self.cache)
        buf=io.BytesIO()
        with zipfile.ZipFile(buf,'w') as z:
            z.writestr('filme.json',json.dumps(p))
            link=zipfile.ZipInfo('midia/link.png');link.create_system=3
            link.external_attr=(0o120777<<16)
            z.writestr(link,b'/etc/passwd')
        with self.assertRaisesRegex(ValueError,'link simbólico'):
            import_zip(self.write_zip(buf.getvalue()),'teste',self.projects,self.media,self.cache)

    def test_http_chunk_import_bundle_and_open_project(self):
        p={'cenas':[{'tipo':'foto','imagem':{'arquivo':'board.png'},'audio':{'voice_text':'Não apagar'}}]}
        content=sample_zip(p,{'midia/board.png':png()})
        with patch.object(app,'PROJECTS',self.projects),patch.object(app,'MEDIA',self.media),patch.object(app,'CACHE',self.cache):
            server=__import__('http.server',fromlist=['ThreadingHTTPServer']).ThreadingHTTPServer(('127.0.0.1',0),app.Handler)
            thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
            url=f'http://127.0.0.1:{server.server_port}'
            def post(path,data):
                req=urllib.request.Request(url+path,data=json.dumps(data).encode(),headers={'Content-Type':'application/json'})
                with urllib.request.urlopen(req,timeout=10) as resp:return json.load(resp)
            try:
                start=post('/api/upload/chunks',{'op':'start','kind':'bundle','filename':'album.zip','size':len(content)})
                post('/api/upload/chunks',{'op':'append','upload_id':start['upload_id'],'index':0,'data':base64.b64encode(content).decode()})
                result=post('/api/upload/chunks',{'op':'finish','upload_id':start['upload_id'],'name':'album'})
                self.assertEqual(result['name'],'album')
                with urllib.request.urlopen(url+'/api/project?name=album',timeout=10) as response:
                    saved=json.load(response)['project']
                self.assertEqual(saved['cenas'][0]['audio']['voice_text'],'Não apagar')
                self.assertEqual(saved['cenas'][0]['imagem']['arquivo'],'board.png')
            finally:
                server.shutdown();server.server_close();thread.join(timeout=5)


class AudioPreservationTests(unittest.TestCase):
    def test_ui_does_not_destroy_script_on_voice_attachment_or_removal(self):
        js=(Path(__file__).resolve().parents[1]/'web'/'app.js').read_text()
        self.assertNotIn("scene.audio.voice_text='';scene.fala=''",js)
        self.assertIn("scene.audio.voice_file=filename;scene.audio.voice_enabled=true",js)
        self.assertIn("t.id==='removeVoiceFile'",js)
        self.assertIn("t.id==='removeSceneMusic'",js)
        self.assertNotIn("voice_text:'',voice_file:'',music_file:'',tracks:[],muted:true",js)
        self.assertIn("voice_file:'',music_file:'',tracks:[],muted:false",js)


@unittest.skipUnless(shutil.which('ffmpeg') is not None,'FFmpeg required')
class OfflineHtmlTests(unittest.TestCase):
    def test_self_contained_html_renders_svg_frames_and_video(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);media=root/'midia';output=root/'render'
            media.mkdir();output.mkdir()
            (media/'board.png').write_bytes(png())
            clip=media/'clip.mp4'
            subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-f','lavfi',
                '-i','color=c=blue:s=80x120:d=1:r=10','-c:v','libx264','-pix_fmt','yuv420p',str(clip)],
                check=True,stdout=subprocess.DEVNULL)
            project={'video':{'width':720,'height':1280,'draw_fps':2},'cenas':[{'tipo':'foto',
                'duracao':1,'imagem':{'arquivo':'board.png'},'video_clipe':{'arquivo':'clip.mp4',
                    'x':.5,'y':.4,'w':.5,'h':.25}}]}
            result=export_html('teste',project,media,output,with_audio=False)
            page=(output/result['html']).read_text()
            self.assertIn('data:video/mp4;base64,',__import__('base64').b64decode(page.split("const encoded='")[1].split("';")[0]).decode())
            self.assertNotIn('fetch(',page)
            self.assertIn('Audio',page.replace('audio','Audio') if 'audio' in page else 'Audio')
            self.assertIn('ssimage:',page)
            self.assertIn("replace(/ssimage:(\\d+)/g",page)
            self.assertLess((output/result['html']).stat().st_size,5_000_000)

    def test_export_html_job_and_download_route(self):
        from http.server import ThreadingHTTPServer
        import time
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            media=root/'midia';projects=root/'projetos';output=root/'render'
            for p in (media,projects,output):p.mkdir()
            (projects/'prova.json').write_text(json.dumps({'titulo':'Prova de download',
              'video':{'width':720,'height':1280,'draw_fps':2},
              'cenas':[{'tipo':'cartoes','duracao':1,'titulo':'Cena sem áudio'}]}))
            with patch.object(app,'MEDIA',media),patch.object(app,'PROJECTS',projects),patch.object(app,'OUTPUT',output),\
                 patch.object(studio_core,'OUTPUT',output),patch.object(studio_core,'MEDIA',media):
                server=ThreadingHTTPServer(('127.0.0.1',0),app.Handler)
                thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
                base=f'http://127.0.0.1:{server.server_port}'
                try:
                    req=urllib.request.Request(base+'/api/job',
                        data=json.dumps({'name':'prova','mode':'export-html-silent'}).encode(),
                        headers={'Content-Type':'application/json'})
                    with urllib.request.urlopen(req,timeout=15) as response:
                        token=json.load(response)['job']
                    deadline=time.monotonic()+25
                    while time.monotonic()<deadline:
                        with urllib.request.urlopen(base+'/api/job/'+token,timeout=10) as response:
                            job=json.load(response)
                        if job['status'] in ('done','error'):break
                        time.sleep(.1)
                    self.assertEqual(job['status'],'done',job.get('error'))
                    filename=job['result']['html']
                    with urllib.request.urlopen(base+'/api/output/'+filename,timeout=10) as response:
                        self.assertEqual(response.headers.get_content_type(),'text/html')
                        self.assertIn('attachment',response.headers.get('Content-Disposition',''))
                        page=response.read().decode('utf8')
                    self.assertIn('Prova de download',page)
                    self.assertIn('const encoded=',page)
                finally:
                    server.shutdown();server.server_close();thread.join(timeout=5)

    def test_audio_mix_embedded_without_internet(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);media=root/'midia';output=root/'render'
            for p in (media,output):p.mkdir()
            project={'video':{'width':640,'height':360,'draw_fps':1},'cenas':[{
                'tipo':'cartoes','titulo':'Sem locução','duracao':1,
                'audio':{'voice_enabled':False}}]}
            with patch.object(studio_core,'OUTPUT',output),patch.object(studio_core,'MEDIA',media):
                result=export_html('sem_locucao',project,media,output,with_audio=True)
            page=(output/result['html']).read_text()
            data=json.loads(base64.b64decode(page.split("const encoded='")[1].split("';")[0]))
            self.assertTrue(data['audio'].startswith('data:audio/mpeg;base64,'))
            self.assertNotEqual(result['html'], 'sem_locucao_standalone_sem_audio.html')
            self.assertEqual(len(data['scenes']),1)

if __name__=='__main__':unittest.main()
