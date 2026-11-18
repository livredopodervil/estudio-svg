"""Smoke contract: the new narration module is reachable through the explicit HTTP allowlist."""
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

class VoiceBatchWebContract(unittest.TestCase):
    def test_module_is_whitelisted(self):
        self.assertIn("'/voice-bulk.mjs'", (ROOT/'app.py').read_text(encoding='utf8'))
        self.assertTrue((ROOT/'web/voice-bulk.mjs').is_file())
    def test_buttons_are_present(self):
        index=(ROOT/'web/index.html').read_text(encoding='utf8')
        app=(ROOT/'web/app.js').read_text(encoding='utf8')
        self.assertIn('id="activateAllVoices"',index)
        self.assertIn('activateAllVoicesEditor',app)
        self.assertIn("await prepareNarrations('browser-export')",app)
if __name__=='__main__':unittest.main()
