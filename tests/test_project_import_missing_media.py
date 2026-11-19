"""Regression tests for ZIP bundles with absent or nested images.

Uses a small schema stub to isolate the importer's file-handling contract. This
is not a substitute for end-to-end tests with the live studio schema/renderer.
"""
import contextlib
import importlib.util
import io
import json
import sys
import tempfile
import types
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from PIL import Image


class ImportMissingMediaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module_path = Path(__file__).resolve().parents[1] / 'project_import.py'

    @contextlib.contextmanager
    def importer(self):
        schema = types.ModuleType('schema')
        schema.asset = lambda x: Path(x).name
        schema.name = lambda x: x
        schema.normalize = lambda x: x
        bundle = types.ModuleType('project_bundle')
        bundle.referenced_media = lambda p: set(
            [p.get('trilha', '')] +
            [s['imagem']['arquivo'] for s in p['cenas']] +
            [s['video_clipe']['arquivo'] for s in p['cenas']] +
            [o['file'] for s in p['cenas'] for o in s.get('objetos_midia',[]) if o['kind'] != 'gil'] +
            [s['audio']['voice_file'] for s in p['cenas']] +
            [s['audio']['music_file'] for s in p['cenas']]
        ) - {''}
        with patch.dict(sys.modules, {'schema': schema, 'project_bundle': bundle}):
            spec = importlib.util.spec_from_file_location('import_zip_missing_test', self.module_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            yield module

    def scene(self, file='img.jpg'):
        return {'imagem': {'arquivo': file}, 'video_clipe': {'arquivo': ''},
                'objetos_midia': [{'kind': 'image', 'file': file}],
                'audio': {'voice_file': '', 'music_file': '', 'tracks': []}}

    def archive(self, path, scenes, images=None):
        images = images or {}
        with zipfile.ZipFile(path, 'w') as z:
            z.writestr('projeto.json', json.dumps({'trilha': '', 'cenas': scenes}))
            for filename, contents in images.items():
                z.writestr(filename, contents)

    def image(self):
        buffer = io.BytesIO()
        Image.new('RGB', (2, 2), (20, 30, 40)).save(buffer, 'JPEG')
        return buffer.getvalue()

    def test_missing_images_do_not_block_and_refs_remain(self):
        with tempfile.TemporaryDirectory() as temp, self.importer() as importer:
            root = Path(temp)
            for folder in ('projects', 'media', 'cache'): (root / folder).mkdir()
            source = root / 'source.zip'
            self.archive(source, [self.scene('img.jpg'), self.scene('img.jpg')])
            result = importer.import_zip(source, 'demo', root/'projects',root/'media',root/'cache')
            self.assertEqual(result['scenes'], 2)
            self.assertEqual(result['media'], {})
            self.assertEqual(result['missing_media'], [{'original':'img.jpg','reference':'img.jpg'}])
            saved = json.loads((root/'projects'/'demo.json').read_text())
            self.assertEqual(saved['cenas'][0]['imagem']['arquivo'], 'img.jpg')
            self.assertEqual(saved['cenas'][1]['objetos_midia'][0]['file'], 'img.jpg')

    def test_midias_folder_is_recognized(self):
        with tempfile.TemporaryDirectory() as temp, self.importer() as importer:
            root = Path(temp)
            for folder in ('projects', 'media', 'cache'): (root / folder).mkdir()
            source = root / 'source.zip'
            self.archive(source, [self.scene()], {'midias/img.jpg': self.image()})
            result = importer.import_zip(source, 'demo', root/'projects',root/'media',root/'cache')
            self.assertEqual(result['missing_media'], [])
            self.assertEqual(result['media'], {'img.jpg': 'img.jpg'})
            self.assertTrue((root/'media'/'img.jpg').exists())

    def test_missing_name_collision_does_not_bind_unrelated_media(self):
        with tempfile.TemporaryDirectory() as temp, self.importer() as importer:
            root=Path(temp)
            for folder in ('projects', 'media', 'cache'): (root/folder).mkdir()
            (root/'media'/'img.jpg').write_bytes(b'not the missing image')
            source=root/'source.zip'
            self.archive(source, [self.scene()])
            result=importer.import_zip(source, 'demo',root/'projects',root/'media',root/'cache')
            missing=result['missing_media'][0]['reference']
            self.assertNotEqual(missing,'img.jpg')
            self.assertFalse((root/'media'/missing).exists())
            self.assertEqual(json.loads((root/'projects'/'demo.json').read_text())['cenas'][0]['imagem']['arquivo'],missing)
            self.assertEqual((root/'media'/'img.jpg').read_bytes(),b'not the missing image')

    def test_mixed_missing_and_present_references(self):
        with tempfile.TemporaryDirectory() as temp, self.importer() as importer:
            root=Path(temp)
            for folder in ('projects','media','cache'): (root/folder).mkdir()
            source=root/'source.zip'
            self.archive(source,[self.scene('missing.jpg'),self.scene('present.jpg')], {'midia/present.jpg':self.image()})
            result=importer.import_zip(source,'demo',root/'projects',root/'media',root/'cache')
            self.assertEqual(result['media'],{'present.jpg':'present.jpg'})
            self.assertEqual(result['missing_media'],[{'original':'missing.jpg','reference':'missing.jpg'}])
            self.assertTrue((root/'media'/'present.jpg').is_file())
            self.assertFalse((root/'media'/'missing.jpg').exists())


if __name__ == '__main__':
    unittest.main()
