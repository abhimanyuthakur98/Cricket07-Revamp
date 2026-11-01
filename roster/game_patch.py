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
        aliases = [player.get('name'), player.get('scoreboard')]
        if player.get('first') and player.get('last'):
            aliases.append(''.join(part[0] for part in player['first'].split()) + player['last'])
        if key in [normalize(alias) for alias in aliases if alias]:
            return player
    # Surname + first initial must identify exactly one person within this team.
    tokens = name.replace('.', ' ').split()
    if len(tokens) > 1:
        matches = [p for p in candidates if normalize(p.get('last', '')) == normalize(tokens[-1])
                   and p.get('first', '?')[0].lower() == tokens[0][0].lower()]
        if len(matches) == 1:
            return matches[0]
    return None


def skills(record):
    return [(struct.unpack_from('<I', record, 108 + 4 * (i // 5))[0] >> (6 * (i % 5))) & 63 for i in range(40)]


def write_skills(record, values):
    for word in range(8):
        original = struct.unpack_from('<I', record, 108 + 4 * word)[0]
        packed = original & 0xc0000000
        for index in range(5):
            packed |= int(values[word * 5 + index]) << (index * 6)
        struct.pack_into('<I', record, 108 + 4 * word, packed)


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


def prepare(snapshot, format_name):
    original = ROOT / 'local_runtime/game/Data/data.gob'
    archive = BigArchive(original)
    database = bytearray(archive.read(DATABASE))
    if len(database) != 620140:
        raise ValueError('Unsupported game database version; original files were left untouched')
    metadata_file = ROOT / 'roster/player_metadata.json'
    metadata = json.loads(metadata_file.read_text(encoding='utf-8')) if metadata_file.exists() else {}
    overrides = json.loads((ROOT / 'roster/role_overrides.json').read_text(encoding='utf-8'))
    for team, facts in overrides.items():
        metadata.setdefault(team, {'players': []})['players'] = facts['players'] + metadata.get(team, {}).get('players', [])
    records = {}
    for offset in range(356, 356 + 1096 * 360, 360):
        record = bytes(database[offset:offset + 360])
        player_id = struct.unpack_from('<H', record, 8)[0]
        if player_id:
            records[player_id] = (offset, record)
    replacements, report, changed = {}, {}, set()
    for team in snapshot['formats'][format_name]['teams']:
        name = team['name']
        if name not in TEAMS:
            continue
        team_id, _ = TEAMS[name]
        start = 431980 + team_id * 2808
        slots = list(struct.unpack_from('<20H', database, start + 24))
        if len(set(slots)) != 20 or not all(slot in records for slot in slots):
            raise ValueError('Unrecognized team layout: ' + name)
        squad = list(team['players'])
        if len(squad) < 11:
            report[name] = {'skipped': 'Fewer than 11 recent players; original squad retained'}
            continue
        facts = {p['id']: role_for(p['name'], name, metadata) for p in squad}
        def keeper(p):
            fact = facts[p['id']]
            return bool((fact and fact.get('role') == 'wk') or p['stats']['stumpings'])
        def bowling(p):
            fact = facts[p['id']]
            return (fact and fact.get('role') in ('bowl', 'allround')) or p['stats']['legalBalls'] >= 60
        best_bat = sorted(squad, key=lambda p: p['ratings']['batting'] or 0, reverse=True)
        best_bowl = sorted([p for p in squad if bowling(p)], key=lambda p: p['ratings']['bowling'] or 0, reverse=True)
        first = next((p for p in best_bat if keeper(p)), None)
        chosen = [first] if first else []
        for player in best_bowl[:5]:
            if player not in chosen:
                chosen.append(player)
        for player in best_bat:
            if player not in chosen:
                chosen.append(player)
            if len(chosen) == 11:
                break
        chosen.sort(key=lambda p: p['ratings']['batting'] or 0, reverse=True)
        squad = chosen + [p for p in best_bat if p not in chosen]
        entries = []
        for slot, player in zip(slots, squad):
            offset, pristine = records[slot]
            record = bytearray(pristine)
            fact = facts[player['id']]
            is_keeper = keeper(player)
            if fact:
                style = STYLE.get((fact.get('bowl_arm'), fact.get('bowl_style')))
                pool = [r for _, r in records.values()
                        if (((r[141] >> 1) & 15) == 2) == is_keeper
                        and (style is None or (r[140] & 15) == style)]
                if pool:
                    donor = min(pool, key=lambda r: abs(sum(skills(r)[:14]) / 14 - 45))
                    record[108:142] = donor[108:142]
                record[141] = (record[141] & 0xfe) | int(fact.get('bat_hand') == 'L')
                if style is not None:
                    record[140] = (record[140] & 0xd0) | style
                    record[140] &= ~0x20
                else:
                    record[140] |= 0x20
            if is_keeper:
                record[141] = (record[141] & 0xe1) | 4
            elif (record[141] >> 1) & 15 == 2:
                record[141] &= 0xe1
            record[12:28] = game_name(player['name'])
            record[28:108] = bytes(80)  # Do not present the donor's career as the new player's.
            struct.pack_into('<H', record, 10, 0xffff)  # No incorrect 2006 commentary name.
            values = skills(record)
            for field, indices in (('batting', range(14)), ('bowling', range(18, 23))):
                rating = player['ratings'][field]
                if rating is not None:
                    shift(values, indices, 1 + rating * 61 / 99)
            write_skills(record, values)
            database[offset:offset + 360] = record
            changed.add(slot)
            entries.append({'id': player['id'], 'slot': slot, 'name': player['name'],
                            'displayName': record[12:28].split(b'\0')[0].decode('latin1'),
                            'ratings': player['ratings'], 'roleMetadata': bool(fact), 'keeper': is_keeper})
        # Original reserves must not remain in a current squad with fewer than 20 players.
        active_slots = slots[:len(squad)]
        padded = active_slots + [0] * (20 - len(active_slots))
        captain_index = next((i for i,p in enumerate(squad) if facts[p['id']] and
                              ('T20I' if format_name == 'T20' else format_name) in (facts[p['id']].get('captain_formats') or [])), 0)
        for copy_id in [team_id] + ({57: [61], 60: [62]}.get(team_id, [])):
            base = 431980 + copy_id * 2808
            struct.pack_into('<20H', database, base + 24, *padded)
            struct.pack_into('<H', database, base + 70, slots[captain_index])
        report[name] = entries
    replacements[DATABASE] = bytes(database)
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
    target = ROOT / 'local_runtime/prepared/Data/data.gob'
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix('.tmp')
    archive.replace_into(temporary, replacements)
    temporary.replace(target)
    digest = hashlib.sha256(target.read_bytes()).hexdigest()[:16]
    atomic_json(ROOT / 'local_runtime/prepared/report.json', {'format': format_name, 'asOf': snapshot['asOf'], 'teams': report, 'hash': digest})
    return {'hash': digest, 'players': len(changed), 'format': format_name, 'asOf': snapshot['asOf']}
