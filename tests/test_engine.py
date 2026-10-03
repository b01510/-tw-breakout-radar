import json
import unittest
from pathlib import Path
from engine import evaluate

class EventTests(unittest.TestCase):
    def test_real_retry_is_detected_without_future_bars(self):
        bars=json.loads((Path(__file__).parent/'fixtures/2069-through-2026-09-08.json').read_text())
        old=evaluate(bars[:-1]);new=evaluate(bars)
        self.assertEqual(old['status'],'疑似假突破')
        self.assertEqual(new['status'],'今日突破')
        self.assertEqual(new['breakoutDate'],'2026-09-08')
        self.assertAlmostEqual(new['platformHigh'],22.15,places=2)
        self.assertTrue(new['retry'])
        self.assertEqual(new['eventHistory'][-1]['failedDate'],'2026-09-02')
    def test_live_platform_does_not_move_on_followthrough(self):
        bars=json.loads((Path(__file__).parent/'fixtures/2069-through-2026-09-08.json').read_text())
        first=evaluate(bars)
        bars.append(dict(date='2026-09-09',open=22.7,high=24.5,low=22.65,close=23.3,volume=3729655))
        next_=evaluate(bars)
        self.assertEqual(first['eventId'],next_['eventId'])
        self.assertEqual(first['platformHigh'],next_['platformHigh'])
        self.assertEqual(first['resistance'],next_['resistance'])
    def test_ordinary_low_volume_rebound_does_not_restore_failed_event(self):
        bars=json.loads((Path(__file__).parent/'fixtures/2069-through-2026-09-08.json').read_text())
        bars=bars[:-1]
        previous=evaluate(bars)
        bars.append(dict(date='2026-09-08',open=21.35,high=22.4,low=20.95,close=22.4,volume=1000))
        next_=evaluate(bars)
        self.assertEqual(next_['status'],'疑似假突破')
        self.assertEqual(previous['breakoutDate'],next_['breakoutDate'])
if __name__=='__main__': unittest.main()
