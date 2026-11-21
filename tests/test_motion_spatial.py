import json
import tempfile
import unittest
import zipfile
from hashlib import sha256
from pathlib import Path
from unittest.mock import patch
import xml.etree.ElementTree as ET

import app
from spatialseed_sources import store_spatialseed_files
from graphics import visualize
from project_bundle import bundle_to_file
from project_import import import_zip
from schema import normalize

DEMO = Path(__file__).resolve().parents[1] / 'examples/motion_spatial.json'


class MotionSpatial(unittest.TestCase):
    def setUp(self):
        self.doc = normalize(json.loads(DEMO.read_text()))

    def test_reopen_and_bundle_restore_native_bytes(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            with patch.object(app, 'PROJECTS', root):
                app.save_project('origem', self.doc)
                opened = app.read_project('origem')
                data = opened['cenas'][0]['spatialseed_viewport']['source'].encode()
                filename = sha256(data).hexdigest() + '.spatialseed'
                sidecar = root / 'spatialseed' / filename
                self.assertEqual(sidecar.read_bytes(), data)
                bundle_to_file('origem', opened, root, root / 'demo.zip')
                with zipfile.ZipFile(root / 'demo.zip') as archive:
                    self.assertEqual(archive.read('spatialseed/' + filename), data)
                sidecar.unlink()
                import_zip(root / 'demo.zip', 'copia', root, root, root)
                self.assertEqual(app.read_project('copia'), opened)
                self.assertEqual(sidecar.read_bytes(), data)
                sidecar.write_bytes(b'edited')
                with self.assertRaises(ValueError):
                    app.save_project('novo', self.doc)
                self.assertFalse((root / 'novo.json').exists())
                self.assertEqual(sidecar.read_bytes(), b'edited')

    def test_without_hard_links_and_concurrent_writers(self):
        from concurrent.futures import ThreadPoolExecutor
        import os
        with tempfile.TemporaryDirectory() as folder:
            link = getattr(os, 'link', None)
            if link is not None:
                del os.link
                self.addCleanup(setattr, os, 'link', link)
            with ThreadPoolExecutor(max_workers=6) as pool:
                list(pool.map(lambda _: store_spatialseed_files(folder, self.doc), range(24)))
            files = list((Path(folder) / 'spatialseed').iterdir())
            self.assertEqual(len(files), 1)
            self.assertEqual(files[0].read_bytes(), self.doc['cenas'][0]['spatialseed_viewport']['source'].encode())

    def test_failed_publication_cleans_stage_and_can_retry(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch.object(Path, 'replace', side_effect=OSError('falha simulada')):
                with self.assertRaisesRegex(OSError, 'simulada'):
                    store_spatialseed_files(folder, self.doc)
            self.assertEqual(list((Path(folder) / 'spatialseed').iterdir()), [])
            store_spatialseed_files(folder, self.doc)
            self.assertEqual(len(list((Path(folder) / 'spatialseed').glob('*.spatialseed'))), 1)

    def test_seek_and_transparent_overlay_at_both_aspects(self):
        scene = self.doc['cenas'][0]
        for w,h in ((640,360),(360,640)):
            def render(t):
                return visualize(scene,t/scene['duracao'],width=w,height=h)
            a=render(.12)
            self.assertNotEqual(a, render(1.3))
            self.assertEqual(a, render(.12))
            root=ET.fromstring(a)
            self.assertIsNone(root.find("{*}rect[@fill='url(#wash)']"))
            for track in scene['animacoes']:
                self.assertIsNotNone(root.find(".//*[@id='%s']" % track['alvo']))
            self.assertIn('url(#wash)',visualize({**scene,'spatialseed_viewport':{}},width=w,height=h))
