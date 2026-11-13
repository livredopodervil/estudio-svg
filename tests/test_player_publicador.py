"""Regression tests for published manifests, media and integrity.
Tests inject a deterministic renderer in place of the user's unmounted checkout.
The actual Studio renderer is also exercised separately in integration smoke.
"""
import base64
import importlib.util
import json
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

MODPATH = Path(__file__).resolve().parents[1] / 'tools' / 'estudio_web_publish.py'
spec = importlib.util.spec_from_file_location('estudio_web_publish', MODPATH)
publisher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(publisher)
ONEPX = base64.b64encode(b'fake png bytes').decode('ascii')


def fake_visualize(scene, t, index, count, media, w, h):
    if scene.get('unsafe'):
        return '<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>'
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}">'
            f'<image href="data:image/png;base64,{ONEPX}" width="10" height="10"/>'
            f'<rect x="{round(t*100)}" y="15" width="20" height="10" fill="red"/></svg>')


def fake_normalize(d):
    return d


def fake_length(scene, project, voice=False):
    return scene['duracao']


class PublisherTests(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.addCleanup(self.t.cleanup)
        self.base=Path(self.t.name)
        self.project=self.base/'example.json'
        self.media=self.base/'midia'; self.media.mkdir()
        self.out=self.base/'site'
        p={'versao':'3.0.0-alpha.4','titulo':'Sono e saúde','video':{'width':720,'height':1280,'draw_fps':2},
           'cenas':[{'id':'a','tipo':'svg','duracao':1.5,'titulo':'Rotina',
                     'audio':{'voice_enabled':True,'voice_text':'Durma em horários regulares.'}},
                    {'id':'b','tipo':'svg','duracao':1,'titulo':'Ambiente',
                     'audio':{'voice_enabled':False,'voice_text':'Não ler.'}}]}
        self.project.write_text(json.dumps(p),encoding='utf8')
        modules={'graphics':types.SimpleNamespace(visualize=fake_visualize),
                 'schema':types.SimpleNamespace(normalize=fake_normalize),
                 'studio_core':types.SimpleNamespace(scene_length=fake_length)}
        self.patcher=patch.dict(sys.modules,modules)
        self.patcher.start()
        self.addCleanup(self.patcher.stop)
        self.src=publisher.Path(__file__).resolve().parents[1]

    def export(self,slug='sono'):
        return publisher.export_project(self.project,self.media,self.out,slug,video_mode='copy-mp4')

    def test_export_manifest_and_catalog(self):
        d=self.export()
        m=json.loads((d/'manifest.json').read_text())
        self.assertEqual(m['schema'],'studio.web-player/v1')
        self.assertEqual(len(m['scenes']),2)
        self.assertEqual(len(m['scenes'][0]['frames']),3)
        self.assertEqual(m['scenes'][0]['voiceText'],'Durma em horários regulares.')
        self.assertEqual(m['scenes'][1]['voiceText'],'')
        self.assertTrue((d/'index.html').is_file())
        self.assertEqual(publisher.verify_root(self.out),['sono'])

    def test_dedup_embedded_images(self):
        d=self.export(); m=json.loads((d/'manifest.json').read_text())
        self.assertEqual(len(list((d/'assets').iterdir())),1)
        for f in m['scenes'][0]['frames']:
            contents=(d/f).read_text()
            self.assertIn('../assets/',contents)
            self.assertNotIn('data:image',contents)

    def test_never_overwrites_existing_publications(self):
        self.export()
        with self.assertRaises(FileExistsError):self.export()
        self.assertEqual(publisher.verify_root(self.out),['sono'])

    def test_rejects_unsafe_slug(self):
        with self.assertRaises(ValueError):self.export('../stolen')

    def test_detects_checksum_mismatch(self):
        d=self.export()
        frame=next((d/'frames').glob('*.svg'))
        frame.write_text('tampered',encoding='utf8')
        with self.assertRaisesRegex(ValueError,'Checksum divergente'):publisher.verify_root(self.out)

    def test_rejects_script_in_visuals_and_rolls_back(self):
        p=json.loads(self.project.read_text());p['cenas'][0]['unsafe']=True
        self.project.write_text(json.dumps(p))
        with self.assertRaisesRegex(ValueError,'inseguro'):self.export()
        self.assertFalse((self.out/'apresentacoes'/'sono').exists())

    def test_catalog_multiple(self):
        self.export('a');self.export('b')
        self.assertEqual(publisher.verify_root(self.out),['a','b'])

    def test_safe_media_blocks_traversal_and_symlink(self):
        for n in ['../secret','/etc/passwd','.hidden']:
            with self.assertRaises(ValueError):publisher.safe_media(self.media,n)
        target=self.media/'real.mp4';target.write_bytes(b'mp4')
        (self.media/'alias.mp4').symlink_to(target)
        with self.assertRaises(FileNotFoundError):publisher.safe_media(self.media,'alias.mp4')

if __name__=='__main__':unittest.main()
