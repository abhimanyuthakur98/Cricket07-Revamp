"""Validate and adapt the user's curated player file without fetching third-party data."""
import json
from datetime import datetime, timezone
from pathlib import Path
from .teams import TEAMS

PATH = Path(__file__).resolve().parent / 'custom_players.json'
STYLES = {'offbreak': 'offspin', 'legbreak': 'legspin',
          'legbreak googly': 'legspin', 'slow left-arm orthodox': 'left-arm orthodox',
          'left-arm wrist-spin': 'left-arm wrist', 'medium-fast': 'fast-medium'}


def snapshot(path=PATH):
    players = json.loads(Path(path).read_text(encoding='utf-8'))
    if not isinstance(players, list) or not players:
        raise ValueError('Custom players must be a nonempty array')
    seen = set()
    formats = {f: {'teams': []} for f in ('Test', 'ODI', 'T20')}
    pools = {}
    for p in players:
        if p['id'] in seen or p['team'] not in TEAMS:
            raise ValueError('Duplicate player ID or unsupported team: ' + p['name'])
        seen.add(p['id'])
        profile = p['profile']
        role = 'wk' if profile.get('wicketkeeper') else {
            'batter': 'bat', 'bowler': 'bowl', 'allrounder': 'allround',
            'wicketkeeper': 'wk'}[profile['role']]
        fact = {'role': role, 'bat_hand': {'right': 'R', 'left': 'L'}[profile['battingHand']],
                'bowl_arm': {'right': 'R', 'left': 'L'}.get(profile['bowlingArm']),
                'bowl_style': STYLES.get(profile['bowlingStyle'], profile['bowlingStyle']),
                'source': 'User-supplied roster/custom_players.json'}
        raw = p.get('gameInternals', {}).get('rawSkillValues')
        if raw is not None and (len(raw) != 40 or any(type(v) is not int or not 0 <= v <= 63 for v in raw)):
            raise ValueError('Invalid raw skills: ' + p['name'])
        appearance = p.get('appearance', {})
        if 'skinPalette' in appearance and not 0 <= appearance['skinPalette'] <= 255:
            raise ValueError('Invalid skin palette: ' + p['name'])
        for f, entry in p['formats'].items():
            if f not in formats:
                raise ValueError('Unsupported format: ' + f)
            for key in ('batting', 'bowling'):
                rating = entry['ratings'].get(key)
                if rating is not None and (type(rating) is not int or not 1 <= rating <= 99):
                    raise ValueError('Invalid rating: ' + p['name'])
            s = entry['recentStats']
            stats = {k: s.get(k, 0) for k in ('runs', 'ballsFaced', 'dismissals', 'wickets', 'catches', 'stumpings', 'battingInnings')}
            stats.update(legalBalls=s.get('legalBallsBowled', 0), conceded=s.get('runsConceded', 0),
                         battingPositionTotal=(entry.get('battingOrder') or 7) * s.get('battingInnings', 0), openingSpells=0)
            pools.setdefault((f, p['team']), []).append({
                'id': p['id'], 'name': p['displayName'], 'fullName': p['name'],
                'lastPlayed': entry['lastPlayed'], 'matches': s.get('matches', 0),
                'stats': stats, 'ratings': entry['ratings'], 'startingXI': entry['startingXI'],
                'battingOrder': entry.get('battingOrder'), 'customProfile': fact,
                'customAppearance': appearance, 'rawSkillValues': raw,
                'heightCm': profile.get('heightCm'), 'weightKg': profile.get('weightKg')})
    for (f, team), squad in sorted(pools.items()):
        starters = [p for p in squad if p['startingXI']]
        if len(squad) > 20 or sorted(p['battingOrder'] for p in starters) != list(range(1, 12)):
            raise ValueError('Need an ordered XI and at most 20 players: ' + team + '/' + f)
        if not any(p['customProfile']['role'] == 'wk' for p in starters):
            raise ValueError('Starting XI needs a wicketkeeper: ' + team + '/' + f)
        squad.sort(key=lambda p: (not p['startingXI'], p['battingOrder'] or 99))
        latest = max((p['lastPlayed'] for p in squad if p['lastPlayed']), default=None)
        formats[f]['teams'].append({'name': team, 'gameTeamId': TEAMS[team][0],
            'logo': 'assets/teams/' + TEAMS[team][1] + '.png', 'latestMatch': latest,
            'latestMatchId': None, 'stale': False,
            'startingXI': [p['id'] for p in squad[:11]], 'players': squad})
    for data in formats.values():
        data['latestMatch'] = max((t['latestMatch'] for t in data['teams'] if t['latestMatch']), default=None)
    return {'schemaVersion': 1, 'asOf': max(p['asOf'] for p in players),
            'generatedAt': datetime.now(timezone.utc).isoformat(),
            'source': {'name': 'User-supplied player file'},
            'squadPolicy': 'User-defined XIs, batting order and reserves for each format. Includes custom Unlimited Overs squads.',
            'ratingPolicy': 'User-supplied ratings, not independently verified. Raw skills provide the baseline; format batting/bowling ratings adjust their skill groups.',
            'gameIntegration': 'local-launch-patch', 'customRoster': True, 'formats': formats}

