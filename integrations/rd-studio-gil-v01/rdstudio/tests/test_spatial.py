"""Tests for spatial editor on a reduced fixture, without network or GitHub."""
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from server import Studio, StudioError
from spatial import ENGINE_MARKER

class TestSpatial(unittest.TestCase):
 def setUp(self):
  self.t=tempfile.TemporaryDirectory();self.root=Path(self.t.name)
  (self.root/'modules').mkdir();(self.root/'js').mkdir();(self.root/'catalog/projects').mkdir(parents=True)
  (self.root/'projetos/tarefas-unicode').mkdir(parents=True)
  (self.root/'projetos/tarefas-unicode/index.html').write_text('<title>Tarefas</title>')
  (self.root/'index.html').write_text('<a href="#projetos">Projetos</a>')
  (self.root/'modules/nucleo.js').write_text("export default {id:'nucleo',name:'Núcleo',position:[0,0,0],menu:new Array(12).fill('Início')};\n")
  (self.root/'modules/sistemas.js').write_text("export default {id:'sistemas',position: [ 9, 7, -10 ],menu:new Array(12).fill('Sistemas')};\n")
  (self.root/'modules/manifest.json').write_text(json.dumps({'schemaVersion':1,'modules':[{'id':'nucleo','src':'./modules/nucleo.js'},{'id':'sistemas','src':'./modules/sistemas.js'}],'links':[['nucleo','sistemas']]}))
  (self.root/'catalog/projects/tarefas-unicode.json').write_text(json.dumps({'id':'tarefas-unicode','title':'Tarefas Unicode','summary':'Lista de tarefas','status':'publicado','category':'Ferramentas','url':'/projetos/tarefas-unicode/','preview':''}))
  self.s=Studio(self.root,8875,8876);self.op=self.s.spatial
 def tearDown(self):self.t.cleanup()
 def test_graph_position(self):
  overview=self.op.overview()
  with self.assertRaises(StudioError):self.op.save_links({'links':[['nucleo','desconhecido']],'expected_sha256':overview['manifest_sha'],'confirm':'SALVAR GRAFO'})
  self.assertEqual(self.op.save_links({'links':[],'expected_sha256':overview['manifest_sha'],'confirm':'SALVAR GRAFO'})['links'],[])
  a=self.s.text_read('modules/sistemas.js');self.op.save_position({'id':'sistemas','position':[2,3,-4],'expected_sha256':a['sha256']})
  self.assertEqual(self.op.overview()['nodes'][1]['position'],[2,3,-4])
  with self.assertRaises(StudioError):self.op.save_position({'id':'sistemas','position':[1,1,1],'expected_sha256':a['sha256']})
 def test_portfolio_integrates(self):
  r=self.op.expose({'destination':'spatial','confirm':'INTEGRAR'})
  self.assertEqual(r['faces'],12)
  m=json.loads((self.root/'modules/manifest.json').read_text())
  self.assertTrue(any(x['id']=='portfolio' for x in m['modules']))
  self.assertIn(['nucleo','portfolio'],m['links'])
  a=(self.root/'modules/portfolio.js').read_text();self.assertIn('tarefas-unicode',a)
  for i in range(1,13):self.assertTrue((self.root/f'assets/modules/portfolio/face-{i:02}.svg').is_file())
  # Reapply does not add duplicate nodes/links.
  self.op.expose({'destination':'spatial','confirm':'INTEGRAR'})
  m=json.loads((self.root/'modules/manifest.json').read_text())
  self.assertEqual(sum(x['id']=='portfolio' for x in m['modules']),1)
 def test_portfolio_does_not_overwrite_manual_module(self):
  (self.root/'modules/portfolio.js').write_text('export default {}')
  with self.assertRaises(StudioError):self.op.expose({'destination':'spatial','confirm':'INTEGRAR'})
 def test_settings_reject_unsupported_engine(self):
  (self.root/'js/site-v10.js').write_text('const ok=true;')
  o=self.op.overview();self.assertFalse(o['adapter_supported'])
  with self.assertRaises(StudioError):self.op.save_settings({'settings':o['settings'],'expected_sha256':o['settings_sha'],'confirm':'APLICAR CENA'})
  self.assertFalse((self.root/'config/spatial.json').exists())
if __name__=='__main__':unittest.main()
