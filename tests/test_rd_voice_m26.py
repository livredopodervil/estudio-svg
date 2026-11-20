"""Regressões do ponto de integração M2.6: Edge, Piper e browser.

Executar no checkout real: python -m unittest discover -s tests -p test_rd_voice_m26.py
"""
import tempfile
import unittest
from pathlib import Path
from unittest import mock
import subprocess
import shutil

from rd_voices.core import Catalog
import studio_audio_score as score
import studio_core
from schema import default_project, normalize


class VoiceIntegration(unittest.TestCase):
    def test_all_snapshot_voices_supported_as_character(self):
        ids=[x['ShortName'] for x in Catalog.load().voices]
        self.assertEqual(len(ids), 318)
        self.assertEqual(len(ids), len(set(ids)))
        for voice in ids:
            parsed=score.parse_score(
                f'@personagem ator edge:{voice}\n00:00 | ator | neutro | | Texto.', 1)
            self.assertEqual(parsed['takes'][0]['voice'], 'edge:'+voice)

    def test_voice_override_on_line(self):
        parsed=score.parse_score(
            '@personagem atriz piper:faber\n'
            '00:00 | atriz | alegre | voz=edge:pt-BR-FranciscaNeural,ritmo=1.1,tom=7,volume=-5 | Olá.', 1)
        take=parsed['takes'][0]
        self.assertEqual(take['voice'], 'edge:pt-BR-FranciscaNeural')
        self.assertEqual(score.edge_cue_params(take)['pitch'], '+7Hz')
        self.assertEqual(score.edge_cue_params(take)['volume'], '-5%')

    def test_backward_compatible_piper_score(self):
        t=score.parse_score('@personagem atriz faber\n00:01 | atriz | neutro | ritmo=1.0 | Teste.',1)['takes'][0]
        self.assertEqual(t['voice'],'faber')
        self.assertEqual(t['tempo'],1.0)

    def test_unavailable_edge_voice_rejected(self):
        with self.assertRaises(ValueError):
            score.parse_score('@personagem a edge:pt-BR-VozInexistenteNeural\n00:00 | a | neutro | | Teste.',1)

    def test_browser_preview_selected_but_export_blocked(self):
        t=score.parse_score('@personagem a browser:system-voice\n00:00 | a | neutro | | Teste.',1)
        self.assertEqual(t['takes'][0]['voice'], 'browser:system-voice')
        with tempfile.TemporaryDirectory() as d:
            media=Path(d)/'media';cache=Path(d)/'cache';media.mkdir();cache.mkdir()
            with self.assertRaisesRegex(score.ScoreError, 'não exporta'):
                score.generate('@personagem a browser:system-voice\n00:00 | a | neutro | | Teste.',[1],media,cache,ffmpeg='ffmpeg')

    def test_project_and_scene_voice_survive_normalize(self):
        p=default_project()
        p['voice']={'provider':'edge','voice_id':'pt-BR-FranciscaNeural','prosody':{'rate_pct':-11,'pitch_hz':6,'volume_pct':-2},'intention':'calmo'}
        p['cenas'][0]['audio']['voice']={'provider':'edge','voice_id':'pt-BR-AntonioNeural','prosody':{'rate_pct':15,'pitch_hz':0,'volume_pct':0}}
        normalized=normalize(p)
        self.assertEqual(normalize(normalized),normalized)
        self.assertEqual(normalized['voice']['prosody']['rate_pct'],-11)
        self.assertEqual(studio_core.effective_voice(normalized['cenas'][0],normalized)['voice_id'],'pt-BR-AntonioNeural')
        self.assertEqual(studio_core.effective_voice(normalized['cenas'][1],normalized)['voice_id'],'pt-BR-FranciscaNeural')

    def test_browser_settings_survive_normalize(self):
        p=default_project();p['voice']={'provider':'browser','voice_id':'urn:local-speech','browser':{'rate':1.2,'pitch':1.4,'volume':.6},'prosody':{'rate_pct':0,'pitch_hz':0,'volume_pct':0}}
        normalized=normalize(p)
        self.assertEqual(normalized['voice']['browser']['rate'],1.2)
        with self.assertRaisesRegex(studio_core.StudioError,'não gera arquivo'):
            studio_core.effective_voice(normalized['cenas'][0],normalized)

    def test_edge_prosody_affects_cache_signature(self):
        p=default_project();p['voice']={'provider':'edge','voice_id':'pt-BR-AntonioNeural','prosody':{'rate_pct':-5}}
        old=studio_core.tts_key(p['cenas'][0],p)
        p['voice']['prosody']['rate_pct']=20
        self.assertNotEqual(old,studio_core.tts_key(p['cenas'][0],p))

    def test_old_project_cache_signature_unchanged(self):
        p=default_project();c=p['cenas'][0]
        self.assertIsNone(studio_core.effective_voice(c,p))
        self.assertEqual(studio_core.tts_key(c,p),studio_core.digest(['tts',c['audio']['voice_text'],p['voz'],p['velocidade_voz']]))

    def test_edge_cli_has_rate_pitch_volume(self):
        p=default_project();p['voice']={'provider':'edge','voice_id':'pt-BR-AntonioNeural','prosody':{'rate_pct':-9,'pitch_hz':8,'volume_pct':3}}
        with mock.patch.object(studio_core.shutil,'which',return_value='/usr/bin/edge-tts'),mock.patch.object(studio_core,'run') as run:
            studio_core.synthesize('Texto',p,Path('/tmp/voice.mp3'),scene=p['cenas'][0])
            cmd=run.call_args.args[0]
        self.assertEqual(cmd[cmd.index('--voice')+1],'pt-BR-AntonioNeural')
        self.assertEqual(cmd[cmd.index('--rate')+1],'-9%')
        self.assertEqual(cmd[cmd.index('--pitch')+1],'+8Hz')
        self.assertEqual(cmd[cmd.index('--volume')+1],'+3%')

    @unittest.skipUnless(shutil.which('ffmpeg'), 'FFmpeg requerido para decodificação real')
    def test_score_edge_to_scene_wav_using_mocked_synthesis(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);media=root/'media';cache=root/'cache';media.mkdir();cache.mkdir()
            sample=cache/'sample.mp3'
            subprocess.run(['ffmpeg','-nostdin','-v','error','-f','lavfi','-i','sine=frequency=440:duration=0.3',
                            '-codec:a','libmp3lame','-y',str(sample)],check=True)
            calls=[]
            def synth_edge(text,voice,params,media_dir,cache_dir):
                calls.append((text,voice,params)); dest=media_dir/'fake.mp3';dest.write_bytes(sample.read_bytes())
                return {'filename':'fake.mp3'}
            result=score.generate('@personagem b edge:pt-BR-AntonioNeural\n00:00 | b | alegre | ritmo=1.1,tom=2 | Olá.',
                                [1],media,cache,edge_synth=synth_edge)
            self.assertEqual(len(calls),1)
            self.assertEqual(result['count'],1)
            self.assertTrue((media/result['scenes'][0]['filename']).is_file())

if __name__=='__main__': unittest.main()
