"""HTTP regression: execute exact Handler.do_GET without importing optional app modules."""
import ast
from pathlib import Path
from urllib.parse import urlsplit
import unittest
ROOT=Path(__file__).resolve().parents[1]

class HTTPSubtitleModuleTest(unittest.TestCase):
    def test_whitelisted_module(self):
        tree=ast.parse((ROOT/'app.py').read_text(encoding='utf8'))
        klass=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='Handler')
        fn=next(n for n in klass.body if isinstance(n,ast.FunctionDef) and n.name=='do_GET')
        definition=ast.Module(body=[ast.ClassDef(name='MinimalHandler', bases=[], keywords=[], body=[fn], decorator_list=[])],type_ignores=[])
        ast.fix_missing_locations(definition)
        scope={'urlsplit':urlsplit,'ROOT':ROOT}
        exec(compile(definition,'app.py','exec'),scope)
        h=scope['MinimalHandler']()
        h.path='/subtitle-frame.mjs';h.response=lambda status,content,mime=None: (status,content,mime)
        status,body,mime=h.do_GET()
        self.assertEqual(status,200)
        self.assertIn('subtitleState',body.decode('utf8'))
        self.assertIn('javascript',mime)

if __name__=='__main__':unittest.main()
