"""Regression tests for independent compressed exports and request dispatch."""
import json
import tempfile
import unittest
import wave
from pathlib import Path
from unittest.mock import patch

import app
import audio_export
from schema import normalize

class CompressedExportTests(unittest.TestCase):
    def make_source(self, path, seconds=0.5):
        with wave.open(str(path), 'wb') as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(48000)
            wav.writeframes(b'\x02\x01'*int(48000*seconds))

    def test_mp3_and_opus_are_valid_and_cached(self):
        with tempfile.TemporaryDirectory() as td:
            temp=Path(td);source=temp/'source.wav';self.make_source(source)
            for fmt,extension in [('mp3','.mp3'),('opus','.opus')]:
                dst=temp/('saida'+extension)
                a=audio_export.encode(source,dst,fmt)
                self.assertEqual(a['audio'],dst.name)
                self.assertTrue(dst.stat().st_size>100)
                self.assertTrue(audio_export.duration(dst)>0)
                self.assertFalse(a['cached'])
                b=audio_export.encode(source,dst,fmt)
                self.assertTrue(b['cached'])

    def test_export_scene_voice_is_independent_of_music(self):
        with tempfile.TemporaryDirectory() as td:
            temp=Path(td);source=temp/'speech.wav';self.make_source(source)
            project=normalize({'cenas':[{'tipo':'cartoes','audio':{'voice_enabled':True,'voice_file':'speech.wav'}}]})
            with patch.object(audio_export,'OUTPUT',temp),patch.object(audio_export,'voice_source',return_value=source):
                result=audio_export.export_scene_voice('meuprojeto',project,1)
            self.assertTrue((temp/result['audio']).is_file())
            self.assertIn('cena_001_voz.mp3',result['audio'])

    def test_voice_scene_bounds_and_queue_dispatch(self):
        project=normalize({'cenas':[{'tipo':'cartoes'}]})
        with self.assertRaisesRegex(audio_export.StudioError,'Número de cena'):
            audio_export.export_scene_voice('p',project,2)
        with patch.object(app,'read_project',return_value=project):
            job,reused=app.queue_job('unit','audio-mp3')
            self.assertEqual(job['mode'],'audio-mp3')
            # Wait for auto worker so it does not interfere with other tests.
            import time
            for _ in range(100):
                if job['status'] in ('done','error'):break
                time.sleep(.02)
        self.assertIn(job['status'],('done','error'))

    def test_content_type_for_audio_download_is_configured(self):
        import inspect
        src=inspect.getsource(app.Handler.route)
        self.assertIn("'audio/mpeg'",src)
        self.assertIn("'audio/ogg'",src)

if __name__ == '__main__':unittest.main()
