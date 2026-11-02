"""Apply a launch snapshot to verified Cricket 07 BIGF/CDF team slots.

Always rebuild from the pristine local archive; never compound patches.
"""
import hashlib
import json
from pathlib import Path
import re
import struct
from .archive import BigArchive
from .refresh import ROOT, atomic_json
from .teams import TEAMS

DATABASE = '113964e05e69ab31d264fb8f15c58e5c.cdf'
FACES = '730eef3fd7726e43de955f21083ab000.xml'
SPEEDS = '6db25817c37163921676c2d9be05214e.xml'
STYLE = {('R', 'legspin'): 0, ('L', 'left-arm wrist'): 1,
         ('R', 'offspin'): 2, ('L', 'offspin'): 2, ('L', 'left-arm orthodox'): 3,
         ('L', 'medium'): 4, ('R', 'medium'): 5, ('L', 'fast-medium'): 6,
         ('R', 'fast-medium'): 7, ('L', 'fast'): 8, ('R', 'fast'): 9}


def normalize(text):
    return re.sub('[^a-z0-9]', '', text.lower())


def role_for(name, team, metadata):
    candidates = metadata.get(team, {}).get('players', [])
    key = normalize(name)
    for player in candidates:
        aliases = [player.get('name'), player.get('scoreboard')] + player.get('aliases', [])
        if player.get('first') and player.get('last'):
            aliases.append(''.join(part[0] for part in player['first'].split()) + player['last'])
        if key in [normalize(alias) for alias in aliases if alias]:
            return {**player, 'source': player.get('source', metadata[team].get('source'))}
    # Surname + first initial must identify exactly one person within this team.
    tokens = name.replace('.', ' ').split()
    if len(tokens) > 1:
        matches = [p for p in candidates if normalize(p.get('last', '')) == normalize(tokens[-1])
                   and p.get('first', '?')[0].lower() == tokens[0][0].lower()]
        if len(matches) == 1:
            return {**matches[0], 'source': matches[0].get('source', metadata[team].get('source'))}
    return None


