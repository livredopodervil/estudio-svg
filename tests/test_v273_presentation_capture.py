"""Regression tests: local recorder route and continuous audio presentation."""
import contextlib
import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
import wave
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

import app
from schema import normalize
from studio_core import audio_key, continuous_music_signature, digest, scene_length, voice_source


class PresentationCaptureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server=ThreadingHTTPServer(('127.0.0.1', 0), app.Handler)
        cls.thread=threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base=f'http://127.0.0.1:{cls.server.server_port}'

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)

    def get(self, path, *, range_header=None):
        headers={'Range':range_header} if range_header else {}
        req=urllib.request.Request(self.base+path, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=8) as response:
                return response.status, response.headers, response.read()
        except urllib.error.HTTPError as error:
            return error.code, error.headers, error.read()

    def test_recorder_module_is_served(self):
        status, headers, body=self.get('/media-recorder.js?v=2.7.3')
        self.assertEqual(status, 200)
        self.assertIn('javascript', headers['Content-Type'])
        self.assertIn(b'window.StudioRecorder', body)

    def test_presentation_page_has_audio_controls(self):
        status, _, body=self.get('/captura?name=demo_organico')
        self.assertEqual(status, 200)
        self.assertIn(b'id="prepare"', body)
        self.assertIn(b'id="start"', body)

    def test_mix_signature_and_inline_stream_are_current(self):
        pr=normalize({'video':{'width':640,'height':360,'draw_fps':2},
                      'trilha_continua':False,
                      'cenas':[{'tipo':'numero','titulo':'TESTE','duracao':1,
                                'audio':{'voice_enabled':False}}]})
        scene=pr['cenas'][0]
        voice=voice_source(scene, pr, required=False)
        sec=scene_length(scene, pr, voice=bool(voice))
        sig=digest(['mix25',[audio_key(scene,pr,sec,voice)],continuous_music_signature(pr)])
        with tempfile.TemporaryDirectory() as td:
            base=Path(td)
            with wave.open(str(base/'teste_mix.wav'), 'wb') as wav:
                wav.setnchannels(2)
                wav.setsampwidth(2)
                wav.setframerate(48000)
                wav.writeframes(b'\0'*48000*4)
            (base/'teste_mix.json').write_text(json.dumps({'signature':sig}))
            with patch.object(app,'OUTPUT',base), patch.object(app,'read_project',return_value=pr):
                code,_,raw=self.get('/api/presentation?name=teste')
                self.assertEqual(code,200)
                info=json.loads(raw)
                self.assertTrue(info['mix_ready'])
                self.assertEqual(info['audio_url'],'/api/presentation/audio?name=teste')
                status,headers,payload=self.get(info['audio_url'],range_header='bytes=0-15')
                self.assertEqual(status,206)
                self.assertEqual(len(payload),16)
                self.assertEqual(headers['Content-Type'],'audio/wav')
                # Outdated project audio cannot be played accidentally.
                (base/'teste_mix.json').write_text(json.dumps({'signature':'stale'}))
                code,_,raw=self.get('/api/presentation?name=teste')
                self.assertFalse(json.loads(raw)['mix_ready'])
                code,_,_=self.get('/api/presentation/audio?name=teste')
                self.assertEqual(code,404)

    def test_preparation_job_runs_voice_then_mix(self):
        pr=normalize({'cenas':[{'tipo':'numero','audio':{'voice_enabled':False}}]})
        order=[]
        def voice(project,callback):
            order.append('voice'); callback(1,'vozes prontas')
        def mix(name,project,callback):
            order.append('mix'); callback(1,'mix pronto')
            return {'audio':'teste_mix.wav'}
        job={'id':'unit','status':'queued','logs':[], 'progress':0,'phase':'', 'lastlog':0}
        with patch.object(app,'read_project',return_value=pr), \
             patch('studio_core.batch_audio',side_effect=voice), \
             patch('studio_core.project_audio_mix',side_effect=mix):
            app.work(job,'teste','apresentacao-audio',None,False)
        self.assertEqual(job['status'],'done')
        self.assertEqual(order,['voice','mix'])
        self.assertEqual(job['result']['audio'],'teste_mix.wav')


if __name__=='__main__':
    unittest.main()
