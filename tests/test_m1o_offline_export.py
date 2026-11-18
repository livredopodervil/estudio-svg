"""Testes M1O: integridade, retomada, cronologia constante e MP4 com áudio."""
import io
import subprocess
from array import array
import json
from pathlib import Path
import tempfile
import unittest
import wave
from PIL import Image

import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from offline_export import OfflineExport, OfflineError, _probe, synth_gil_wav


def png(i,width=320,height=320):
    pic=Image.new('RGB',(width,height), ((i*13)%255, (i*31)%255,(i*53)%255))
    mem=io.BytesIO()
    pic.save(mem,format='PNG')
    return mem.getvalue()


def silence(path,seconds):
    with wave.open(str(path),'wb') as w:
        w.setnchannels(2);w.setsampwidth(2);w.setframerate(48000)
        remaining=round(seconds*48000)
        while remaining:
            take=min(remaining,8192)
            w.writeframesraw(b'\0'*(take*4))
            remaining-=take


class TestOffline(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root=Path(self.tmp.name)
        for n in ('cache','render','media'):(root/n).mkdir()
        self.root=root
        self.m=OfflineExport(root/'cache',root/'render',root/'media',chunk_frames=12)
        self.pr={'titulo':'QA','video':{'width':320,'height':320,'fps':24},'cenas':[{'duracao':1.5}]}
        self.event=[{'time':.35,'duration':.25,'frequency':540,'gain':.04,'wave':'sine'}]
        self.args={'durations':[1.5], 'voices':[None], 'build_mix':lambda target:silence(target,1.5),
                   'gil_events':self.event, 'fps':24,'width':320,'height':320}

    def start(self):
        return self.m.start(self.pr,**self.args)

    def test_partial_session_resume_and_final_mp4(self):
        first=self.start()
        self.assertEqual(first['frames'],36)
        self.assertEqual(first['next_frame'],0)
        self.assertFalse(first['resumed'])
        token=first['token']
        for i in range(17):
            result=self.m.upload(token,i,png(i))
            self.assertEqual(result['next_frame'],i+1)
        self.assertEqual(result['chunks'],1)
        # Simulação de encerramento do servidor, preservando arquivos no disco.
        self.m=OfflineExport(self.root/'cache',self.root/'render',self.root/'media',chunk_frames=12)
        again=self.start()
        self.assertEqual(again['token'],token)
        self.assertEqual(again['next_frame'],17)
        self.assertTrue(again['resumed'])
        with self.assertRaisesRegex(OfflineError,'Sequência inválida'):
            self.m.upload(token,16,png(16))
        for i in range(17,36):
            self.m.upload(token,i,png(i))
        done=self.m.finish(token)
        self.assertEqual(done['stats']['encoded_frames'],36)
        self.assertAlmostEqual(done['stats']['video_seconds'],1.5,places=2)
        self.assertTrue((self.root/'render'/done['file']).is_file())
        streams=_probe(self.root/'render'/done['file'])['streams']
        video=next(s for s in streams if s['codec_type']=='video')
        self.assertEqual(video['avg_frame_rate'],'24/1')
        self.assertEqual(int(video['nb_read_frames']),36)
        self.assertEqual(len([s for s in streams if s['codec_type']=='audio']),1)
        self.assertEqual(self.m.finish(token)['file'],done['file'])
        self.assertFalse(list((self.root/'cache'/token/'frames').glob('*.png')))
        output=subprocess.run(['ffmpeg','-v','error','-ss','0.37','-t','0.08',
                               '-i',str(self.root/'render'/done['file']),'-vn',
                               '-ar','48000','-ac','1','-c:a','pcm_s16le','-f','s16le','pipe:1'],
                               capture_output=True,check=False)
        if output.returncode:raise RuntimeError(output.stderr.decode())
        output=output.stdout
        samples=array('h');samples.frombytes(output[:len(output)//2*2])
        self.assertGreater(max(map(abs,samples)),200,'tom GIL deve estar no MP4')
        packet_csv=subprocess.run(['ffprobe','-v','error','-select_streams','v:0',
                                  '-show_entries','packet=pts_time','-of','csv=p=0',
                                  str(self.root/'render'/done['file'])],
                                  capture_output=True,text=True,check=True).stdout
        pts=[float(x.strip()) for x in packet_csv.splitlines() if x.strip()]
        self.assertEqual(len(pts),36)
        self.assertTrue(all(b>a for a,b in zip(pts,pts[1:])), 'timestamps crescentes')

    def test_recover_crash_before_segment_manifest(self):
        initial=self.start();token=initial['token']
        path=self.root/'cache'/token
        # O navegador enviou o último PNG; processo morreu antes do ffmpeg.
        for i in range(12):
            (path/'frames'/f'{i:08d}.png').write_bytes(png(i))
        # Um MP4 temporário não commitado não poderá ser confundido com um segmento válido.
        (path/'segments'/'000000.mp4').write_bytes(b'incomplete')
        self.m=OfflineExport(self.root/'cache',self.root/'render',self.root/'media',chunk_frames=12)
        resumed=self.start()
        self.assertEqual(resumed['next_frame'],12)
        self.assertEqual(resumed['chunks'],1)
        for i in range(12,36):self.m.upload(token,i,png(i))
        self.assertEqual(self.m.finish(token)['stats']['encoded_frames'],36)

    def test_recover_audio_preparation_interrupted(self):
        first=self.start();token=first['token']
        path=self.root/'cache'/token
        (path/'mix.wav').unlink()
        (path/'mix.partial.wav').write_bytes(b'incompleto')
        state=json.loads((path/'state.json').read_text())
        state['status']='preparing'
        (path/'state.json').write_text(json.dumps(state))
        again=self.start()
        self.assertEqual(again['token'],token)
        self.assertEqual(again['next_frame'],0)
        self.assertGreater((path/'mix.wav').stat().st_size,44)

    def test_discard_partial_png_temp_after_crash(self):
        token=self.start()['token']
        temp=self.root/'cache'/token/'frames'/'00000000.tmp'
        temp.write_bytes(b'data not yet committed')
        self.m=OfflineExport(self.root/'cache',self.root/'render',self.root/'media',chunk_frames=12)
        self.assertEqual(self.start()['next_frame'],0)
        self.m.upload(token,0,png(0))
        self.assertFalse(temp.exists())
        self.assertEqual(self.m.status(token)['next_frame'],1)

    def test_wrong_dimensions_or_sequence_rejected(self):
        token=self.start()['token']
        with self.assertRaisesRegex(OfflineError,'Sequência inválida'):
            self.m.upload(token,1,png(1))
        with self.assertRaisesRegex(OfflineError,'dimensões incorretas'):
            self.m.upload(token,0,png(0,322,320))
        with self.assertRaisesRegex(OfflineError,'não é PNG'):
            self.m.upload(token,0,b'x'*100)
        self.assertEqual(self.m.status(token)['next_frame'],0)
        with self.assertRaisesRegex(OfflineError,'Quadros incompletos'):
            self.m.finish(token)

    def test_media_changed_invalidates_checkpoint(self):
        # Fingerprint capta mudanças de arquivos usados pelo projeto.
        path=self.root/'media'/'image.png'
        path.write_bytes(b'first')
        self.pr['cenas'][0]['imagem']='image.png'
        first=self.start()
        path.write_bytes(b'second-changed')
        next_session=self.start()
        self.assertNotEqual(first['token'],next_session['token'])

    def test_tone_limits(self):
        args=dict(self.args)
        args['gil_events']=[{'time':0,'duration':.1,'frequency':800,'gain':2,'wave':'sine'}]
        with self.assertRaisesRegex(OfflineError,'fora dos limites'):
            self.m.start(self.pr,**args)

if __name__=='__main__':unittest.main()
