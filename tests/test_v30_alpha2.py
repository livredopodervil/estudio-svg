"""Alpha 2: portable ZIP, image names, scene silence, 3D hierarchy and camera tracks."""
import io
import json
import math
import tempfile
import unittest
import wave
import zipfile
from pathlib import Path
from unittest.mock import patch

from PIL import Image
from schema import normalize
from project_bundle import bundle_to_file, referenced_media
from spatial_scene import normalize_spatial, render_spatial, camera_pose
from app import image_alias
import app
import studio_core


class BundleAndImageTests(unittest.TestCase):
    def test_bundle_contains_json_and_only_referenced_images(self):
        with tempfile.TemporaryDirectory() as root:
            folder=Path(root);media=folder/'midia';media.mkdir()
            (media/'prancha.jpg').write_bytes(b'JPEG-data')
            (media/'nao_usar.jpg').write_bytes(b'PRIVATE')
            raw={'video':{'width':720,'height':1280},'cenas':[
                {'tipo':'cartoes','imagem':{'arquivo':'prancha.jpg','crop':[0,.5,.5,.5]}},
                {'tipo':'numero','imagem':{'arquivo':'prancha.jpg'}}]}
            z=folder/'bundle.zip';r=bundle_to_file('teste',raw,media,z)
            self.assertEqual(r['files'],['prancha.jpg'])
            with zipfile.ZipFile(z) as bundle:
                self.assertEqual(set(bundle.namelist()),{'projetos/teste.json','midia/prancha.jpg','LEIA-ME.txt'})
                project=json.loads(bundle.read('projetos/teste.json'))
                self.assertEqual(project['cenas'][0]['imagem']['crop'],[0,.5,.5,.5])
                self.assertEqual(bundle.read('midia/prancha.jpg'),b'JPEG-data')

    def test_bundle_rejects_missing_assets_and_traversal(self):
        with tempfile.TemporaryDirectory() as root:
            folder=Path(root)
            p={'cenas':[{'tipo':'foto','imagem':{'arquivo':'missing.jpg'}}]}
            with self.assertRaisesRegex(ValueError,'não encontrada'):
                bundle_to_file('demo',p,folder,folder/'out.zip')
            self.assertFalse((folder/'out.zip').exists())
            with self.assertRaises(ValueError):
                bundle_to_file('demo',{'cenas':[{'tipo':'foto','imagem':{'arquivo':'../private'}}]},folder,folder/'out.zip')

    def test_image_alias_never_overwrites_existing_names(self):
        with tempfile.TemporaryDirectory() as root:
            folder=Path(root)
            (folder/'Prancha_A.jpg').write_bytes(b'existing')
            with patch.object(app,'MEDIA',folder):
                self.assertEqual(image_alias('Prancha A.png'),'Prancha_A_2.jpg')
                self.assertEqual(image_alias('../../segredo.png'),'segredo.jpg')
                with self.assertRaisesRegex(Exception,'Escolha um nome'):
                    image_alias('...')


    def test_http_upload_rename_and_download_bundle(self):
        import base64
        import threading
        import urllib.request
        from http.server import ThreadingHTTPServer
        with tempfile.TemporaryDirectory() as root:
            folder=Path(root);media=folder/'midia';cache=folder/'cache';projects=folder/'projetos'
            for item in (media,cache,projects):item.mkdir()
            sample=io.BytesIO()
            Image.new('RGB',(250,360),(188,73,41)).save(sample,format='PNG')
            with patch.object(app,'MEDIA',media),patch.object(app,'CACHE',cache),patch.object(app,'PROJECTS',projects):
                server=ThreadingHTTPServer(('127.0.0.1',0),app.Handler)
                thread=threading.Thread(target=server.serve_forever,daemon=True)
                thread.start()
                base=f'http://127.0.0.1:{server.server_port}'
                def post(path,payload):
                    raw=json.dumps(payload).encode()
                    request=urllib.request.Request(base+path,data=raw,headers={'Content-Type':'application/json'})
                    with urllib.request.urlopen(request,timeout=10) as response:
                        return json.load(response)
                try:
                    uploaded=post('/api/upload',{'kind':'image','filename':'test.png','preferred_name':'Prancha Original',
                                  'data':base64.b64encode(sample.getvalue()).decode()})
                    self.assertEqual(uploaded['filename'],'Prancha_Original.jpg')
                    with Image.open(media/uploaded['filename']) as image:
                        self.assertEqual(image.size,(250,360))
                    renamed=post('/api/media/image/alias',{'file':uploaded['filename'],'new_name':'prancha compartilhada'})
                    self.assertEqual(renamed['filename'],'prancha_compartilhada.jpg')
                    self.assertTrue((media/uploaded['filename']).exists())
                    app.save_project('demo',{'cenas':[{'tipo':'cartoes','imagem':{'arquivo':renamed['filename']}}]})
                    with urllib.request.urlopen(base+'/api/project/bundle?name=demo',timeout=15) as r:
                        self.assertEqual(r.status,200)
                        self.assertEqual(r.headers.get_content_type(),'application/zip')
                        archive_bytes=r.read()
                    with zipfile.ZipFile(io.BytesIO(archive_bytes)) as z:
                        self.assertIn('midia/prancha_compartilhada.jpg',z.namelist())
                        self.assertIn('projetos/demo.json',z.namelist())
                finally:
                    server.shutdown();server.server_close();thread.join(timeout=5)

    def test_image_import_is_offered_in_composer_and_bundle_in_editor(self):
        root=Path(__file__).resolve().parents[1]
        composer=(root/'web/image-composer.js').read_text()
        ui=(root/'web/index.html').read_text()
        for needle in ('id="icImportFile"','id="icFileName"','id="icRename"','cropResize','cropMove'):
            self.assertIn(needle,composer)
        self.assertIn('id="exportBundle"',ui)


