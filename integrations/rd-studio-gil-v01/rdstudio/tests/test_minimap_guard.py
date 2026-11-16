"""Evita regressão da miniatura durante publicação e testa reparo local."""
import sys
import tempfile
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from server import Studio, StudioError
from test_mini_sync import MOCK

class Guard(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.root=Path(self.tmp.name)
        (self.root/'js').mkdir()
        (self.root/'laboratorio').mkdir()
        (self.root/'laboratorio/index.html').write_text('laboratorio',encoding='utf8')
        (self.root/'index.html').write_text('inicio',encoding='utf8')
        self.studio=Studio(self.root,8875,8876)
        self.script=self.root/'js/site-v10.js'
    def tearDown(self):self.tmp.cleanup()
    def test_blocks_remote_feature_loss(self):
        self.script.write_text('const mini=true;',encoding='utf8')
        self.studio._git_run=lambda args,timeout=15:'/* RD-STUDIO-MINI-SYNC-V1 */\n'+MOCK
        with self.assertRaisesRegex(StudioError,'REGRESSÃO BLOQUEADA'):
            self.studio.spatial._miniature_publication_guard()
    def test_repair_and_repeat(self):
        self.script.write_text(MOCK,encoding='utf8')
        res=self.studio.spatial.repair_minimap({'confirm':'REPARAR MINIATURA'})
        self.assertTrue(res['changed'])
        self.assertIn('RD-STUDIO-MINI-SYNC-V1',self.script.read_text())
        res=self.studio.spatial.repair_minimap({'confirm':'REPARAR MINIATURA'})
        self.assertFalse(res['changed'])
        self.studio._git_run=lambda args,timeout=15:self.script.read_text()
        self.studio.spatial._miniature_publication_guard()
    def test_blocks_broken_editorial_engine(self):
        self.script.write_text(MOCK,encoding='utf8')
        (self.root/'modules').mkdir()
        (self.root/'modules/content-pages.js').write_text('export default {};')
        self.studio._git_run=lambda args,timeout=15:MOCK
        with self.assertRaisesRegex(StudioError,'conteúdo editorial'):
            self.studio.spatial._miniature_publication_guard()
if __name__=='__main__':unittest.main()
