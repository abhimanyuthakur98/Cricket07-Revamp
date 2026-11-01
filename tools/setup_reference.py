"""One-time cache of ICC member logos and public player role facts."""
from concurrent.futures import ThreadPoolExecutor
from html.parser import HTMLParser
import io
import json
from pathlib import Path
import re
import sys
import urllib.request
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from roster.teams import TEAMS

ROOT = Path(__file__).resolve().parents[1]


def fetch(url):
    with urllib.request.urlopen(url, timeout=60) as response:
        return response.read()


def main():
    from PIL import Image
    metadata = {}
    research = 'https://raw.githubusercontent.com/syedharis14/cricket07-2026-squads/main/research/'
    listing = json.loads(fetch('https://api.github.com/repos/syedharis14/cricket07-2026-squads/contents/research'))
    def role_file(entry):
        data = json.loads(fetch(research + entry['name']))
        keys = ('name', 'first', 'last', 'scoreboard', 'role', 'bat_hand', 'bowl_arm', 'bowl_style', 'formats', 'captain_formats', 'wk_formats', 'first_choice_wk')
        return data['team'], {'source': entry['download_url'], 'sources': data.get('sources', []),
                              'asOf': data.get('as_of'),
                              'players': [{k:p.get(k) for k in keys} for p in data['players']]}
    with ThreadPoolExecutor(max_workers=4) as executor:
        for team, facts in executor.map(role_file, listing):
            metadata[team] = facts
    (ROOT / 'roster/player_metadata.json').write_text(json.dumps(metadata, indent=2), encoding='utf-8')
    members = {}
    decoder = json.JSONDecoder()
    for region in ('africa', 'americas', 'asia', 'pacific', 'europe'):
        html = fetch('https://www.icc-cricket.com/about/members/' + region).decode()
        chunks = [json.loads(m)[1] for m in re.findall(r'self\.__next_f\.push\((\[1,".*?"])\)', html)]
        text = ''.join(chunks)
        for match in re.finditer(r'\{"type":"customentity"', text):
            try:
                item, _ = decoder.raw_decode(text[match.start():])
            except ValueError:
                continue
            if item.get('entityCode') == 'member_association':
                members[item['title']] = item
    assets = ROOT / 'web/assets/teams'
    assets.mkdir(parents=True, exist_ok=True)
    (ROOT / 'local_runtime/research/members.json').write_text(json.dumps(members), encoding='utf-8')
    records = {}
    class Images(HTMLParser):
        def handle_starttag(self, tag, attrs):
            fields = dict(attrs)
            if tag == 'img' and ('/member_association/' in fields.get('src', '') or (fields.get('width') == '140' and fields.get('height') == '30' and fields.get('class') == 'm-auto')):
                self.url = fields['src']
    def badge(team):
        fallbacks = {
            'Zimbabwe': ('https://en.wikipedia.org/wiki/Zimbabwe_Cricket', 'https://upload.wikimedia.org/wikipedia/en/thumb/4/48/Zimbabwe_Cricket_%28logo%29.svg/250px-Zimbabwe_Cricket_%28logo%29.svg.png'),
            'United States of America': ('https://en.wikipedia.org/wiki/USA_Cricket', 'https://upload.wikimedia.org/wikipedia/en/thumb/7/7e/USA_Cricket_logo.svg/250px-USA_Cricket_logo.svg.png'),
            'Bermuda': ('https://cricketbermuda.com/', 'https://cricketbermuda.com/wp-content/uploads/2020/07/BCB-logo-1.png'),
        }
        key = 'USA' if team == 'United States of America' else team
        member = members.get(key)
        if key == 'USA':
            member = member or members.get('United States of America') or members.get('United States')
        if not member:
            member = next((m for title, m in members.items() if key.lower() in title.lower() or key.lower() in m.get('fields', {}).get('name', '').lower()), None)
        if not member:
            raise ValueError('ICC member missing: ' + team + '; found ' + ', '.join(members))
        page_url = member['url']
        parser = Images()
        if team in fallbacks:
            page_url, parser.url = fallbacks[team]
        else:
            profile = fetch(page_url).decode()
            parser.feed(profile)
        if not getattr(parser, 'url', None):
            raise ValueError('ICC badge image missing: ' + team + ' ' + page_url)
        target = assets / (TEAMS[team][1] + '.png')
        image = Image.open(target if target.exists() else io.BytesIO(fetch(parser.url))).convert('RGBA')
        image.thumbnail((256,256), Image.Resampling.LANCZOS)
        image.save(target)
        print('Badge cached:', team, image.size, flush=True)
        return team, {'path': str(target.relative_to(ROOT / 'web')).replace('\\', '/'),
                      'source': page_url, 'imageUrl': parser.url,
                      'rights': 'Team/board trademarks. Source attribution retained for this game modification; no ownership or endorsement claimed.'}
    for team in TEAMS:
        try:
            key, record = badge(team)
            records[key] = record
        except Exception as error:
            raise RuntimeError('Badge setup failed for ' + team) from error
    (assets / 'sources.json').write_text(json.dumps(records, indent=2), encoding='utf-8')
    print('Reference assets ready.', flush=True)


if __name__ == '__main__':
    main()
