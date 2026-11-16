import hashlib
import json
import os
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch
from patches import PatchManager,PatchError

def digest(b):return hashlib.sha256(b).hexdigest()

class TestPatches(unittest.TestCase):
    def setUp(self):
        self.t=tempfile.TemporaryDirectory()
        self.addCleanup(self.t.cleanup)
        self.home=Path(self.t.name)
        self.repo=self.home/'repo';self.repo.mkdir()
        (self.repo/'content-src').mkdir()
        (self.repo/'content-src'/'aps.md').write_text('ANTIGO',encoding='utf8')
        (self.home/'storage'/'downloads').mkdir(parents=True)
        self.env=patch('pathlib.Path.home',return_value=self.home);self.env.start();self.addCleanup(self.env.stop)
        self.m=PatchManager(self.repo)
        # Unit tests must never scan actual Android /sdcard/Download or user files.
        # Restrict discovery to the disposable temp directory used by this test.
        self.inbox_patch=patch.object(self.m,'_inbox_paths',
            return_value=[self.home/'storage'/'downloads'])
        self.inbox_patch.start();self.addCleanup(self.inbox_patch.stop)
        self.name='teste-editorial.rdpatch.zip'
        self.path=self.home/'storage'/'downloads'/self.name
        self.man={'schema':1,'id':'aps-test-plugin','title':'APS teste','version':'1.0',
            'files':[{'path':'content-src/aps.md','operation':'replace', 'allowed_before_sha256':[digest(b'ANTIGO')], 'sha256':digest(b'NOVO')},
             {'path':'assets/img.webp','operation':'add','sha256':digest(b'WEBP_DATA')} ]}
        self.make_zip()
    def make_zip(self,manifest=None,files=None):
        with zipfile.ZipFile(self.path,'w') as z:
            z.writestr('patch.json',json.dumps(manifest or self.man))
            for k,v in (files or {'content-src/aps.md':b'NOVO','assets/img.webp':b'WEBP_DATA'}).items():
                z.writestr('files/'+k,v)
    def test_plan_apply_remove_roundtrip(self):
        self.assertTrue(self.m.plan(self.name)['ready'])
        self.assertEqual(len(self.m.installed()),0)
        self.m.apply(self.name,'APLICAR')
        self.assertEqual((self.repo/'content-src'/'aps.md').read_text(),'NOVO')
        self.assertTrue((self.repo/'assets/img.webp').is_file())
        self.assertEqual(self.m.plan(self.name)['ready'],False)
        self.assertTrue(self.m.removal_plan('aps-test-plugin')['ready'])
        self.m.remove('aps-test-plugin','REMOVER')
        self.assertEqual((self.repo/'content-src'/'aps.md').read_text(),'ANTIGO')
        self.assertFalse((self.repo/'assets/img.webp').exists())
    def test_edited_file_blocks_remove(self):
        self.m.apply(self.name,'APLICAR')
        (self.repo/'content-src'/'aps.md').write_text('EDIÇÃO DO USUÁRIO')
        self.assertFalse(self.m.removal_plan('aps-test-plugin')['ready'])
        with self.assertRaises(PatchError):self.m.remove('aps-test-plugin','REMOVER')
        self.assertEqual((self.repo/'content-src'/'aps.md').read_text(),'EDIÇÃO DO USUÁRIO')
    def test_changed_base_blocks_apply(self):
        (self.repo/'content-src'/'aps.md').write_text('OUTRO')
        self.assertFalse(self.m.plan(self.name)['ready'])
        with self.assertRaises(PatchError):self.m.apply(self.name,'APLICAR')
    def test_hash_tampered_blocks_plan(self):
        self.make_zip(files={'content-src/aps.md':b'TAMPERED','assets/img.webp':b'WEBP_DATA'})
        with self.assertRaises(PatchError):self.m.plan(self.name)
    def test_unsafe_path(self):
        self.man['files'][0]['path']='../secrets.txt'
        self.make_zip()
        with self.assertRaises(PatchError):self.m.plan(self.name)
    def test_symlink_blocks(self):
        (self.repo/'assets').symlink_to(self.home)
        self.assertFalse((self.home/'img.webp').exists())
        with self.assertRaises(PatchError):self.m.plan(self.name)
    def test_idempotent_state(self):
        self.m.apply(self.name,'APLICAR')
        with self.assertRaises(PatchError):self.m.apply(self.name,'APLICAR')
    def test_accepts_mp4_and_roundtrip(self):
        mp4=b'\x00\x00\x00\x18ftypisom\x00\x00\x02\x00isomiso2'
        manifest={'schema':1,'id':'intro-video-teste','title':'Vídeo teste','version':'1.0.0',
                  'files':[{'path':'assets/intro/abertura.mp4','operation':'add','sha256':digest(mp4)}]}
        self.make_zip(manifest,{'assets/intro/abertura.mp4':mp4})
        self.assertTrue(self.m.plan(self.name)['ready'])
        self.m.apply(self.name,'APLICAR')
        self.assertEqual((self.repo/'assets/intro/abertura.mp4').read_bytes(),mp4)
        self.m.remove('intro-video-teste','REMOVER')
        self.assertFalse((self.repo/'assets/intro/abertura.mp4').exists())

    def test_rejects_disguised_mp4(self):
        fake=b'not-an-mp4'
        manifest={'schema':1,'id':'intro-video-falso','title':'Vídeo falso','version':'1.0.0',
                  'files':[{'path':'assets/intro/abertura.mp4','operation':'add','sha256':digest(fake)}]}
        self.make_zip(manifest,{'assets/intro/abertura.mp4':fake})
        with self.assertRaises(PatchError):self.m.plan(self.name)

    def test_confirmation(self):
        with self.assertRaises(PatchError):self.m.apply(self.name,'SIM')
    def test_archives_list(self):
        l=self.m.available()
        # Results can contain arbitrary archives in real use, so do not rely
        # on list position; the test itself only sees its disposable fixture.
        self.assertEqual({item.get('id') for item in l['available']},
                         {'aps-test-plugin'})
        self.assertEqual(len(l['available']),1)
        self.assertEqual(l['installed'],[])

if __name__=='__main__':unittest.main()
