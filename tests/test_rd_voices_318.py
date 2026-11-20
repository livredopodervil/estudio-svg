import asyncio
import json
from pathlib import Path
import tempfile
import types
import unittest
from unittest.mock import patch
from rd_voices import Catalog, normalize_voice, resolve_voice, resolve_voice_config, make_voice_plan, edge_parameters
from rd_voices.edge_engine import synthesize_edge


class CatalogAndContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.c = Catalog.load()

    def test_catalog_integrity(self):
        self.assertEqual(len(self.c.voices), 318)
        self.assertEqual(len({v['Locale'] for v in self.c.voices}), 142)
        self.assertEqual(self.c.normalized()['count'],318)
        self.assertEqual(len(self.c.by_id),318)

    def test_pt_br(self):
        self.assertEqual({v['ShortName'] for v in self.c.voices if v['Locale']=='pt-BR'},
            {'pt-BR-AntonioNeural', 'pt-BR-FranciscaNeural', 'pt-BR-ThalitaMultilingualNeural'})

    def test_preserves_every_source_field(self):
        normalized = self.c.normalized()
        for i, item in enumerate(self.c.voices):
            self.assertEqual(normalized['voices'][i]['raw'], item)
            self.assertTrue(normalized['voices'][i]['id'].startswith('edge:'))

    def test_no_native_style(self):
        self.assertFalse(self.c.normalized()['capabilities']['native_style'])
        self.assertFalse(self.c.normalized()['capabilities']['native_emotion'])
        self.assertIn('VoicePersonalities', self.c.voices[0]['VoiceTag'])

    def test_identity(self):
        self.assertEqual(normalize_voice('edge:pt-BR-AntonioNeural'),{'provider':'edge','voice_id':'pt-BR-AntonioNeural'})
        self.assertEqual(normalize_voice('pt_BR-faber-medium'),{'provider':'legacy','voice_id':'pt_BR-faber-medium'})
        self.assertEqual(normalize_voice('piper:pt_BR-faber-medium'),{'provider':'piper','voice_id':'pt_BR-faber-medium'})
        self.assertEqual(normalize_voice('browser:com.google.voice_pt'),{'provider':'browser','voice_id':'com.google.voice_pt'})

    def test_scope_priority(self):
        p={'voice':'edge:pt-BR-AntonioNeural'}
        ch={'voice':'piper:pt_BR-faber-medium'}
        scene={'voice':'edge:pt-BR-FranciscaNeural'}
        line={'voice':'edge:pt-BR-ThalitaMultilingualNeural'}
        self.assertEqual(resolve_voice(project=p,character=ch,scene=scene,line=line)['voice_id'],'pt-BR-ThalitaMultilingualNeural')
        self.assertEqual(resolve_voice(project=p,character=ch)['provider'],'piper')
        self.assertEqual(resolve_voice(project=p)['provider'],'edge')

    def test_scope_prosody_preserved(self):
        p={'voice':{'provider':'edge','voice_id':'pt-BR-AntonioNeural','prosody':{'rate_pct':-4,'pitch_hz':3}}}
        ch={'voice':'edge:pt-BR-FranciscaNeural','prosody':{'rate_pct':5},'intention':'solene'}
        scene={'prosody':{'volume_pct':2}}
        line={'voice':'edge:pt-BR-ThalitaMultilingualNeural','prosody':{'rate_pct':9}}
        c=resolve_voice_config(project=p,character=ch,scene=scene,line=line)
        self.assertEqual(c['prosody'], {'rate_pct':9,'pitch_hz':3,'volume_pct':2})
        self.assertEqual(c['intention'],'solene')
        self.assertEqual(c['voice_id'],'pt-BR-ThalitaMultilingualNeural')
        self.assertEqual(p['voice']['prosody'],{'rate_pct':-4,'pitch_hz':3})

    def test_script_plan_by_scene_and_character(self):
        p={'voice':'edge:pt-BR-AntonioNeural',
           'characters':{'ana':{'voice':'edge:pt-BR-FranciscaNeural'}},
           'scenes':[{'id':'s1','lines':[{'id':'l1','character_id':'ana','text':'Olá'},
                                      {'id':'l2','text':'Narração','voice':'edge:pt-BR-ThalitaMultilingualNeural'}]}]}
        plan=make_voice_plan(p)
        self.assertEqual(len(plan),2)
        self.assertEqual(plan[0]['config']['voice_id'],'pt-BR-FranciscaNeural')
        self.assertEqual(plan[1]['config']['voice_id'],'pt-BR-ThalitaMultilingualNeural')
        self.assertEqual(plan[1]['scene_id'],'s1')

    def test_edge_params_and_presets(self):
        self.assertEqual(edge_parameters({'prosody':{'rate_pct':10,'pitch_hz':-6,'volume_pct':2}})['rate'],'+10%')
        self.assertEqual(edge_parameters({'emotion':'alegre','apply_intention_preset':False})['pitch'],'+0Hz')
        self.assertEqual(edge_parameters({'emotion':'alegre','apply_intention_preset':True})['pitch'],'+8Hz')
        self.assertFalse(edge_parameters({'emotion':'triste'})['native_style_supported'])
        with self.assertRaises(ValueError):edge_parameters({'prosody':{'pitch_hz':201}})
        with self.assertRaises(ValueError):edge_parameters({'prosody':{'rate_pct':'20;rm -rf'}})

    def test_error_handling(self):
        with self.assertRaises(ValueError):resolve_voice(project={})
        with self.assertRaises(ValueError):self.c.require('pt-BR-fakeNeural')
        with self.assertRaises(ValueError):make_voice_plan({'scenes': 'oops'})

    def test_edge_mock_stream_and_cache(self):
        class FakeSpeech:
            calls=[]
            def __init__(self, **kw):
                self.calls.append(kw)
            async def stream(self):
                yield {'type':'WordBoundary','text':'Olá','offset':10_000_000,'duration':3_000_000}
                yield {'type':'audio','data':b'ID3fake mp3 bytes'}
        fake=types.SimpleNamespace(Communicate=FakeSpeech)
        with tempfile.TemporaryDirectory() as root, patch.dict('sys.modules',{'edge_tts':fake}):
            payload={'text':'Olá','voice':'edge:pt-BR-FranciscaNeural',
                     'prosody':{'rate_pct':-5,'pitch_hz':3,'volume_pct':2},'emotion':'calmo'}
            a=asyncio.run(synthesize_edge(payload,cache_dir=Path(root),catalog=self.c))
            self.assertIn('audio_url',a)
            self.assertEqual(a['words'][0]['start_sec'],1.0)
            self.assertEqual(a['words'][0]['duration_sec'],0.3)
            self.assertFalse(a['intention_is_native'])
            self.assertEqual(FakeSpeech.calls[0]['rate'],'-5%')
            self.assertNotIn('style',FakeSpeech.calls[0])
            b=asyncio.run(synthesize_edge(payload,cache_dir=Path(root),catalog=self.c))
            self.assertEqual(b,a)
            self.assertEqual(len(FakeSpeech.calls),1)
            self.assertTrue((Path(root)/(a['cache_key']+'.mp3')).is_file())

if __name__=='__main__':unittest.main()
