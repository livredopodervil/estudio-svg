import sys, tempfile, unittest, json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from studio_project_ops import rename_project
class Tests(unittest.TestCase):
    def test_rename_preserves_bytes_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as x:
            root=Path(x); raw=b'{"titulo":"exemplo","cenas":[]}'
            (root/'old.json').write_bytes(raw)
            self.assertEqual(rename_project(root,'old','novo'),'novo')
            self.assertFalse((root/'old.json').exists());self.assertEqual((root/'novo.json').read_bytes(),raw)
            (root/'old.json').write_bytes(b'outro')
            with self.assertRaisesRegex(ValueError,'Nome j'):
                rename_project(root,'old','novo')
    def test_archive_conflict(self):
        with tempfile.TemporaryDirectory() as x:
            r=Path(x);(r/'old.json').write_bytes(b'{}');(r/'.arquivados').mkdir();(r/'.arquivados'/'novo.json').write_bytes(b'{}')
            with self.assertRaises(ValueError):rename_project(r,'old','novo')
            self.assertTrue((r/'old.json').exists())
    def test_invalid_identifiers(self):
        with tempfile.TemporaryDirectory() as x:
            r=Path(x);(r/'old.json').write_bytes(b'{}')
            for s in ('../evil','espaco livre','ç',''):
                with self.assertRaises(ValueError):rename_project(r,'old',s)
            self.assertTrue((r/'old.json').exists())
if __name__=='__main__':unittest.main()
