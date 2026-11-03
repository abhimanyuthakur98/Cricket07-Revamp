"""Verify every hosted game chunk, byte count, hash and required launch asset."""
import gzip
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]/'dist-vercel'


def main():
    m=json.loads((ROOT/'play/game/manifest.json').read_text())
    for f in m['files']:
        digest=hashlib.sha1();size=0
        for i,n in enumerate(f['parts']):
            path=ROOT/'play/game'/(f['src']+f'.{i:03d}.gz')
            assert path.stat().st_size==n,path
            data=gzip.decompress(path.read_bytes());digest.update(data);size+=len(data)
        assert size==f['size'],f['path']
        assert digest.hexdigest().startswith(f['hash']),f['path']
    for f in ('T20','ODI','Test'):
        assert (ROOT/'play/rosters'/f'{f}.cdf').stat().st_size==620140
    for p in ('play/index.html','play/c07.js','play/build/cricket07.js','play/build/cricket07.wasm','play/inter-latin.woff2','local-launch.js','broadcast.js','broadcast-state.js','broadcast.css','engine-layout.mjs','squad-ratings.mjs','data/playtest.json'):
        assert (ROOT/p).stat().st_size>0,p
    assert b'\0asm'==(ROOT/'play/build/cricket07.wasm').read_bytes()[:4]
    loader=(ROOT/'play/c07.js').read_text()
    assert '.revamp-hashes.json' in loader
    assert 'window.revampAttach(M)' in loader
    print('Complete hosted game verified: all chunks, hashes, audio, runtime and three roster formats.')
    print((ROOT/'deployment-report.json').read_text())


if __name__=='__main__':main()
