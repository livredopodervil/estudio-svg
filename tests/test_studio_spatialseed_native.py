from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from studio_spatialseed_native import convert_spatialseed


class TestSpatialSeedNative(unittest.TestCase):
    def test_rejects_untrusted_or_non_json_input(self):
        for value in ('', 'alert(1)', '[]', '{}'*125001):
            with self.subTest(value=value[:15]):
                with self.assertRaises(ValueError):
                    convert_spatialseed(value, 'gil', 'spatial')

    def test_requires_roots(self):
        with self.assertRaisesRegex(ValueError, 'RD_GIL_ROOT'):
            convert_spatialseed('{}', '', '')

    def test_converter_reads_valid_document_without_video(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            gil = root/'gil'; spatial=root/'seed'
            (gil/'tools').mkdir(parents=True)
            (gil/'tools'/'import_spatialseed.mjs').write_text('// test only')
            (spatial/'apps'/'web').mkdir(parents=True)
            def fake_run(cmd, timeout):
                self.assertEqual(cmd[0], 'node')
                self.assertEqual(cmd[1], '--max-old-space-size=256')
                self.assertEqual(timeout, 60)
                self.assertEqual(Path(cmd[3]).read_text(), '{"objetos":[]}')
                self.assertEqual(Path(cmd[5]), spatial)
                Path(cmd[4]).write_text('gil-timeline-test')
            with patch('studio_spatialseed_native.run', side_effect=fake_run):
                result = convert_spatialseed('{"objetos":[]}', gil, spatial)
            self.assertEqual(result['source'], 'gil-timeline-test')
            self.assertEqual(len(result['source_sha256']), 64)
            self.assertEqual(len(result['origin_sha256']), 64)


if __name__ == '__main__': unittest.main()
