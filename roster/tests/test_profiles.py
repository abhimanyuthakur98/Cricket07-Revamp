import unittest
from roster.profiles import convert


class ProfileTests(unittest.TestCase):
    def test_keeper_bio_and_unknown_measurements(self):
        result = convert({'position': {'name': 'WK-Batsman'},
                          'batStyle': [{'description':'Left-hand bat'}]}, 'https://example.test/player')
        self.assertEqual(result['role'], 'wk')
        self.assertEqual(result['bat_hand'], 'L')
        self.assertIsNone(result['height'])
        self.assertIsNone(result['weight'])

    def test_spin_allrounder_style(self):
        result = convert({'position': {'name':'Bowling allrounder'},
                          'bowlStyle':[{'description':'Slow left-arm orthodox'}]}, 'https://example.test/player')
        self.assertEqual(result['role'], 'allround')
        self.assertEqual(result['bowl_style'], 'left-arm orthodox')
        self.assertEqual(result['bowl_arm'], 'L')

    def test_unknown_role_stays_unknown(self):
        self.assertIsNone(convert({'position':{'name':'Unknown'}},'https://example.test/player')['role'])
