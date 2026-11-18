import sys, unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from subtitle_times import parse_srt, seconds
class TimingTest(unittest.TestCase):
    def test_one_word_per_boundary_and_delay(self):
        raw = """1
00:00:00,000 --> 00:00:00,310
Olá

2
00:00:00,590 --> 00:00:01,110
mundo!
"""
        cues=parse_srt(raw, .12)
        self.assertEqual(cues,[{'start':.12,'end':.43,'text':'Olá'}, {'start':.71,'end':1.23,'text':'mundo!'}])
    def test_webvtt(self):
        cues=parse_srt('WEBVTT\n\n00:00:02.350 --> 00:00:03.100\nA palavra')
        self.assertEqual(cues[0],{'start':2.35,'end':3.1,'text':'A palavra'})
    def test_reject_invalid_data(self):
        self.assertEqual(parse_srt('texto sem tempos'),[])
        with self.assertRaises(ValueError):parse_srt('a'*250001)
        with self.assertRaises(ValueError):seconds('00:00:64,001')
        with self.assertRaises(ValueError):parse_srt('1\n00:00:00,000 --> 00:00:01,000\nx',delay=33)
if __name__=='__main__':unittest.main()