class AudioMuteTests(unittest.TestCase):
    def test_silence_survives_normalization(self):
        project=normalize({'cenas':[{'tipo':'cartoes','audio':{'muted':True,'voice_enabled':True,'voice_text':'teste'}},
                            {'tipo':'cartoes','audio':{'muted':False}}]})
        self.assertTrue(project['cenas'][0]['audio']['muted'])
        self.assertFalse(project['cenas'][1]['audio']['muted'])
        self.assertIsNone(studio_core.voice_source(project['cenas'][0],project,required=False))

    @unittest.skipUnless(bool(__import__('shutil').which('ffmpeg')),'FFmpeg unavailable')
    def test_continuous_track_is_silent_during_muted_scene(self):
        with tempfile.TemporaryDirectory() as root:
            folder=Path(root)
            audio=folder/'music.wav'
            # generate one second of 440Hz stereo PCM, 48 kHz
            import struct
            frames=bytearray()
            for i in range(48000):
                value=int(13000*math.sin(2*math.pi*440*i/48000))
                frames.extend(struct.pack('<hh',value,value))
            with wave.open(str(audio),'wb') as stream:
                stream.setframerate(48000);stream.setsampwidth(2);stream.setnchannels(2);stream.writeframes(frames)
            silence=[]
            for idx in range(2):
                path=folder/f'{idx}.wav'
                with wave.open(str(path),'wb') as stream:
                    stream.setframerate(48000);stream.setsampwidth(2);stream.setnchannels(2)
                    stream.writeframes(bytes(48000*4))
                silence.append(path)
            pr=normalize({'trilha':audio.name,'trilha_continua':True,'volume_musica':.5,
               'cenas':[{'tipo':'numero','duracao':1,'audio':{'muted':True}},
                        {'tipo':'numero','duracao':1,'audio':{'muted':False}}]})
            output=folder/'mix.wav'
            with patch.object(studio_core,'MEDIA',folder):
                studio_core.concat_audio(silence,output,pr)
            with wave.open(str(output),'rb') as result:
                self.assertEqual(result.getnframes(),96000)
                first=result.readframes(48000)
                second=result.readframes(48000)
            import struct
            def rms(data):
                count=len(data)//2
                return (sum(value*value for (value,) in struct.iter_unpack('<h',data))/max(count,1))**.5
            # silence first half (<10 PCM units) and measurable music second
            self.assertLess(rms(first),10)
            self.assertGreater(rms(second),100)


class SpatialAlpha2Tests(unittest.TestCase):
    def test_cone_and_cylinder_render(self):
        obj=normalize_spatial({'objetos':[
          {'id':'c1','tipo':'cilindro','posicao':[-1.2,0,0]},
          {'id':'c2','tipo':'cone','posicao':[1.2,0,0]},{'id':'g','tipo':'grupo'}]})
        svg=render_spatial(obj,.35,720)
        self.assertGreater(svg.count('<polygon'),8)
        self.assertEqual(svg,render_spatial(obj,.35,720))

    def test_hierarchy_changes_child_world_coordinates(self):
        base={'objetos':[
            {'id':'pai','tipo':'cubo','posicao':[0,0,0]},
            {'id':'filho','tipo':'esfera','posicao':[1,0,0],'pai':'pai'}]}
        a=render_spatial(normalize_spatial(base),.5,720)
        base['objetos'][0]['posicao']=[3,0,0]
        b=render_spatial(normalize_spatial(base),.5,720)
        self.assertNotEqual(a,b)
        self.assertIn('spg-filho',a)
        self.assertIn('spg-filho',b)

    def test_parent_cycle_and_unknown_parent_rejected(self):
        with self.assertRaisesRegex(ValueError,'ciclo'):
            normalize_spatial({'objetos':[{'id':'a','pai':'b'},{'id':'b','pai':'a'}]})
        with self.assertRaisesRegex(ValueError,'inexistente'):
            normalize_spatial({'objetos':[{'id':'a','pai':'unknown'}]})

    def test_camera_animated_at_absolute_time(self):
        s=normalize_spatial({'objetos':[{'id':'x','tipo':'cubo','posicao':[1,0,0]}],
          'animacoes':[{'alvo':'__camera__','propriedade':'azimute','inicio':0,'fim':1,
                         'de':0,'ate':180,'easing':'linear'}]})
        self.assertEqual(camera_pose(s['camera'],s['animacoes'],.5)['azimute'],90)
        a=render_spatial(s,0,1280);b=render_spatial(s,1,1280)
        self.assertNotEqual(a,b)
        self.assertEqual(render_spatial(s,.3,1280),render_spatial(s,.3,1280))

if __name__ == '__main__':unittest.main()
