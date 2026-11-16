"""Testes offline: python -m unittest discover -s tests -v"""
import base64
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from server import Studio, StudioError


class StudioTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / 'site'
        self.root.mkdir()
        (self.root / 'index.html').write_text('''<!doctype html><html><head>
        <meta property="og:title" content="Site">
        <meta property="og:description" content="Descrição">
        <meta property="og:url" content="https://rogerioduarte.org/">
        <meta property="og:image" content="https://rogerioduarte.org/assets/og.jpg">
        </head><body><a href="/projetos/demo/">Demo</a></body></html>''', encoding='utf8')
        (self.root / 'assets').mkdir()
        (self.root / 'assets/og.jpg').write_bytes(b'\xff\xd8\xfftest')
        (self.root / 'projetos/demo').mkdir(parents=True)
        (self.root / 'projetos/demo/index.html').write_text('<h1>demo</h1>', encoding='utf8')
        self.studio = Studio(self.root, 8765, 8766)
        self.studio.history_root = Path(self.temp.name) / 'historico'

    def tearDown(self):
        self.temp.cleanup()

    def test_validation_and_local_absolute_links(self):
        r = self.studio.validate()
        self.assertEqual(r['errors'], [], r)
        self.assertTrue(all('modules/manifest.json' in warning for warning in r['warnings']),r)

    def test_file_save_conflict_and_history(self):
        old = self.studio.text_read('index.html')
        saved = self.studio.save_text({'path':'index.html','content':old['content']+'\n<!-- edição -->','expected_sha256':old['sha256']})
        self.assertNotEqual(saved['sha256'],old['sha256'])
        self.assertEqual(len(self.studio.history('index.html')),1)
        with self.assertRaises(StudioError) as ctx:
            self.studio.save_text({'path':'index.html','content':'invalido','expected_sha256':old['sha256']})
        self.assertEqual(ctx.exception.status,409)
        self.studio.restore({'path':'index.html','id':self.studio.history('index.html')[0]['id'],'expected_sha256':saved['sha256']})
        self.assertEqual(self.studio.text_read('index.html')['content'],old['content'])

    def test_dangerous_paths_and_symlinks(self):
        for p in ('../secret','/etc/passwd','.git/config','assets/../index.html','/tmp/../etc/passwd'):
            with self.assertRaises(StudioError, msg=p):
                self.studio.resolve(p, allow_missing=True)
        out = Path(self.temp.name) / 'outside'
        out.mkdir()
        (self.root / 'symlink').symlink_to(out, target_is_directory=True)
        with self.assertRaises(StudioError):
            self.studio.resolve('symlink/demo.txt', allow_missing=True)

    def test_json_validation(self):
        with self.assertRaises(StudioError):
            self.studio.save_text({'path':'dados.json','content':'{não json','expected_sha256':None})
        self.studio.save_text({'path':'dados.json','content':'{"ok": true}','expected_sha256':None})
        self.assertTrue((self.root / 'dados.json').is_file())

    def test_catalog_and_custom_fields_preserved(self):
        self.studio.init_catalog()
        self.assertTrue((self.root / 'catalog/edges.json').is_file())
        d={'id':'spatialseed','title':'SpatialSeed','summary':'Teste','status':'publicado','category':'computacao','url':'https://example.org','preview':'','color':'#123456','topics':['3d'],'neighbors':[],'expected_sha256':None}
        r=self.studio.catalog_save(d)
        self.assertEqual(self.studio.catalog()['projects'][0]['id'],'spatialseed')
        f=self.root/'catalog/projects/spatialseed.json';v=json.loads(f.read_text());v['source']='https://example.org/code';f.write_text(json.dumps(v))
        d['expected_sha256']=self.studio.text_read('catalog/projects/spatialseed.json')['sha256']
        self.studio.catalog_save(d)
        self.assertEqual(json.loads(f.read_text())['source'],'https://example.org/code')
        self.assertEqual(self.studio.validate()['errors'],[])

    def test_bad_catalog_url_rejected(self):
        d={'id':'x','title':'X','summary':'', 'status':'rascunho', 'url':'javascript:alert(1)'}
        with self.assertRaises(StudioError):
            self.studio.catalog_save(d)

    def test_image_upload_signature(self):
        payload=base64.b64encode(b'\x89PNG\r\n\x1a\nTEST').decode()
        self.studio.asset_upload({'path':'assets/previews/a.png','base64':payload,'expected_sha256':None})
        self.assertTrue((self.root/'assets/previews/a.png').is_file())
        info=self.studio.media_info('assets/previews/a.png')
        self.assertTrue(info['exists'])
        new=base64.b64encode(b'\x89PNG\r\n\x1a\nREPLACED').decode()
        self.studio.asset_upload({'path':'assets/previews/a.png','base64':new,'expected_sha256':info['sha256']})
        self.assertEqual(len(self.studio.history('assets/previews/a.png')),1)
        with self.assertRaises(StudioError):
            self.studio.asset_upload({'path':'assets/previews/b.jpg','base64':payload,'expected_sha256':None})
        with self.assertRaises(StudioError):
            self.studio.asset_upload({'path':'hack.py','base64':payload,'expected_sha256':None})

    def test_git_commit_requires_validation_and_does_not_push(self):
        for command in (["git","init","-q"],["git","config","user.email","local@example.org"],["git","config","user.name","Test Local"]):
            subprocess.check_call(command,cwd=self.root)
        subprocess.check_call(['git','add','index.html','assets/og.jpg','projetos/demo/index.html'],cwd=self.root)
        subprocess.check_call(['git','commit','-qm','baseline'],cwd=self.root)
        old=self.studio.text_read('index.html')
        self.studio.save_text({'path':'index.html','content':old['content']+'<!--test-->','expected_sha256':old['sha256']})
        self.studio.stage(['index.html'])
        with self.assertRaises(StudioError):
            self.studio.commit({'message':'feat: update content','confirm':'COMMIT'})
        self.assertFalse(self.studio.validate()['errors'])
        result=self.studio.commit({'message':'feat: update content','confirm':'COMMIT'})
        self.assertIn('Commit local',result['message'])
        self.assertEqual(subprocess.check_output(['git','log','-1','--format=%s'],cwd=self.root,text=True).strip(),'feat: update content')


if __name__ == '__main__':
    unittest.main()
