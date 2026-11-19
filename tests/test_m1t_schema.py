import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from studio_instances import normalize_library, normalize_roots

MEDIA = {'id': 'photo', 'kind': 'image', 'file': 'photo.jpg',
         'x': .5, 'y': .5, 'w': .4, 'h': .4, 'start': 0, 'end': 8}
LIBRARY = {
    'format': 'rd-instance-library-1',
    'definitions': [
        {'id': 'photo', 'kind': 'media', 'media': MEDIA},
        {'id': 'pair', 'kind': 'group', 'children': [
            {'id': 'left', 'ref': 'photo', 'transform': {'matrix': [1,0,0,1,-.2,0]}},
            {'id': 'right', 'ref': 'photo', 'transform': {'matrix': [1,0,0,1,.2,0]}},
        ]},
    ],
}

def stub_media(items):
    return [dict(x) for x in items]

class M1T(unittest.TestCase):
    def test_shared_library_and_instances(self):
        lib, counts = normalize_library(LIBRARY, stub_media)
        self.assertEqual(counts['pair'], 2)
        roots = normalize_roots([{'id': 'copy1', 'ref': 'pair'}], counts, 8)
        self.assertEqual(roots[0]['end'], 8.)
        self.assertEqual(roots[0]['transform']['matrix'], [1.,0.,0.,1.,0.,0.])
        self.assertEqual(normalize_library(lib, stub_media)[0], lib)
        self.assertEqual(normalize_roots(roots, counts, 8), roots)

    def test_group_cycle_rejected(self):
        lib = {'format': 'rd-instance-library-1', 'definitions': [
            {'id': 'A', 'kind': 'group', 'children': [{'id':'b', 'ref': 'B'}]},
            {'id': 'B', 'kind': 'group', 'children': [{'id':'a', 'ref': 'A'}]},
        ]}
        with self.assertRaisesRegex(ValueError, 'ciclo'):
            normalize_library(lib, stub_media)

    def test_insecure_values_rejected(self):
        for bad_matrix in [[0,0,0,0,0,0], [1,0,0,1,float('nan'),0], [1,0,0,1,100,0]]:
            with self.subTest(bad_matrix=bad_matrix):
                with self.assertRaises(ValueError):
                    normalize_roots([{'id':'x','ref':'photo','transform':{'matrix':bad_matrix}}], {'photo':1}, 8)
        for bad_id in ['path/escape', 'á', '../evil', '']:
            with self.subTest(bad_id=bad_id):
                with self.assertRaises(ValueError):
                    normalize_roots([{'id':bad_id,'ref':'photo'}], {'photo':1}, 8)

    def test_limits(self):
        lib, counts = normalize_library(LIBRARY, stub_media)
        with self.assertRaises(ValueError):
            normalize_roots([{'id':f'x{i}', 'ref':'pair'} for i in range(33)], counts, 8)
        with self.assertRaises(ValueError):
            normalize_roots([{'id':'x', 'ref':'pair', 'start':7, 'end':5}], counts, 8)

    def test_empty_project(self):
        self.assertIsNone(normalize_library(None, stub_media))
        self.assertIsNone(normalize_roots(None, {}, 6))

if __name__ == '__main__':
    unittest.main()
