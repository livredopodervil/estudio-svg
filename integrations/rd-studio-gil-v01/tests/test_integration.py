import sys,tempfile,unittest,zipfile,json,hashlib,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'rdstudio'))
from patches import PatchManager,PatchError
class Integration(unittest.TestCase):
    def test_demo_apply_remove(self):
        archive=next((ROOT/'demo').glob('gil-gil-timeline-v01-*.rdpatch.zip'))
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)/'site';root.mkdir();(root/'index.html').write_text('original')
            m=PatchManager(root);m.state=Path(d)/'state';m._inbox_paths=lambda:[archive.parent]
            plan=m.plan(archive.name);self.assertTrue(plan['ready']);self.assertEqual(len(plan['files']),4)
            m.apply(archive.name,'APLICAR');self.assertEqual((root/'index.html').read_text(),'original')
            self.assertFalse(m.plan(archive.name)['ready'])
            for item in plan['files']:
                self.assertEqual(hashlib.sha256((root/item['path']).read_bytes()).hexdigest(),item['after'])
            m.remove(plan['id'],'REMOVER');self.assertTrue(all(not (root/i['path']).exists() for i in plan['files']))
    def test_original_code_unchanged_except_tab(self):
        rows=(ROOT/'integration/RD442-SHA256SUMS.txt').read_text().splitlines();modified=[]
        for row in rows:
            h,name=row.split('  ',1)
            if hashlib.sha256((ROOT/'rdstudio'/name).read_bytes()).hexdigest()!=h:modified.append(name)
        self.assertEqual(sorted(modified),['web/app.js','web/index.html','web/spatial.js','web/style.css'])
        html=(ROOT/'rdstudio/web/index.html').read_text();js=(ROOT/'rdstudio/web/app.js').read_text()
        self.assertIn('id="tab-multimedia"',html);self.assertIn("multimedia:'Multimídia'",js);self.assertIn('127.0.0.1:8791/',html)
if __name__=='__main__':unittest.main()
