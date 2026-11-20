"""RD Audio 1: parser, boundaries, caching, offline mixing."""
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
import wave

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from studio_audio_score import parse_score, ScoreError, generate, seconds, status_kokoro

SCORE='''# Exemplo do RD Audio 1
@personagem narrador faber
@personagem cientista edresson
@cena 1
00:00.0 | narrador | calmo | ritmo=0.94,ganho=1,pausa=0.2 | O átomo contém prótons.
00:01.0 | cientista | urgente | ritmo=0.90,ganho=0.8 | O nêutron provoca fissão!
@cena 2
00:00.5 | narrador | neutro | ritmo=1.0,ganho=1.2 | Energia liberada.
'''

class AudioScoreTests(unittest.TestCase):
    def test_parse_roles_timing_emotions(self):
        r=parse_score(SCORE,2)
        self.assertEqual([x['voice'] for x in r['takes']],['faber','edresson','faber'])
        self.assertEqual([x['scene'] for x in r['takes']],[1,1,2])
        self.assertAlmostEqual(r['takes'][1]['tempo'],.819)
        self.assertAlmostEqual(r['takes'][1]['gain'],.88)
        self.assertEqual(seconds('1:02.125'),62.125)
        self.assertGreater(len(r['warnings']),0)

    def test_bad_score_rejected(self):
        errors=['@cena 9\n00:00 | narrador | neutro | | Texto.',
                '00:00 | admin | neutro | | Texto.',
                '00:00 | narrador | malicioso | | Texto.',
                '00:00 | narrador | neutro | ritmo=nan | Texto.',
                '00:00 | narrador | neutro | | ',
                '00:00 | !efeito | ../secret.wav | ganho=1',
                '00:00 | narrador | neutro | ganho=1; rm -rf / | Texto.']
        for s in errors:
            with self.subTest(s=s),self.assertRaises(ScoreError):parse_score(s,2)

    def test_missing_kokoro_not_claimed_portuguese(self):
        with tempfile.TemporaryDirectory() as d:
            st=status_kokoro(d)
            self.assertFalse(st['ready_ptbr'])

    def test_effect_metadata(self):
        s='00:01.5 | !efeito | impacto.wav | ganho=0.35'
        r=parse_score(s,1)
        self.assertEqual(r['effects'][0]['file'],'impacto.wav')
        self.assertEqual(r['effects'][0]['at'],1.5)

    @unittest.skipUnless(__import__('shutil').which('ffmpeg'),'ffmpeg requerido para teste de mix')
    def test_mix_multiple_voices_scenes_and_cache(self):
        with tempfile.TemporaryDirectory() as d:
            folder=Path(d);media=folder/'media';cache=folder/'cache';media.mkdir();cache.mkdir()
            calls=[]
            def fake(text,voice,tempo,pause,media_dir,cache_dir):
                rate=22050 if voice=='faber' else 16000
                name='fake-'+voice+'.wav';p=media_dir/name
                if not p.exists():
                    with wave.open(str(p),'wb') as f:
                        f.setnchannels(1);f.setsampwidth(2);f.setframerate(rate)
                        f.writeframes((int(1000 if voice=='faber' else -500).to_bytes(2,'little',signed=True))*int(rate*.20))
                calls.append((voice,tempo))
                return {'filename':name,'seconds':.2,'cached':False,'voice':voice}
            s='@personagem narrador faber\n@personagem outro edresson\n@cena 1\n00:00.0 | narrador | calmo | | Olá.\n00:00.5 | outro | alegre | | Adeus.\n@cena 2\n00:00.1 | narrador | neutro | | Fim.'
            out=generate(s,[1.0,1.0],media,cache,synth=fake)
            self.assertEqual(len(out['scenes']),2)
            self.assertEqual([r['scene'] for r in out['scenes']],[1,2])
            self.assertEqual(len(calls),3)
            for item in out['scenes']:
                with wave.open(str(media/item['filename']),'rb') as f:
                    self.assertEqual((f.getframerate(),f.getnchannels(),f.getsampwidth()),(22050,1,2))
                    self.assertAlmostEqual(f.getnframes()/22050,1,places=2)
            cached=generate(s,[1.0,1.0],media,cache,synth=fake)
            self.assertTrue(all(x['cached'] for x in cached['scenes']))

    @unittest.skipUnless(__import__('shutil').which('ffmpeg'),'ffmpeg requerido para teste de mix')
    def test_mix_effects_no_path_traversal(self):
        with tempfile.TemporaryDirectory() as d:
            folder=Path(d);media=folder/'media';cache=folder/'cache';media.mkdir();cache.mkdir()
            p=media/'impacto.wav'
            with wave.open(str(p),'wb') as f:
                f.setnchannels(1);f.setsampwidth(2);f.setframerate(22050);f.writeframes(b'\0\x01'*2205)
            result=generate('00:00.1 | !efeito | impacto.wav | ganho=0.5',[.5],media,cache)
            self.assertEqual(result['scenes'][0]['effects'],1)

if __name__=='__main__':unittest.main()
