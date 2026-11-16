import json
import os
from pathlib import Path
import tempfile
import unittest
import sys
sys.path.insert(0,str(Path(__file__).parent.parent))
from discovery import Discovery
from server import Studio, StudioError


class DiscoveryTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.home=Path(self.tmp.name)
        self.repo=self.home/'repo';self.repo.mkdir()
        (self.repo/'index.html').write_text('<html><title>site</title></html>')
        self.studio=Studio(self.repo,12340,12341)
        self.d=Discovery(self.studio,StudioError)
        self.d.home=self.home
        self.d.backups=self.home/'safe-backups'
        self.v1=self.home/'App-v1'
        self.v2=self.home/'App-v2'
        for p,v in [(self.v1,'um'),(self.v2,'dois')]:
            p.mkdir()
            (p/'index.html').write_text(f'<html><head><title>Meu site {v}</title></head><body>{v}</body></html>')
            (p/'app.js').write_text(f'const valor={v!r};')
        (self.v2/'novo.css').write_text('body{color:blue;}')
    def tearDown(self):self.tmp.cleanup()
    def test_browse_privacy(self):
        (self.home/'.ssh').mkdir()
        (self.home/'.ssh'/'id_ed25519').write_text('private')
        (self.home/'openlink').symlink_to(self.home/'.ssh',target_is_directory=True)
        listing=self.d.browse()
        names=[x['name'] for x in listing['items']]
        self.assertIn('App-v1',names)
        self.assertNotIn('.ssh',names)
        self.assertNotIn('openlink',names)
        with self.assertRaises(StudioError):self.d.browse(str(self.home/'.ssh'))
        with self.assertRaises(StudioError):self.d.browse(str(self.home/'openlink'))
        with self.assertRaises(StudioError):self.d.browse('/etc')
    def test_scan_versions(self):
        r=self.d.scan({'root':str(self.home),'depth':3})
        names={c['name'] for c in r['candidates']}
        self.assertTrue({'App-v1','App-v2'}.issubset(names))
        versions={c['name']:c['group'] for c in r['candidates']}
        self.assertEqual(versions['App-v1'],versions['App-v2'])
    def test_compare(self):
        r=self.d.compare({'a':str(self.v1),'b':str(self.v2)})
        self.assertIn('novo.css',r['added'])
        self.assertIn('index.html',r['changed'])
        self.assertIn('app.js',r['changed'])
        self.assertIn('-const valor',r['diff']) if r['focus']=='app.js' else self.assertTrue(r['diff'])
    def test_replace_and_backup(self):
        target=self.repo/'projetos'/'app';target.mkdir(parents=True)
        (target/'index.html').write_text('<html>velho</html>')
        (target/'apagar.js').write_text('velho')
        plan=self.d.replacement_plan({'id':'app','source':str(self.v2)})
        self.assertIn('apagar.js',plan['removed'])
        with self.assertRaises(StudioError):self.d.replacement_apply({**plan,'confirm':'OUTRO'})
        result=self.d.replacement_apply({**plan,'confirm':'SUBSTITUIR app'})
        self.assertTrue(Path(result['backup']).joinpath('index.html').is_file())
        self.assertEqual((target/'index.html').read_text(),(self.v2/'index.html').read_text())
        self.assertFalse((target/'apagar.js').exists())
        self.assertTrue((target/'novo.css').exists())
    def test_visuals_and_catalog(self):
        target=self.repo/'projetos'/'app';target.mkdir(parents=True)
        (target/'index.html').write_text('<html><head><title>Aplicativo 3D</title></head></html>')
        self.studio.init_catalog()
        self.studio.catalog_save({'id':'app','title':'Aplicativo 3D','status':'rascunho','category':'teste','url':'/projetos/app/','expected_sha256':None})
        plan=self.d.visual_plan({'id':'app'})
        self.assertEqual(plan['default'],'')
        with self.assertRaises(StudioError):self.d.visuals_apply({'id':'app','confirm':'OUTRO'})
        r=self.d.visuals_apply({'id':'app','confirm':'GERAR','source':''})
        for rel in r['generated']:self.assertTrue((self.repo/rel.lstrip('/')).is_file())
        rec=json.loads((self.repo/'catalog/projects/app.json').read_text())
        self.assertEqual(rec['preview'],r['generated'][0]);self.assertEqual(rec['status'],'rascunho')
    def test_running_safe(self):
        r=self.d.running()
        self.assertIsInstance(r['ports'],list)
        self.assertIsInstance(r['processes'],list)

if __name__=='__main__':unittest.main()

class PublicPortfolioTest(unittest.TestCase):
    def test_portfolio_generates_selected_catalog(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)/'site';root.mkdir()
            (root/'index.html').write_text('<nav><a href="#projetos">Projetos</a></nav>')
            (root/'projetos/telemedicina').mkdir(parents=True)
            (root/'projetos/telemedicina/index.html').write_text('ok')
            st=Studio(root,8972,8973); d=Discovery(st,StudioError);d.home=Path(t)
            st.init_catalog()
            st.catalog_save({'id':'teste','title':'Exemplo de página','status':'demonstracao','summary':'<script>alert(1)</script>',
                             'url':'/projetos/teste/','expected_sha256':None})
            st.catalog_save({'id':'privado','title':'Rascunho privado','status':'rascunho',
                             'url':'/projetos/privado/','expected_sha256':None})
            r=d.portfolio_generate({'confirm':'GERAR PORTFOLIO','link_home':True})
            page=(root/'projetos/index.html').read_text()
            self.assertTrue(r['linked_home'])
            self.assertIn('Exemplo de página',page)
            self.assertIn('Telemedicina',page)
            self.assertNotIn('Rascunho privado',page)
            self.assertNotIn('<script>alert(1)</script>',page)
            self.assertIn('Portfólio', (root/'index.html').read_text())
            d.portfolio_generate({'confirm':'GERAR PORTFOLIO','link_home':True})
            self.assertEqual((root/'index.html').read_text().count('<a href="./projetos/">Portfólio</a>'),1)
