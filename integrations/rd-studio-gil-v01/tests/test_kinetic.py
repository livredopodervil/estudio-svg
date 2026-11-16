import sys,tempfile,unittest,zipfile,json,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'rdstudio'))
from patches import PatchManager
class Kinetic(unittest.TestCase):
    def test_page_and_archival_manifest(self):
        archive=next((ROOT/'demo').glob('gil-gil-maquina-cinetica-*.rdpatch.zip'))
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)/'site';root.mkdir();(root/'index.html').write_text('original');(root/'data').mkdir();(root/'data/social-latest.json').write_text('bot')
            m=PatchManager(root);m.state=Path(d)/'state';m._inbox_paths=lambda:[archive.parent]
            plan=m.plan(archive.name);self.assertTrue(plan['ready']);self.assertEqual(len(plan['files']),5)
            m.apply(archive.name,'APLICAR');base=root/'projetos/gil-maquina-cinetica';c=json.loads((base/'component.json').read_text());self.assertEqual(len(c['artifacts']),4)
            for a in c['artifacts']:self.assertEqual(hashlib.sha256((base/a['path']).read_bytes()).hexdigest(),a['sha256'])
            self.assertEqual((root/'data/social-latest.json').read_text(),'bot');self.assertEqual((root/'index.html').read_text(),'original');m.remove(plan['id'],'REMOVER');self.assertFalse((base/'component.json').exists())
