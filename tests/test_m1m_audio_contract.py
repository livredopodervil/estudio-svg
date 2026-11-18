"""Dry-run tests of original Studio TTS contract (no network or synthesis)."""
import ast
import tempfile
import types
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
TREE=ast.parse((ROOT/'studio_core.py').read_text(encoding='utf8'))

def isolated(name, symbols):
    method=next(n for n in TREE.body if isinstance(n,ast.FunctionDef) and n.name==name)
    module=ast.fix_missing_locations(ast.Module(body=[method],type_ignores=[]))
    scope=dict(symbols)
    exec(compile(module,'studio_core.py','exec'),scope)
    return scope[name]

class ContractTest(unittest.TestCase):
    def test_edge_voice_and_srt_written_in_single_invocation(self):
        invocations=[]
        synth=isolated('synthesize',{
            'shutil':types.SimpleNamespace(which=lambda tool:'/stub/'+tool),
            'StudioError':RuntimeError,
            'run':lambda args,**kwargs: invocations.append((args,kwargs)),
        })
        synth('Palavra falada',{'motor_voz':'edge-tts','voz':'pt-BR-AntonioNeural','velocidade_voz':'+0%'},Path('/tmp/voz.mp3'),Path('/tmp/voz.srt'))
        self.assertEqual(len(invocations),1)
        cmd=invocations[0][0]
        self.assertEqual(cmd[0],'edge-tts')
        self.assertEqual(cmd[cmd.index('--write-media')+1],Path('/tmp/voz.mp3'))
        self.assertEqual(cmd[cmd.index('--write-subtitles')+1],'/tmp/voz.srt')

    def test_force_timing_success_preserves_cache_key_and_writes_subtitles(self):
        with tempfile.TemporaryDirectory() as dirname:
            base=Path(dirname)
            (base/'voices').mkdir()
            original=(base/'voices'/'aabb.mp3')
            original.write_bytes(b'original')
            def fake_synth(text,pr,tmp,subtitles=None):
                tmp.write_bytes(b'new audio' * 100)
                subtitles.write_text('1\n00:00:00,000 --> 00:00:00,400\nOlá\n')
            batch=isolated('batch_audio',{
                'CACHE':base,'OUTPUT':base,'StudioError':RuntimeError,
                'tts_key':lambda _s,_p:'aabb',
                'voice_extension':lambda _p:'.mp3',
                'duration':lambda path:1 if Path(path).exists() else 0,
                'synthesize':fake_synth,
            })
            pr={'motor_voz':'edge-tts','cenas':[{'audio':{'voice_enabled':True,'voice_text':'Olá','voice_file':'','muted':False}}]}
            batch(pr,export_zip=False,force_timing=True)
            self.assertEqual(original.read_bytes(),b'new audio'*100)
            self.assertTrue(original.with_suffix('.srt').is_file())

    def test_failed_tts_does_not_replace_cached_voice(self):
        with tempfile.TemporaryDirectory() as dirname:
            base=Path(dirname);(base/'voices').mkdir()
            original=base/'voices'/'aabb.mp3';original.write_bytes(b'old voice')
            def fail(*_a,**_kw):raise RuntimeError('rede ausente')
            batch=isolated('batch_audio',{
                'CACHE':base,'OUTPUT':base,'StudioError':RuntimeError,
                'tts_key':lambda _s,_p:'aabb',
                'voice_extension':lambda _p:'.mp3',
                'duration':lambda path:1 if Path(path).exists() else 0,
                'synthesize':fail,
            })
            pr={'motor_voz':'edge-tts','cenas':[{'audio':{'voice_enabled':True,'voice_text':'Olá','voice_file':'','muted':False}}]}
            with self.assertRaisesRegex(RuntimeError,'rede ausente'):
                batch(pr,export_zip=False,force_timing=True)
            self.assertEqual(original.read_bytes(),b'old voice')
            self.assertFalse(original.with_suffix('.srt').exists())

if __name__=='__main__':unittest.main()
