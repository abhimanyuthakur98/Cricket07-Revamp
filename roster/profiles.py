"""Public ESPN player bios, joined through Cricsheet's stable player register.

Cache factual roles and published measurements; absent measurements stay null.
"""
from concurrent.futures import ThreadPoolExecutor
import csv
from datetime import datetime, timezone, timedelta
import io
import json
import html
import re
import urllib.request
from .refresh import ROOT, atomic_json

OUTPUT = ROOT / 'roster/player_profiles.json'
REGISTER = 'https://cricsheet.org/register/people.csv'
API = 'https://site.web.api.espn.com/apis/common/v3/sports/cricket/icc-world-cup/athletes/'


def fetch(url):
    request = urllib.request.Request(url, headers={'User-Agent': 'Cricket07-Revamp/1.0'})
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read()


def convert(athlete, source):
    position = athlete.get('position', {}).get('name', '')
    lower = position.lower()
    role = 'wk' if 'wicketkeeper' in lower or 'wicket keeper' in lower or lower.startswith('wk') else (
        'allround' if 'allrounder' in lower or 'all-rounder' in lower or 'all rounder' in lower else
        'bowl' if 'bowler' in lower else 'bat' if 'bat' in lower else None)
    bat = ' '.join(s.get('description', '') for s in athlete.get('batStyle', []))
    bowl = ' '.join(s.get('description', '') for s in athlete.get('bowlStyle', []))
    description = bowl.lower()
    style = ('left-arm wrist' if 'chinaman' in description or 'left-arm wrist' in description else
             'legspin' if 'legbreak' in description or 'leg spin' in description else
             'left-arm orthodox' if 'orthodox' in description else
             'offspin' if 'offbreak' in description or 'off spin' in description else
             'fast-medium' if 'fast-medium' in description or 'medium-fast' in description else
             'fast' if 'fast' in description else 'medium' if 'medium' in description else None)
    return {'name': athlete.get('displayName'), 'role': role, 'position': position,
            'bat_hand': 'L' if 'Left' in bat else 'R' if 'Right' in bat else None,
            'bowl_arm': 'L' if 'left' in description else 'R' if 'right' in description or style == 'legspin' else None,
            'bowl_style': style, 'height': athlete.get('height'), 'weight': athlete.get('weight'),
            'displayHeight': athlete.get('displayHeight'), 'displayWeight': athlete.get('displayWeight'),
            'dateOfBirth': athlete.get('displayDOB'), 'headshot': athlete.get('headshot', {}).get('href'),
            'source': source, 'fetchedAt': datetime.now(timezone.utc).isoformat()}


def update(snapshot):
    cached = json.loads(OUTPUT.read_text(encoding='utf-8')) if OUTPUT.exists() else {}
    ids = {p['id'] for f in snapshot['formats'].values() for t in f['teams'] for p in t['players']}
    cutoff = datetime.now(timezone.utc) - timedelta(days=30)
    def fresh(player_id):
        try:
            return datetime.fromisoformat(cached[player_id]['fetchedAt']) >= cutoff
        except (KeyError, ValueError):
            return False
    missing = {i for i in ids if not fresh(i)}
    if not missing:
        return cached
    register = {r['identifier']: r for r in csv.DictReader(io.StringIO(fetch(REGISTER).decode('utf-8-sig')))}
    def one(player_id):
        espn = register.get(player_id, {}).get('key_cricinfo')
        if not espn:
            return player_id, None
        source = API + espn
        try:
            athlete = json.loads(fetch(source))['athlete']
            return player_id, convert(athlete, source)
        except Exception as error:
            print('Player bio unavailable:', player_id, str(error), flush=True)
            return player_id, None
    with ThreadPoolExecutor(max_workers=5) as pool:
        for player_id, facts in pool.map(one, sorted(missing)):
            if facts:
                cached[player_id] = {**cached.get(player_id, {}), **facts}
    atomic_json(OUTPUT, cached)
    return cached


def enrich(snapshot):
    cached = json.loads(OUTPUT.read_text(encoding='utf-8')) if OUTPUT.exists() else {}
    ids = {p['id'] for f in snapshot['formats'].values() for t in f['teams'] for p in t['players']}
    pending = [i for i in ids if not cached.get(i, {}).get('bioChecked')]
    if not pending:
        return cached
    register = {r['identifier']: r for r in csv.DictReader(io.StringIO(fetch(REGISTER).decode('utf-8-sig')))}
    def one(player_id):
        key = register.get(player_id, {}).get('key_cricbuzz')
        profile = dict(cached.get(player_id, {}))
        if not key:
            profile['bioChecked'] = True
            profile['measurementStatus'] = 'No linked biography with published measurements'
            return player_id, profile
        source = 'https://www.cricbuzz.com/profiles/' + key
        try:
            page = fetch(source).decode('utf-8')
            def field(label):
                found = re.search('>' + re.escape(label) + r'</div><div[^>]*>(.*?)</div>', page, re.S)
                return html.unescape(re.sub('<[^>]+>', '', found[1])).strip() if found else ''
            height = field('Height')
            cm = re.search(r'(\d+(?:\.\d+)?)\s*cm', height)
            if cm:
                profile['heightCm'] = float(cm[1])
                profile['displayHeight'] = height
                profile['heightSource'] = source
            if not profile.get('role'):
                facts = convert({'position': {'name': field('Role')},
                                 'batStyle': [{'description': field('Batting Style')}],
                                 'bowlStyle': [{'description': field('Bowling Style')}]}, source)
                profile.update({k:v for k,v in facts.items() if v is not None})
            profile['bioChecked'] = True
            profile['bioSource'] = source
        except Exception as error:
            print('Bio unavailable:', player_id, str(error), flush=True)
            profile['bioChecked'] = True
            profile['measurementStatus'] = 'Biography unavailable; measurements not verified'
        return player_id, profile
    with ThreadPoolExecutor(max_workers=4) as pool:
        for player_id, facts in pool.map(one, sorted(pending)):
            if facts:
                cached[player_id] = facts
    atomic_json(OUTPUT, cached)
    return cached


if __name__ == '__main__':
    from .refresh import OUTPUT as SNAPSHOT
    print('Player profiles:', len(update(json.loads(SNAPSHOT.read_text(encoding='utf-8')))))
    print('Bios checked:', len(enrich(json.loads(SNAPSHOT.read_text(encoding='utf-8')))))
