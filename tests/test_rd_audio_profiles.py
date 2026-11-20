import importlib
import io
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
import wave

from rd_audio_profiles import compile_score, process_take, ProfileError

SCORE='''@processador radio {"ffmpeg":["highpass=f=75","acompressor=threshold=-18dB:ratio=2.5:attack=15:release=150"]}
@perfil investigativo {"ritmo":0.95,"ganho":1.0,"pausa":0.35,"tom":-3,"processador":"radio"}
@perfil enfatico {"ritmo":0.89,"ganho":1.1,"pausa":0.20}
@personagem narrador faber perfil=investigativo
@cena 1
@fala 00:00 [personagem=narrador] [estilo=investigativo] O governo emite títulos.
@fala 00:02 [personagem=narrador] [estilo=enfatico] [ritmo=0.92] E paga juros.
'''

class Profiles(unittest.TestCase):
    def test_definitions_and_tags(self):
        out=compile_score(SCORE)
        self.assertIn('00:00 | narrador | neutro |',out.source)
        self.assertIn('ritmo=0.92',out.source)
        self.assertIn('perfil definido',out.source)
        self.assertEqual(out.lines[6]['emotion'],'investigativo')
        self.assertEqual(out.lines[6]['processor'],'radio')
        self.assertEqual(out.lines[7]['emotion'],'enfatico')
        self.assertEqual(len(out.source.splitlines()),len(SCORE.splitlines()))
    def test_profile_on_character(self):
        s='@perfil documental {"ritmo":0.97}\n@personagem n faber perfil=documental\n@cena 1\n00:00 | n | neutro | | Bom dia.'
        out=compile_score(s)
        self.assertIn('ritmo=0.97',out.source)
    def test_legacy_is_unchanged(self):
        old='@personagem n faber\n@cena 1\n00:00 | n | solene | ritmo=0.94 | Teste.'
        self.assertEqual(compile_score(old).source,old)
    def test_invalid_json(self):
        with self.assertRaises(ProfileError):compile_score('@perfil X {oops}')
    def test_invalid_untrusted_processor(self):
        with self.assertRaises(ProfileError):compile_score('@processador p {"ffmpeg":["amovie=/etc/passwd"]}')
        with self.assertRaises(ProfileError):compile_score('@processador p {"ffmpeg":["highpass=f=80;touch /tmp/x"]}')
    def test_invalid_limits(self):
        with self.assertRaises(ProfileError):compile_score('@perfil a {"ritmo":3.0}')
        with self.assertRaises(ProfileError):compile_score('@perfil a {"script":"rm -rf /"}')
    def test_missing_processor(self):
        with self.assertRaises(ProfileError):compile_score('@perfil a {"processador":"ausente"}')
    def test_profiler_engine_integrated(self):
        try:score=importlib.import_module('studio_audio_score')
        except ImportError:self.skipTest('score legacy not included')
        result=score.parse_score(SCORE,1)
        self.assertEqual(len(result['takes']),2)
        self.assertEqual(result['takes'][0]['emotion'],'investigativo')
        self.assertEqual(result['takes'][1]['emotion'],'enfatico')
        self.assertEqual(result['takes'][1]['tempo'],0.92)
        self.assertEqual(result['takes'][0]['processor'],'radio')
    def test_sample_is_one_take_and_does_not_replace_existing(self):
        try:score=importlib.import_module('studio_audio_score')
        except ImportError:self.skipTest('score legacy not included')
        with tempfile.TemporaryDirectory() as t:
            media=Path(t)/'media';media.mkdir();cache=Path(t)/'cache';cache.mkdir()
            keeper=media/'existing.wav';keeper.write_bytes(b'untouched')
            invoked=[]
            def fake_synth(text,voice,tempo,pause,med,cac):
                invoked.append((text,voice))
                p=Path(med)/'stub.wav'
                with wave.open(str(p),'wb') as w:
                    w.setnchannels(1);w.setsampwidth(2);w.setframerate(22050)
                    w.writeframes(b'\0\0'*2205)
                return {'filename':'stub.wav'}
            result=score.generate(SCORE,[10.0],media,cache,synth=fake_synth,only_line=6)
            self.assertEqual(len(invoked),1)
            self.assertEqual(len(result['scenes']),1)
            self.assertEqual(result['scenes'][0]['takes'],1)
            self.assertEqual(keeper.read_bytes(),b'untouched')
            self.assertTrue((media/result['scenes'][0]['filename']).exists())

    def test_process_takes_audio(self):
        if not subprocess.run(['which','ffmpeg'],capture_output=True).returncode==0:self.skipTest('ffmpeg missing')
        with tempfile.TemporaryDirectory() as t:
            media=Path(t)/'media';media.mkdir();cache=Path(t)/'cache';cache.mkdir()
            original=media/'demo.wav'
            with wave.open(str(original),'wb') as w:
                w.setnchannels(1);w.setsampwidth(2);w.setframerate(22050)
                w.writeframes(b'\0\0'*2205)
            out=process_take(original,'radio',{'radio':{'ffmpeg':['highpass=f=75']}},media,cache)
            self.assertTrue(out.exists())
            self.assertNotEqual(out,original)
            self.assertEqual(process_take(original,'radio',{'radio':{'ffmpeg':['highpass=f=75']}},media,cache),out)
            self.assertTrue(original.exists())

if __name__=='__main__':unittest.main()
