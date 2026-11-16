"""Git release and snapshot rollback, using an isolated local bare remote."""
import tempfile
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from server import Studio, StudioError

def git(root,*args):
 return subprocess.check_output(['git',*args],cwd=root,text=True,stderr=subprocess.STDOUT).strip()

class PublishWizard(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();home=Path(self.tmp.name)
  remote=home/'remote.git';remote.mkdir();git(remote,'init','--bare','-q','--initial-branch=main')
  self.remote=remote
  repo=home/'work';repo.mkdir();self.repo=repo
  git(repo,'init','-q','--initial-branch=main')
  git(repo,'config','user.name','Tester');git(repo,'config','user.email','tester@localhost')
  (repo/'index.html').write_text('<!doctype html><title>Original</title>')
  git(repo,'add','.');git(repo,'commit','-qm','initial')
  git(repo,'remote','add','origin',str(remote));git(repo,'push','-q','-u','origin','main')
  git(repo,'switch','-q','-c','studio/v4-test')
  self.original=git(repo,'rev-parse','HEAD');self.studio=Studio(repo,8875,8876)
 def tearDown(self):self.tmp.cleanup()
 def test_publish_backup_and_revert(self):
  (self.repo/'index.html').write_text('<!doctype html><title>Atualizado</title>')
  self.studio.validate()
  with patch.object(self.studio,'_remote',return_value='https://github.com/test/sample.git'):
   plan=self.studio.spatial.publish_plan()
   self.assertEqual(len(plan['files']),1)
   with self.assertRaises(StudioError):
    self.studio.spatial.publish_apply({'confirm':'PUBLICAR','expected_head':plan['head'],'expected_remote':plan['remote'],
                                    'expected_fingerprint':'invalid','paths':['index.html'],'message':'feat(site): changed'})
   result=self.studio.spatial.publish_apply({'confirm':'PUBLICAR','expected_head':plan['head'],'expected_remote':plan['remote'],
                                    'expected_fingerprint':plan['fingerprint'],'paths':['index.html'],'message':'feat(site): update page'})
   self.assertTrue(result['published']);tag=result['backup_tag']
   self.assertEqual(git(self.remote,'rev-parse',tag),self.original)
   self.assertNotEqual(git(self.remote,'rev-parse','refs/heads/main'),self.original)
   backup=self.studio.spatial.restore_fetch()
   self.assertIn(tag,[x['tag'] for x in backup['tags']])
   result=self.studio.spatial.restore_apply({'confirm':'REVERTER','expected_remote':backup['status']['remote'],'tag':tag})
   self.assertTrue(result['published'])
   self.assertIn('Original',(self.repo/'index.html').read_text())
   self.assertEqual(git(self.remote,'show','main:index.html'), '<!doctype html><title>Original</title>')
 def test_publish_accepts_pre_staged_selected_file(self):
  (self.repo/'index.html').write_text('<!doctype html><title>Staged</title>')
  git(self.repo,'add','index.html')
  self.studio.validate()
  with patch.object(self.studio,'_remote',return_value='https://github.com/test/sample.git'):
   plan=self.studio.spatial.publish_plan()
   self.assertEqual([x['path'] for x in plan['files']],['index.html'])
   result=self.studio.spatial.publish_apply({'confirm':'PUBLICAR','expected_head':plan['head'],
     'expected_remote':plan['remote'],'expected_fingerprint':plan['fingerprint'],
     'paths':['index.html'],'message':'fix(site): publicar arquivo preparado'})
  self.assertTrue(result['published'])
  self.assertIn('Staged',git(self.remote,'show','main:index.html'))
  self.assertEqual(git(self.repo,'status','--porcelain'),'')

 def test_publish_accepts_new_pre_staged_file(self):
  (self.repo/'novo.html').write_text('<!doctype html><title>Novo</title>')
  git(self.repo,'add','novo.html')
  self.studio.validate()
  with patch.object(self.studio,'_remote',return_value='https://github.com/test/sample.git'):
   plan=self.studio.spatial.publish_plan()
   result=self.studio.spatial.publish_apply({'confirm':'PUBLICAR','expected_head':plan['head'],
     'expected_remote':plan['remote'],'expected_fingerprint':plan['fingerprint'],
     'paths':['novo.html'],'message':'feat(site): adicionar pagina nova'})
  self.assertTrue(result['published'])
  self.assertIn('Novo',git(self.remote,'show','main:novo.html'))

 def test_rejects_unselected_pre_staged_without_changes(self):
  (self.repo/'index.html').write_text('<!doctype html><title>Selecionado</title>')
  (self.repo/'outro.html').write_text('<!doctype html><title>Não selecionado</title>')
  git(self.repo,'add','outro.html')
  self.studio.validate()
  with patch.object(self.studio,'_remote',return_value='https://github.com/test/sample.git'):
   plan=self.studio.spatial.publish_plan()
   with self.assertRaisesRegex(StudioError,'NÃO selecionados'):
    self.studio.spatial.publish_apply({'confirm':'PUBLICAR','expected_head':plan['head'],
     'expected_remote':plan['remote'],'expected_fingerprint':plan['fingerprint'],
     'paths':['index.html'],'message':'fix(site): publicar selecionado'})
  self.assertEqual(git(self.repo,'rev-parse','HEAD'),self.original)
  self.assertEqual(git(self.remote,'rev-parse','main'),self.original)
  self.assertEqual(git(self.repo,'diff','--cached','--name-only'),'outro.html')
  self.assertIn('Selecionado',(self.repo/'index.html').read_text())

 def test_cannot_publish_without_validation(self):
  (self.repo/'index.html').write_text('change')
  with patch.object(self.studio,'_remote',return_value='https://github.com/test/sample.git'):
   with self.assertRaises(StudioError):self.studio.spatial.publish_plan()

if __name__=='__main__':unittest.main()
