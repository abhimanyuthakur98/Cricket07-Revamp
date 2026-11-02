import copy
import json
import tempfile
import unittest
from pathlib import Path
from roster.custom import PATH, snapshot


class CustomTests(unittest.TestCase):
    def load(self, players):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'players.json'
            path.write_text(json.dumps(players), encoding='utf-8')
            return snapshot(path)

    def test_order_ratings_reserves_and_profiles(self):
        players = [p for p in json.loads(PATH.read_text()) if p['team'] == 'India']
        result = self.load(players)
        for f in ('T20', 'ODI', 'Test'):
            squad = result['formats'][f]['teams'][0]['players']
            self.assertEqual(len(squad), 15)
            self.assertEqual([p['battingOrder'] for p in squad[:11]], list(range(1, 12)))
            self.assertTrue(all(not p['startingXI'] for p in squad[11:]))
            for p in squad:
                original = next(o for o in players if o['id'] == p['id'])
                self.assertEqual(p['ratings'], original['formats'][f]['ratings'])
                self.assertEqual(p['heightCm'], original['profile']['heightCm'])
                self.assertEqual(p['rawSkillValues'], original['gameInternals']['rawSkillValues'])

    def test_duplicate_ids_rejected(self):
        p = json.loads(PATH.read_text())[0]
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            self.load([p, copy.deepcopy(p)])

    def test_missing_keeper_rejected(self):
        players = [p for p in json.loads(PATH.read_text()) if p['team'] == 'England']
        for player in players:
            player['profile']['wicketkeeper'] = False
            if player['profile']['role'] == 'wicketkeeper':
                player['profile']['role'] = 'batter'
        with self.assertRaisesRegex(ValueError, 'wicketkeeper'):
            self.load(players)

