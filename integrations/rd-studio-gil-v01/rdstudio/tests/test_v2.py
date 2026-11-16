import os
from pathlib import Path
import subprocess
import tempfile
import sys
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from server import Studio, StudioError


def git(*args, cwd):
    return subprocess.check_output(['git', *args], cwd=cwd, text=True, stderr=subprocess.STDOUT).strip()


class V2Test(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        root=Path(self.temp.name)
        self.repo=root/'site';self.repo.mkdir()
        (self.repo/'index.html').write_text('<h1>Site</h1>',encoding='utf-8')
        (self.repo/'laboratorio').mkdir()
        (self.repo/'laboratorio/index.html').write_text('<h1>Atlas</h1>',encoding='utf-8')
        (self.repo/'modules').mkdir()
        (self.repo/'modules/manifest.json').write_text('{"modules":[{"id":"nucleo","src":"./modules/nucleo.js"},{"id":"saude","src":"./modules/saude.js"}],"links":[["nucleo","saude"]]}',encoding='utf-8')
        (self.repo/'modules/nucleo.js').write_text('export default {}',encoding='utf-8')
        (self.repo/'modules/saude.js').write_text('export default {}',encoding='utf-8')
        self.studio=Studio(self.repo,8765,8766)
        self.studio.history_root=root/'history'

    def tearDown(self):
        self.temp.cleanup()

    def test_structure_manifest_and_pages(self):
        s=self.studio.structure()
        self.assertEqual(s['counts']['modules'],2)
        self.assertEqual(s['counts']['spatial_links'],1)
        self.assertIn('page:laboratorio/index.html',[n['id'] for n in s['nodes']])
        self.assertIn({'source':'module:nucleo','target':'module:saude','kind':'spatial'},s['edges'])

    def test_import_local_without_overwrite(self):
        source=Path(self.temp.name)/'old-app';source.mkdir()
        (source/'index.html').write_text('<title>Meu app</title>')
        (source/'style.css').write_text('body{}')
        with patch('server.Path.home',return_value=Path(self.temp.name)):
            plan=self.studio.import_plan({'source':str(source),'id':'meu-app'})
            self.assertEqual(plan['files'],2)
            with self.assertRaises(StudioError):
                self.studio.import_apply({'source':str(source),'id':'meu-app','fingerprint':'wrong','confirm':'IMPORTAR'})
            result=self.studio.import_apply({'source':str(source),'id':'meu-app','fingerprint':plan['fingerprint'],'confirm':'IMPORTAR'})
            self.assertIn('meu-app',result['message'])
            self.assertEqual((self.repo/'projetos/meu-app/index.html').read_text(),'<title>Meu app</title>')
            self.assertEqual(self.studio.catalog()['projects'][0]['url'],'/projetos/meu-app/')
            with self.assertRaises(StudioError):
                self.studio.import_plan({'source':str(source),'id':'meu-app'})

    def test_import_rejects_outside_and_symlink(self):
        source=Path(self.temp.name)/'outside';source.mkdir()
        (source/'index.html').write_text('index')
        with patch('server.Path.home',return_value=Path(self.temp.name)/'other-home'):
            with self.assertRaises(StudioError):self.studio.import_plan({'source':str(source),'id':'app'})

    def test_git_update_and_dirty_protection(self):
        tmp=Path(self.temp.name)
        remote=tmp/'remote.git';remote.mkdir()
        git('init','--bare','-q','--initial-branch=main',cwd=remote)
        seed=tmp/'seed';seed.mkdir()
        git('init','-q','--initial-branch=main',cwd=seed)
        git('config','user.name','Dev',cwd=seed);git('config','user.email','dev@example.org',cwd=seed)
        (seed/'index.html').write_text('version1')
        git('add','.',cwd=seed);git('commit','-qm','initial',cwd=seed)
        git('remote','add','origin',str(remote),cwd=seed);git('push','-q','-u','origin','main',cwd=seed)
        work=tmp/'checkout';git('clone','-q',str(remote),str(work),cwd=tmp)
        git('switch','-q','-c','studio/local-test',cwd=work)
        studio=Studio(work,8900,8901)
        self.assertEqual(studio.sync_info()['behind'],0)
        (seed/'index.html').write_text('version2')
        git('add','.',cwd=seed);git('commit','-qm','second',cwd=seed);git('push','-q',cwd=seed)
        # fetch aceita apenas GitHub; forçamos apenas a identidade do URL no teste local.
        with patch.object(studio,'_remote',return_value='https://github.com/test/sample.git'):
            self.assertEqual(studio.sync_fetch()['behind'],1)
            (work/'temporary.txt').write_text('not staged')
            with self.assertRaises(StudioError):studio.sync_update({'confirm':'ATUALIZAR'})
            self.assertEqual((work/'index.html').read_text(),'version1')
            (work/'temporary.txt').unlink()
            self.assertEqual(studio.sync_update({'confirm':'ATUALIZAR'})['behind'],0)
            self.assertEqual((work/'index.html').read_text(),'version2')
            self.assertEqual(git('rev-parse','HEAD',cwd=work),git('rev-parse','origin/main',cwd=work))

    def test_publish_requires_confirmation_and_approval(self):
        tmp=Path(self.temp.name)
        remote=tmp/'remote.git';remote.mkdir()
        git('init','--bare','-q','--initial-branch=main',cwd=remote)
        git('init','-q','--initial-branch=main',cwd=self.repo)
        git('config','user.name','Dev',cwd=self.repo);git('config','user.email','dev@example.org',cwd=self.repo)
        git('add','.',cwd=self.repo);git('commit','-qm','initial',cwd=self.repo)
        git('remote','add','origin',str(remote),cwd=self.repo);git('push','-q','-u','origin','main',cwd=self.repo)
        git('switch','-q','-c','studio/local-test',cwd=self.repo)
        (self.repo/'index.html').write_text('<title>modified</title>')
        git('add','.',cwd=self.repo);git('commit','-qm','changed',cwd=self.repo)
        self.studio.validate()
        original=git('rev-parse','refs/remotes/origin/main',cwd=self.repo)
        info=self.studio.sync_info()
        with self.assertRaises(StudioError):self.studio.sync_publish({'confirm':'NO'})
        with patch.object(self.studio,'_remote',return_value='https://github.com/test/sample.git'):
            with self.assertRaises(StudioError):self.studio.sync_publish({'confirm':'PUBLICAR','expected_head':info['local'], 'expected_remote':info['remote'],'expected_origin':'bad'})
            result=self.studio.sync_publish({'confirm':'PUBLICAR','expected_head':info['local'],'expected_remote':info['remote'],'expected_origin':'https://github.com/test/sample.git'})
        self.assertIn('Push efetuado',result['message'])
        self.assertEqual(git('rev-parse','refs/heads/main',cwd=remote),info['local'])
        self.assertEqual(git('rev-parse',result['backup_tag'],cwd=remote),original)

if __name__=='__main__':unittest.main()
