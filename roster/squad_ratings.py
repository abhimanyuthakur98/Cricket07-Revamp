"""Export only player/slot data that was actually installed for each format.

The browser's pure squad-rating-model.mjs owns the aggregation formula.
"""
import json
from .refresh import ROOT, atomic_json
from .teams import TEAMS


def prepare_ratings(snapshot, *, broadcast_ui=False, prepared=None):
    prepared = prepared or ROOT / 'local_runtime' / ('prepared-ui' if broadcast_ui else 'prepared')
    names = {str(team_id): name for name, (team_id, _) in TEAMS.items()}
    names.update({'61': 'Scotland', '62': 'Ireland'})
    result = {'schemaVersion': 1, 'asOf': snapshot['asOf'], 'teamNames': names, 'formats': {}}
    for format_name in ('Test', 'ODI', 'T20'):
        report = json.loads((prepared / f'{format_name}.json').read_text(encoding='utf-8'))
        teams = {}
        for team in snapshot['formats'][format_name]['teams']:
            entries = report.get(team['name'])
            if not isinstance(entries, list) or len(entries) < 11:
                continue  # A retained original squad must not receive a fictional rating.
            source = {p['id']: p for p in team['players']}
            players = [{'id': p['id'], 'slot': p['slot'], 'name': p['name'],
                        'ratings': p['ratings'], 'bowls': p['gameRole'] in (3, 4, 5, 9, 10),
                        'legalBalls': source[p['id']]['stats']['legalBalls']}
                       for p in entries]
            team_id = TEAMS[team['name']][0]
            data = {'name': team['name'], 'latestMatch': team['latestMatch'],
                    'stale': team.get('stale', False), 'players': players,
                    'startingXI': [p['id'] for p in entries[:11]]}
            teams[str(team_id)] = data
            for alias in {57: [61], 60: [62]}.get(team_id, []):
                teams[str(alias)] = data
        result['formats'][format_name] = {'teams': teams}
    output = prepared / 'squad-ratings.json'
    atomic_json(output, result)
    return output
