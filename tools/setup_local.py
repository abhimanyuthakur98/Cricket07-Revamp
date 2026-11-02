"""Download the browser runtime with complete audio. Assets stay untracked."""
from concurrent.futures import ThreadPoolExecutor
import gzip
import hashlib
import json
from pathlib import Path
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[1] / 'local_runtime'
SITE = 'https://cricket07.dhaiwat.com/'


def fetch(url):
    with urllib.request.urlopen(url, timeout=180) as response:
        return response.read()


def main():
    public = ROOT / 'web'
    public.mkdir(parents=True, exist_ok=True)
    page = fetch(SITE).decode('utf-8')
    resources = ['c07.js', 'netplay.js', 'audio-worklet.js', 'cricket07-logo.png',
                 'favicon.ico', 'inter-latin.woff2', 'inter-latin-ext.woff2',
                 'inter-LICENSE.txt', 'build/cricket07.js', 'build/cricket07.wasm']
    (public / 'index.html').write_text(page, encoding='utf-8')
    for name in resources:
        target = public / name
        if target.exists():
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        print('Runtime:', name, flush=True)
        target.write_bytes(fetch(SITE + name))
    manifest = json.loads(fetch(SITE + 'game/manifest.json'))
    selected = [f for f in manifest['files'] if
                (f['path'].lower() in ('audio/music.big', 'audio/pbp.big') and f.get('mode') == 'full') or
                (f['path'].lower() not in ('audio/music.big', 'audio/pbp.big') and (not f.get('mode') or f['mode'] == 'lite'))]
    print('Installing game files with full audio:', sum(f['size'] for f in selected) // 1_000_000, 'MB', flush=True)
    def install(entry):
        target = ROOT / 'game' / entry['path']
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_suffix(target.suffix + '.download')
        if temporary.exists() and temporary.stat().st_size == entry['size']:
            if hashlib.sha1(temporary.read_bytes()).hexdigest().startswith(entry['hash']):
                temporary.replace(target)
        if target.exists() and target.stat().st_size == entry['size']:
            if not hashlib.sha1(target.read_bytes()).hexdigest().startswith(entry['hash']):
                raise ValueError('Existing file hash mismatch: ' + entry['path'])
            print('Already present:', entry['path'], flush=True)
            return
        source = entry.get('src', entry['path'])
        encoded = '/'.join(urllib.parse.quote(p) for p in source.split('/'))
        with temporary.open('wb') as output:
            if entry.get('parts'):
                for i, _ in enumerate(entry['parts']):
                    url = manifest['base'] + encoded + f'.{i:03d}.gz?v=' + entry['hash']
                    output.write(gzip.decompress(fetch(url)))
                    print(entry['path'], f'part {i+1}/{len(entry["parts"])}', flush=True)
            else:
                output.write(fetch(manifest['base'] + encoded + '?v=' + entry['hash']))
        if temporary.stat().st_size != entry['size']:
            raise ValueError('Size mismatch: ' + entry['path'])
        digest = hashlib.sha1(temporary.read_bytes()).hexdigest()
        if not digest.startswith(entry['hash']):
            raise ValueError('Hash mismatch: ' + entry['path'])
        temporary.replace(target)
        print('Verified:', entry['path'], flush=True)
    with ThreadPoolExecutor(max_workers=4) as executor:
        list(executor.map(install, selected))
    local_manifest = dict(manifest)
    local_manifest['version'] = str(manifest['version']) + '-full-audio-v2'
    local_manifest.pop('base', None)
    local_manifest['files'] = [{k: v for k, v in f.items() if k in ('path', 'size', 'hash')}
                               for f in selected]
    (ROOT / 'game' / 'manifest.json').write_text(json.dumps(local_manifest), encoding='utf-8')
    print('Local runtime with full music and commentary ready.', flush=True)


if __name__ == '__main__':
    main()
