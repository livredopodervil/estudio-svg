"""Pure read-only adapter tests; no external servers, media or Git changes."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import studio_suite_m3a as suite

class SuiteM3A(unittest.TestCase):
    def test_probe_local_endpoint_no_secrets(self):
        with tempfile.TemporaryDirectory() as p:
            root=Path(p)
            for file in ('rd_audio_profiles.py','studio_audio_score.py'):
                (root/file).write_text('')
            state={'root':'/tmp/site','git':{'branch':'main','head':'8e8554f','status':[]}}
            with patch.object(suite,'_request_json',return_value=state) as probe, \
                 patch.object(suite,'_request_status',return_value=True):
                r=suite.snapshot(root, {'RD_SUITE_ADMIN_PORT':'8885','RD_SUITE_PREVIEW_PORT':'8886'})
            probe.assert_called_once_with(8885,'/api/state')
            self.assertTrue(r['read_only']);self.assertEqual(r['schema'],1)
            self.assertEqual([x['id'] for x in r['services']], ['studio','admin','site','spatialseed','gil','audio'])
            self.assertEqual(r['services'][1]['state'],'online')
            self.assertEqual(r['services'][-1]['state'],'presente')
            self.assertNotIn('token',json.dumps(r).lower())
    def test_admin_unavailable_is_nonfatal(self):
        with patch.object(suite,'_request_json',side_effect=OSError('offline')), \
             patch.object(suite,'_request_status',side_effect=TimeoutError):
            result=suite.snapshot(Path('/no-such-directory'),{})
        self.assertEqual(result['services'][1]['state'],'indisponível')
        self.assertEqual(result['services'][2]['state'],'indisponível')
        self.assertEqual(result['services'][3]['state'],'não configurado')
    def test_site_root_mismatch_and_dirty_reported(self):
        state={'root':'/tmp/stale','git':{'branch':'main','head':'160e29d','status':[{'state':' M','path':'index.html'}]}}
        with patch.object(suite,'_request_json',return_value=state), \
             patch.object(suite,'_request_status',return_value=True):
            result=suite.snapshot(Path('/tmp'),{'RD_SUITE_EXPECTED_SITE_ROOT':'/tmp/published'})
        self.assertEqual(result['services'][1]['state'],'aviso')
        self.assertIn('diferente',result['services'][1]['detail'])
    def test_invalid_port_does_not_probe(self):
        with patch.object(suite,'_request_json',side_effect=AssertionError('must not connect')):
            result=suite.snapshot(Path('/tmp'),{'RD_SUITE_ADMIN_PORT':'8885.evil'})
        self.assertEqual(result['services'][1]['state'],'erro')
        self.assertIsNone(result['ports']['admin'])
    def test_modules_are_only_presence_not_runtime_claim(self):
        with tempfile.TemporaryDirectory() as p:
            root=Path(p);ss=root/'spatial';gil=root/'gil'
            for file in (ss/'apps/web/index.html',ss/'vendor/three.module.js',gil/'src/model.mjs',gil/'src/timeline.mjs'):
                file.parent.mkdir(parents=True,exist_ok=True);file.touch()
            with patch.object(suite,'_request_json',side_effect=OSError()), \
                 patch.object(suite,'_request_status',side_effect=OSError()), \
                 patch.object(suite,'_git',return_value='206b9a9'):
                result=suite.snapshot(root,{'RD_SPATIALSEED_ROOT':str(ss),'RD_GIL_ROOT':str(gil)})
            self.assertEqual(result['services'][3]['state'],'presente')
            self.assertEqual(result['services'][4]['state'],'presente')
            self.assertIn('não testada',result['services'][3]['detail'])

if __name__=='__main__': unittest.main()
