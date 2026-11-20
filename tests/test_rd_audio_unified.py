import unittest
from unittest.mock import patch
from pathlib import Path
import tempfile
from studio_audio_score import parse_score, edge_cue_params, generate
from rd_voices.score_bridge import synthesize_edge_score

class UnifiedAudio(unittest.TestCase):
    def test_edge_and_piper_in_same_score(self):
        # A API AUD-U2 descobre os provedores via installed_catalog.
        # O fixture modela duas vozes disponíveis, sem consultar o Termux.
        fake_catalog = {'voices': [
            {'id': 'piper:faber', 'provider': 'piper', 'voice_id': 'faber', 'available': True},
            {'id': 'edge:pt-BR-AntonioNeural', 'provider': 'edge',
             'voice_id': 'pt-BR-AntonioNeural', 'available': True},
        ]}
        source='@personagem narrador piper:faber\n@personagem ana edge:pt-BR-AntonioNeural\n00:00 | narrador | neutro | ritmo=0.9 | Primeiro.\n00:01 | ana | alegre | ritmo=0.9,tom=3 | Segundo.'
        with patch('rd_voices.available_voices.installed_catalog',return_value=fake_catalog):
            parsed=parse_score(source)
        self.assertEqual([c['voice'] for c in parsed['takes']],['piper:faber','edge:pt-BR-AntonioNeural'])
        params=edge_cue_params(parsed['takes'][1])
        self.assertTrue(int(params['rate'].removesuffix('%'))>0,'Ritmo menor deve acelerar Edge')
        self.assertEqual(params['pitch'],'+3Hz')

    def test_existing_piper_score_unchanged(self):
        self.assertEqual(parse_score('00:00 | narrador | neutro | | Olá.')['takes'][0]['voice'],'faber')

    def test_uses_same_edge_engine_and_explicit_catalog_error(self):
        with tempfile.TemporaryDirectory() as d:
            base=Path(d);media=base/'media';cache=base/'cache';media.mkdir();cache.mkdir()
            calls=[]
            async def fake(payload,*,cache_dir):
                calls.append(payload)
                cache_dir.mkdir(parents=True,exist_ok=True)
                (cache_dir/('a'*64+'.mp3')).write_bytes(b'FAKE')
                return {'cache_key':'a'*64,'words':[]}
            with patch('rd_voices.score_bridge.synthesize_edge',fake):
                item=synthesize_edge_score('Oi','edge:pt-BR-AntonioNeural',{'rate':'+7%','pitch':'+3Hz','volume':'+0%'},media,cache)
            self.assertEqual(item['provider'],'edge')
            self.assertEqual(len(calls),1)
            self.assertEqual(calls[0]['prosody'],{'rate_pct':7,'pitch_hz':3,'volume_pct':0})
            self.assertTrue((media/item['filename']).is_file())

if __name__=='__main__':unittest.main()
