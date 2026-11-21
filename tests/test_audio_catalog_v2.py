from pathlib import Path
from unittest.mock import patch
from tempfile import TemporaryDirectory
import json
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from rd_voices.available_voices import KOKORO_NAMES,piper_models,installed_catalog,kokoro_lexicon,require_voice
from studio_audio_score import parse_score,generate

class CatalogTests(unittest.TestCase):
    def test_kokoro_ids_are_zero_based_official(self):
        self.assertEqual(len(KOKORO_NAMES),54)
        self.assertEqual(KOKORO_NAMES[42:46],['pf_dora','pm_alex','pm_santa','zf_xiaobei'])
    def test_dynamic_piper_models_and_languages(self):
        with TemporaryDirectory() as d:
            root=Path(d)
            for suffix,rate in [('pt_BR-faber-medium',22050),('pt_BR-cadu-medium',22050),('pt_BR-jeff-medium',22050),('pt_BR-edresson-low',16000),('en_US-ryan-medium',22050)]:
                (root/(suffix+'.onnx')).write_bytes(b'test')
                (root/(suffix+'.onnx.json')).write_text(json.dumps({'audio':{'sample_rate':rate}}))
            result=piper_models(root)
            self.assertEqual(set(result),{'faber','cadu','jeff','edresson','en_us-ryan'})
            self.assertEqual(result['edresson']['rate'],16000)
    def test_unavailable_kokoro_lexicon_not_misrepresented(self):
        with TemporaryDirectory() as d:
            root=Path(d)
            for f in ['model.onnx','voices.bin','tokens.txt']:(root/f).write_bytes(b'x')
            (root/'espeak-ng-data').mkdir()
            self.assertIsNone(kokoro_lexicon(root,'pt-BR'))
            (root/'lexicon-pt.txt').write_text('teste')
            self.assertEqual(kokoro_lexicon(root,'pt-BR').name,'lexicon-pt.txt')
            cat=installed_catalog(piper_root=root/'not-here',kokoro_root=root,edge_catalog={'voices':[]})
            self.assertEqual(next(x for x in cat['voices'] if x['id']=='kokoro:pm_alex')['sid'],43)
    def test_mixed_script_edge_piper_kokoro(self):
        with patch('rd_voices.available_voices.require_voice',return_value={'available':True}):
            script='@personagem dora kokoro:pf_dora\n@personagem tecnico piper:cadu\n@cena 1\n00:00 | dora | calmo | | Olá.\n00:01 | tecnico | neutro | | Bom dia.'
            parsed=parse_score(script,1)
            self.assertEqual([v['voice'] for v in parsed['takes']],['kokoro:pf_dora','piper:cadu'])
    def test_enumerate_sans_implicit_fallback(self):
        with self.assertRaisesRegex(ValueError,'não encontrada'):
            require_voice('piper:unknown',catalog={'voices':[]})

if __name__=='__main__':unittest.main()