def skills(record):
    return [(struct.unpack_from('<I', record, 100 + 4 * (i // 5))[0] >> (6 * (i % 5))) & 63 for i in range(40)]


def write_skills(record, values):
    for word in range(8):
        original = struct.unpack_from('<I', record, 100 + 4 * word)[0]
        packed = original & 0xc0000000
        for index in range(5):
            packed |= int(values[word * 5 + index]) << (index * 6)
        struct.pack_into('<I', record, 100 + 4 * word, packed)


def shift(values, indices, target):
    delta = target - sum(values[i] for i in indices) / len(indices)
    for i in indices:
        values[i] = max(1, min(62, round(values[i] + delta)))


def game_name(name):
    raw = name.encode('latin1', 'replace')
    if len(raw) > 15:
        parts = name.split()
        raw = (parts[0][0] + '.' + ' '.join(parts[1:])).encode('latin1', 'replace')
    return raw[:15].ljust(16, b'\0')


def player_type(role, position, bowls=False, spin=False, opening=False):
    if role == 'wk':
        return 7 if position <= 2.5 else 8
    if role == 'allround' or (not role and bowls and position <= 7):
        return 5 if spin else 9
    if role == 'bowl' or (not role and bowls):
        return 4 if spin else 10 if opening else 3
    return 2 if position <= 2.5 else 1


def prepare(snapshot, format_name, *, database_only=False, broadcast_ui=False):
    original = ROOT / 'local_runtime/game/Data/data.gob'
    archive = BigArchive(original)
    database = bytearray(archive.read(DATABASE))
    if len(database) != 620140:
        raise ValueError('Unsupported game database version; original files were left untouched')
    metadata_file = ROOT / 'roster/player_metadata.json'
    metadata = json.loads(metadata_file.read_text(encoding='utf-8')) if metadata_file.exists() else {}
    overrides = json.loads((ROOT / 'roster/role_overrides.json').read_text(encoding='utf-8'))
    profile_file = ROOT / 'roster/player_profiles.json'
    profiles = json.loads(profile_file.read_text(encoding='utf-8')) if profile_file.exists() else {}
    appearance_file = ROOT / 'roster/appearance_profiles.json'
    appearances = json.loads(appearance_file.read_text(encoding='utf-8')) if appearance_file.exists() else {}
    for team, facts in overrides.items():
        verified = [{**p, 'source': p.get('source', facts.get('source')), 'verifiedOverride': True} for p in facts['players']]
        metadata.setdefault(team, {'players': []})['players'] = verified + metadata.get(team, {}).get('players', [])
    records = {}
    for offset in range(4, 432004, 360):
        record = bytes(database[offset:offset + 360])
        player_id = struct.unpack_from('<H', record, 0)[0]
        if player_id:
            records[player_id] = (offset, record)
    replacements, report, changed = {}, {}, set()
    for team in snapshot['formats'][format_name]['teams']:
        name = team['name']
        if name not in TEAMS:
            continue
        team_id, _ = TEAMS[name]
        start = 432004 + team_id * 2808
        slots = list(struct.unpack_from('<20H', database, start))
        if len(set(slots)) != 20 or not all(slot in records for slot in slots):
            raise ValueError('Unrecognized team layout: ' + name)
        squad = list(team['players'])
        if len(squad) < 11:
            report[name] = {'skipped': 'Fewer than 11 recent players; original squad retained'}
            continue
        alias_file = ROOT / 'roster/player_aliases.json'
        aliases = json.loads(alias_file.read_text(encoding='utf-8')) if alias_file.exists() else {}
        facts = {p['id']: next((fact for alias in [p['name']] + aliases.get(p['id'], [])
                               if (fact := role_for(alias, name, metadata))), None) for p in squad}
        for player in squad:
            if player.get('customProfile'):
                facts[player['id']] = player['customProfile']
                continue
            profile = profiles.get(player['id'], {})
            if (facts[player['id']] or {}).get('verifiedOverride'):
                facts[player['id']] = {**{k:v for k,v in profile.items() if v is not None},
                                       **{k:v for k,v in facts[player['id']].items() if v is not None}}
            elif profile.get('role'):
                facts[player['id']] = {**(facts[player['id']] or {}),
                                       **{k:v for k,v in profile.items() if v is not None}}
        def keeper(p):
            fact = facts[p['id']]
            return bool((fact and fact.get('role') == 'wk') or p['stats']['stumpings'])
        def bowling(p):
            fact = facts[p['id']]
            return fact.get('role') in ('bowl', 'allround') if fact and fact.get('role') else p['stats']['legalBalls'] >= 60
        def position(p):
            if p.get('battingOrder') is not None:
                return p['battingOrder']
            stats = p['stats']
            return stats.get('battingPositionTotal', 0) / max(1, stats.get('battingInnings', 0)) if stats.get('battingInnings') else 7
        # The source already supplies the latest XI in scorecard batting order,
        # followed by reserves. Never sort it by form or average career position.
        entries = []
        for slot, player in zip(slots, squad):
            offset, pristine = records[slot]
            record = bytearray(pristine)
            fact = facts[player['id']]
            is_keeper = keeper(player)
            if fact:
                style = STYLE.get((fact.get('bowl_arm'), fact.get('bowl_style')))
                donor_roles = (6,7,8) if is_keeper else (3,4,5,9,10) if bowling(player) else (1,2)
                pool = [r for _, r in records.values()
                        if (r[351] & 15) in donor_roles
                        and (style is None or (r[132] & 15) == style)]
                if pool:
                    donor = min(pool, key=lambda r: abs(sum(skills(r)[:14]) / 14 - 45))
                    record[100:134] = donor[100:134]
                if fact.get('bat_hand') in ('L','R'):
                    record[133] = (record[133] & 0xfe) | int(fact.get('bat_hand') == 'L')
                if style is not None:
                    record[132] = (record[132] & 0xd0) | style
                    record[132] &= ~0x20
                else:
                    if bowling(player):
                        record[132] &= ~0x20
                    else:
                        record[132] |= 0x20
            if is_keeper:
                record[133] = (record[133] & 0xe1) | 4
            elif (record[133] >> 1) & 15 == 2:
                record[133] &= 0xe1
            # Player type is independent from the fielding-position flags above.
            spin = fact and fact.get('bowl_style') in ('legspin', 'offspin', 'left-arm wrist', 'left-arm orthodox')
            role = player_type('wk' if is_keeper else fact.get('role') if fact else None,
                               position(player), bowling(player), spin, player['stats'].get('openingSpells', 0))
            record[351] = (record[351] & 0xf0) | role
            appearance = player.get('customAppearance') or appearances.get(player['id'])
            if appearance:
                record[209] = appearance['skinPalette']
            record[4:20] = game_name(player['name'])
            record[20:100] = bytes(80)  # Do not present the donor's career as the new player's.
            struct.pack_into('<H', record, 2, 0xffff)  # No incorrect 2006 commentary name.
            values = player.get('rawSkillValues') or skills(record)
            values = list(values)
            for field, indices in (('batting', range(14)), ('bowling', range(18, 23))):
                rating = player['ratings'][field]
                if rating is not None:
                    shift(values, indices, 1 + rating * 61 / 99)
            write_skills(record, values)
            database[offset:offset + 360] = record
            changed.add(slot)
            entries.append({'id': player['id'], 'slot': slot, 'name': player['name'],
                            'displayName': record[4:20].split(b'\0')[0].decode('latin1'),
                            'ratings': player['ratings'], 'roleMetadata': bool(fact), 'keeper': is_keeper,
                            'gameRole': role, 'battingPosition': position(player),
                            'startingXI': player.get('startingXI', len(entries)<11),
                            'roleSource': fact.get('source') if fact else 'Scorecard workload inference',
                            'appearance': appearance or {'method': 'Generic appearance; no portrait reference available'},
                            'heightCm': player.get('heightCm', profiles.get(player['id'], {}).get('heightCm')),
                            'weightKg': player.get('weightKg')})
        # Original reserves must not remain in a current squad with fewer than 20 players.
        active_slots = slots[:len(squad)]
        padded = active_slots + [0] * (20 - len(active_slots))
        captain_index = next((i for i,p in enumerate(squad[:11]) if facts[p['id']] and
                              ('T20I' if format_name == 'T20' else format_name) in (facts[p['id']].get('captain_formats') or [])), 0)
        for copy_id in [team_id] + ({57: [61], 60: [62]}.get(team_id, [])):
            base = 432004 + copy_id * 2808
            struct.pack_into('<20H', database, base, *padded)
            struct.pack_into('<H', database, base + 46, slots[captain_index])
        report[name] = entries
    replacements[DATABASE] = bytes(database)
    prepared = ROOT / 'local_runtime' / ('prepared-ui' if broadcast_ui else 'prepared')
    output = prepared / (format_name + '.cdf')
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(database)
    atomic_json(output.with_suffix('.json'), report)
    if database_only:
        return {'format': format_name, 'players': len(changed)}
    # Reused IDs must no longer select old stars' special face models or fixed bowling speeds.
    faces = archive.read(FACES)
    faces = re.sub(rb'<player\b[^>]*location="(\d+)"[^>]*/>',
                   lambda m: b'' if int(m[1]) in changed else m[0], faces)
    replacements[FACES] = faces
    speeds = archive.read(SPEEDS)
    replacements[SPEEDS] = re.sub(rb'<Bowler\s+ID\s*=\s*"(\d+)"[^>]*/>',
                                 lambda m: b'' if int(m[1]) in changed else m[0], speeds)
    from .logos import logo_replacements
    replacements.update(logo_replacements(archive))
    target = prepared / 'Data/data.gob'
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix('.tmp')
    archive.replace_into(temporary, replacements)
    temporary.replace(target)
    digest = hashlib.sha256(target.read_bytes()).hexdigest()[:16]
    atomic_json(prepared / 'report.json', {'format': format_name, 'asOf': snapshot['asOf'], 'teams': report, 'hash': digest})
    return {'hash': digest, 'players': len(changed), 'format': format_name, 'asOf': snapshot['asOf']}
