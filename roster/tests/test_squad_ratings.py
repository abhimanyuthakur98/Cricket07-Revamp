import json
from pathlib import Path
import tempfile
import unittest
from roster.squad_ratings import prepare_ratings


class SquadRatingsTests(unittest.TestCase):
    def test_only_installed_players_and_format_specific_xi_are_exported(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            snapshot = {'asOf': '2026-11-03', 'formats': {}}
            for format_name, rating in [('Test', 70), ('ODI', 60), ('T20', 50)]:
                players = [{'id': str(i), 'name': f'Player {i}', 'stats': {'legalBalls': i * 30}}
                           for i in range(11)]
                team = {'name': 'Ireland', 'players': players, 'latestMatch': '2026-10-01'}
                skipped = {'name': 'Canada', 'players': players[:2], 'latestMatch': '2026-09-01'}
                snapshot['formats'][format_name] = {'teams': [team, skipped]}
                entries = [{'id': str(i), 'slot': 100 + i, 'name': f'Player {i}',
                            'gameRole': 3 if i > 5 else 1,
                            'ratings': {'batting': rating, 'bowling': rating}} for i in reversed(range(11))]
                (root / f'{format_name}.json').write_text(json.dumps({
                    'Ireland': entries, 'Canada': {'skipped': 'Fewer than 11'}}))
            output = prepare_ratings(snapshot, prepared=root)
            data = json.loads(output.read_text())
            self.assertEqual(data['asOf'], snapshot['asOf'])
            for format_name, rating in [('Test', 70), ('ODI', 60), ('T20', 50)]:
                teams = data['formats'][format_name]['teams']
                self.assertNotIn('3', teams)
                self.assertEqual(teams['60'], teams['62'])
                self.assertEqual(teams['60']['startingXI'], list(map(str, reversed(range(11)))))
                self.assertEqual(teams['60']['players'][0]['ratings']['batting'], rating)
                self.assertEqual(teams['60']['players'][0]['legalBalls'], 300)
                self.assertTrue(teams['60']['players'][0]['bowls'])
