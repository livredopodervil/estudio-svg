import json, tempfile, unittest, wave, math, subprocess, shutil, os, threading, urllib.request, urllib.error
from pathlib import Path
from unittest.mock import patch
from http.server import ThreadingHTTPServer
import studio_core, studio_workspace as ws, app
from schema import normalize
from project_import import _free_name
from graphics import visualize

class Workspace(unittest.TestCase):
    def test_fit_real_voice_both_directions_and_skip(self):
        with tempfile.TemporaryDirectory() as tmp:
            d=Path(tmp)
            for fn,dur in [('short.wav',2.25),('long.wav',4.5)]:
                with wave.open(str(d/fn),'wb') as w:
                    w.setparams((1,2,8000,0,'NONE','not compressed'));w.writeframes(b'\x00\x00'*int(8000*dur))
            raw={'cenas':[{'duracao':20,'audio':{'voice_enabled':True,'voice_file':'short.wav','voice_delay':.12}}, {'duracao':2,'audio':{'voice_enabled':True,'voice_file':'long.wav','tracks':[{'file':'short.wav'}]}},{'duracao':10,'audio':{'voice_enabled':True,'voice_file':'missing.wav'}},{'duracao':11},{'duracao':12,'audio':{'voice_enabled':True,'voice_file':'short.wav','muted':True}}]}
            before=json.dumps(raw);pr=normalize(raw)
            with patch.object(studio_core,'MEDIA',d):
                rows=ws.voice_plan(raw,0,4);self.assertEqual(json.dumps(raw),before)
                self.assertAlmostEqual(rows[0]['after'],2.63,places=2);self.assertAlmostEqual(rows[1]['after'],4.88,places=2);self.assertTrue(rows[1]['other_audio'])
                for r in rows[:2]:
                    c=pr['cenas'][r['index']];c['duracao']=r['after'];self.assertGreaterEqual(studio_core.scene_length(c,pr),r['after'])
                self.assertNotIn('after',rows[2]);self.assertNotIn('after',rows[3]);self.assertNotIn('after',rows[4]);self.assertEqual(len(ws.voice_plan(raw,1,1)),1)
            with self.assertRaises(ValueError):ws.voice_plan(raw,0,5)
    def test_cache_voice_and_round_up(self):
        raw={'cenas':[{'duracao':19,'audio':{'voice_enabled':True,'voice_text':'teste','voice_delay':.12}}]}
        with patch.object(ws,'voice_source',return_value=Path('generated.mp3')),patch.object(ws,'duration',return_value=2.34567):
            r=ws.voice_plan(raw,0,0)[0];self.assertEqual(r['after'],2.726)
        with patch.object(ws,'voice_source',return_value=Path('generated.mp3')),patch.object(ws,'duration',return_value=601):
            self.assertNotIn('after',ws.voice_plan(raw,0,0)[0])
    def test_archive_restore_and_shared_media(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'a.json').write_bytes(b'{"raw":1}');(root/'b.json').write_bytes(b'{}');(root/'shared.mp4').write_bytes(b'unchanged')
            ws.change_archive(root,'a');self.assertFalse((root/'a.json').exists());self.assertEqual(ws.archived_projects(root),['a']);self.assertEqual(_free_name(root,'a','project'),'a_2.json')
            with patch.object(app,'PROJECTS',root):
                with self.assertRaises(studio_core.StudioError):app.save_project('a',{'cenas':[{}]})
            with self.assertRaises(ValueError):ws.change_archive(root,'b')
            ws.change_archive(root,'a',restore=True);self.assertEqual((root/'a.json').read_bytes(),b'{"raw":1}');self.assertEqual((root/'shared.mp4').read_bytes(),b'unchanged')
            with self.assertRaises(ValueError):ws.change_archive(root,'../a')
    def test_archive_without_hardlink_and_collision(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);src=root/'a.json';src.write_bytes(b'{ "raw": 1 }\n');(root/'b.json').write_bytes(b'{}')
            with patch.object(os,'link',side_effect=AssertionError('hard link unavailable'),create=True):
                ws.change_archive(root,'a');dest=ws.archive_path(root,'a')
                self.assertEqual(dest.read_bytes(),b'{ "raw": 1 }\n')
                src.write_bytes(b'other')
                with self.assertRaises(ValueError):ws.change_archive(root,'a',restore=True)
                self.assertEqual(src.read_bytes(),b'other');self.assertEqual(dest.read_bytes(),b'{ "raw": 1 }\n')
                src.unlink();ws.change_archive(root,'a',restore=True)
                self.assertEqual(src.read_bytes(),b'{ "raw": 1 }\n');self.assertFalse(dest.exists())
    def test_archive_copy_failure_preserves_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);src=root/'a.json';src.write_bytes(b'{}');(root/'b.json').write_bytes(b'{}')
            with patch.object(os,'fsync',side_effect=OSError('simulated write failure')):
                with self.assertRaises(OSError):ws.change_archive(root,'a')
            self.assertEqual(src.read_bytes(),b'{}');self.assertFalse(ws.archive_path(root,'a').exists())
    def test_archive_source_unlink_failure_preserves_both(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);src=root/'a.json';src.write_bytes(b'{}');(root/'b.json').write_bytes(b'{}')
            original=Path.unlink
            def fail_source(path,*args,**kwargs):
                if path==src:raise PermissionError('simulated unlink failure')
                return original(path,*args,**kwargs)
            with patch.object(Path,'unlink',fail_source):
                with self.assertRaisesRegex(OSError,'cópia preservada'):ws.change_archive(root,'a')
            self.assertEqual(src.read_bytes(),b'{}');self.assertEqual(ws.archive_path(root,'a').read_bytes(),b'{}')
    def test_archive_exclusive_destination_handles_race(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);src=root/'a.json';src.write_bytes(b'{}');(root/'b.json').write_bytes(b'{}')
            dest=ws.archive_path(root,'a');dest.parent.mkdir();dest.write_bytes(b'other')
            original=Path.exists
            def simulate_race(path,*args,**kwargs):
                return False if path==dest else original(path,*args,**kwargs)
            with patch.object(Path,'exists',simulate_race):
                with self.assertRaises(ValueError):ws.change_archive(root,'a')
            self.assertEqual(src.read_bytes(),b'{}');self.assertEqual(dest.read_bytes(),b'other')
    def test_inventory_roles_and_no_scan_of_unrelated_assets(self):
        with tempfile.TemporaryDirectory() as tmp:
            d=Path(tmp);(d/'shared.mp4').write_bytes(b'abc');(d/'secret.txt').write_bytes(b'not referenced');(d/'1234567890abcdef.png').write_bytes(b'fake')
            raw={'cenas':[{'tipo':'svg','svg':'<image href="asset:1234567890abcdef.png"/>','video_clipe':{'arquivo':'shared.mp4'},'audio':{'tracks':[{'file':'shared.mp4'}]}},{'imagem':{'arquivo':'missing.png'}}]}
            rows={r['file']:r for r in ws.inventory(raw,d)};self.assertEqual(set(rows),{'shared.mp4','missing.png','1234567890abcdef.png'});self.assertEqual(len(rows['shared.mp4']['uses']),2);self.assertFalse(rows['missing.png']['present'])
    def test_catalog_actual_visual_renderer(self):
        script="require('./web/workspace-v38.js'); const W=globalThis.StudioWorkspaceV38;console.log(JSON.stringify(W.catalog.map(([id])=>W.object(id,'obj_test',720,8))))"
        items=json.loads(subprocess.check_output(['node','-e',script],text=True,cwd=Path(__file__).resolve().parent.parent))
        for a in items:
            pr=normalize({'cenas':[{'tipo':'svg','titulo':'Biblioteca','svg':'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 720">'+a['markup']+'</svg>','animacoes':a['tracks']}]});c=pr['cenas'][0];self.assertEqual(len(c['animacoes']),len(a['tracks']))
            start=visualize(c,0);end=visualize(c,.3125);self.assertNotEqual(start,end);self.assertIn('obj_test',end);self.assertIn('obj_test',visualize(c,1,browser=True))
    def test_http_archive_origin_and_inventory(self):
        with tempfile.TemporaryDirectory() as tmp:
            d=Path(tmp);raw={'cenas':[{}]};(d/'one.json').write_text(json.dumps(raw));(d/'two.json').write_text(json.dumps(raw))
            srv=ThreadingHTTPServer(('127.0.0.1',0),app.Handler);t=threading.Thread(target=srv.serve_forever,daemon=True);t.start();base=f'http://127.0.0.1:{srv.server_port}'
            def req(route,data=None,origin=True):
                headers={'Content-Type':'application/json'}
                if origin:headers['Origin']=base
                try:
                    with urllib.request.urlopen(urllib.request.Request(base+route,data=json.dumps(data).encode() if data is not None else None,headers=headers),timeout=5) as r:return r.status,r.read()
                except urllib.error.HTTPError as e:return e.code,e.read()
            try:
                with patch.object(app,'PROJECTS',d),patch.object(app,'MEDIA',d):
                    p={'name':'one','action':'archive','confirm':'one'};self.assertEqual(req('/api/workspace/archive',p,False)[0],403);self.assertEqual(req('/api/workspace/archive',p)[0],200)
                    self.assertEqual(json.loads(req('/api/projects')[1])['projects'],['two']);self.assertEqual(json.loads(req('/api/workspace/archived')[1])['projects'],['one']);self.assertEqual(req('/api/workspace/archive',{**p,'action':'restore'})[0],200)
                    self.assertEqual(req('/api/workspace/voice-plan',{'project':raw,'first':0,'last':0})[0],200);self.assertEqual(req('/api/workspace/inventory',{'project':raw})[0],200);self.assertEqual(req('/workspace-v38.js')[0],200)
            finally:srv.shutdown();srv.server_close();t.join(timeout=5)
