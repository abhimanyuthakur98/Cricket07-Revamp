"""Build a complete static playtest deployment; game binaries never enter Git.

Vercel's Git build downloads the verified runtime, prepares the curated squads,
then serves compressed game chunks directly from the CDN (no large Functions).
"""
import gzip
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
OUT=ROOT/'dist-vercel'
PART=8*1024*1024


def write_json(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,separators=(',',':')),encoding='utf-8')


def chunk_file(source,folder,relative):
    digest=hashlib.sha1(source.read_bytes()).hexdigest()[:12]
    rel='files/'+digest+'/'+relative
    target=folder/rel
    target.parent.mkdir(parents=True,exist_ok=True)
    sizes=[]
    with source.open('rb') as stream:
        for index in range((source.stat().st_size+PART-1)//PART):
            payload=gzip.compress(stream.read(PART),compresslevel=6,mtime=0)
            path=Path(str(target)+f'.{index:03d}.gz')
            if not path.exists() or path.stat().st_size!=len(payload):
                path.write_bytes(payload)
            sizes.append(len(payload))
    return {'path':relative,'src':rel,'size':source.stat().st_size,
            'hash':digest,'part':PART,'parts':sizes}


def main():
    try:
        import PIL
    except ImportError:
        environment=ROOT/'local_runtime/build-venv'
        subprocess.run([sys.executable,'-m','venv',str(environment)],check=True)
        python=environment/('Scripts/python.exe' if sys.platform=='win32' else 'bin/python')
        subprocess.run([str(python),'-m','pip','install','-r',str(ROOT/'requirements-local.txt')],check=True)
        subprocess.run([str(python),str(Path(__file__).resolve())],check=True)
        return
    from tools.setup_local import main as setup
    setup()
    from roster.refresh import refresh
    from roster.game_patch import prepare
    from roster.ui_engine import prepare as engine
    snapshot=refresh()
    result=prepare(snapshot,'T20',broadcast_ui=True)
    for f in ('ODI','Test'):
        prepare(snapshot,f,database_only=True,broadcast_ui=True)
    wasm=engine()
    OUT.mkdir(parents=True,exist_ok=True)
    web=ROOT/'web'
    for name in ['assets','data']:
        shutil.copytree(web/name,OUT/name,dirs_exist_ok=True)
    for name in ['rosters.html','rosters.js','roster-runtime.js','broadcast.js','broadcast-state.js','broadcast.css']:
        shutil.copy2(web/name,OUT/name)
    shutil.copy2(web/'hosted-launch.js',OUT/'local-launch.js')
    runtime=ROOT/'local_runtime/web'
    play=OUT/'play';play.mkdir(exist_ok=True)
    for path in runtime.iterdir():
        if path.is_file() and path.name not in ('index.html','c07.js'):
            shutil.copy2(path,play/path.name)
    (play/'build').mkdir(exist_ok=True)
    shutil.copy2(runtime/'build/cricket07.js',play/'build/cricket07.js')
    shutil.copy2(wasm,play/'build/cricket07.wasm')
    source=(runtime/'index.html').read_text(encoding='utf-8')
    source=re.sub(r'<div id="hire".*?</script>','',source,flags=re.S)
    source=re.sub(r'<p class="credit">.*?</p>','<p class="credit">Cricket 07 Revamp · Original game copyright of EA Sports</p>',source,flags=re.S)
    source=re.sub(r'<script type="module" src="https://static.cloudflareinsights.com/[^>]+></script>','',source)
    source=source.replace('<title>Cricket 07</title>','<title>Cricket 07 Revamp · Playtest</title>')
    source=source.replace('<span id="visits">2,693,467 visits</span>','')
    source=source.replace('</head>','<link rel="stylesheet" href="/broadcast.css"><style>#go-online{display:none!important}</style></head>')
    source=source.replace('<body>','<body data-broadcast-ui="true"><div style="position:fixed;top:12px;left:12px;z-index:30;background:#111c16;padding:10px;border-radius:8px"><a href="/rosters.html" style="color:#6de1b0">Player preview</a><p id="revamp-message" style="font-size:12px">Playtest · squads follow the in-game overs.</p></div>')
    source=source.replace('<script src="c07.js"></script>','<script src="/local-launch.js"></script><script src="c07.js"></script>')
    (play/'index.html').write_text(source,encoding='utf-8')
    loader=(runtime/'c07.js').read_text(encoding='utf-8')
    if loader.count('window.c07 = M;')!=1 or loader.count('async function run(session) {')!=1:
        raise ValueError('Unsupported browser launcher')
    loader=loader.replace('window.c07 = M;','window.c07 = M; window.revampAttach(M);')
    loader=loader.replace('async function run(session) {',"async function run(session) {\n if(window.revampLaunching)return; window.revampLaunching=true; if(session)throw new Error('This playtest supports solo matches.'); try{await window.revampBeforeLaunch();}catch(e){window.revampLaunching=false;throw e;}")
    # Invalidate changed files by hash, rather than mistaking an old equal-sized
    # archive for a complete current download. Record hashes before downloading
    # so an interrupted download still resumes on the next visit.
    install="""let oldHashes={};
      try { oldHashes=JSON.parse(await (await (await fileHandle(dir,'.revamp-hashes.json',false)).getFile()).text()); } catch {}
      for(const f of files) if(oldHashes[f.path]!==f.hash) await removeAt(dir,f.path).catch(()=>{});
      const hashWriter=await (await fileHandle(dir,'.revamp-hashes.json',true)).createWritable();
      await hashWriter.write(JSON.stringify(Object.fromEntries(files.map(f=>[f.path,f.hash]))));await hashWriter.close();
      await downloadAll(files, prog);"""
    if loader.count('await downloadAll(files, prog);')!=1:
        raise ValueError('Unsupported browser installer')
    loader=loader.replace('await downloadAll(files, prog);',install)
    (play/'c07.js').write_text(loader,encoding='utf-8')
    roster_dir=play/'rosters';roster_dir.mkdir(exist_ok=True)
    formats={}
    for f in ('T20','ODI','Test'):
        data=ROOT/'local_runtime/prepared-ui'/f'{f}.cdf'
        shutil.copy2(data,roster_dir/data.name)
        formats[f]='/play/rosters/'+data.name
    manifest=json.loads((ROOT/'local_runtime/game/manifest.json').read_text())
    game=play/'game';files=[]
    for entry in manifest['files']:
        rel=entry['path']
        src=ROOT/'local_runtime/game'/rel
        if rel=='Data/data.gob':src=ROOT/'local_runtime/prepared-ui/Data/data.gob'
        print('Packaging:',rel,flush=True)
        files.append(chunk_file(src,game,rel))
    version=hashlib.sha256((json.dumps(files)+hashlib.sha256(wasm.read_bytes()).hexdigest()+json.dumps(formats)).encode()).hexdigest()[:20]
    write_json(game/'manifest.json',{'version':'revamp-'+version,'files':files})
    write_json(OUT/'data/playtest.json',{'version':version,'asOf':snapshot['asOf'],'formats':formats})
    write_json(OUT/'deployment-report.json',{'version':version,'gameFiles':len(files),'downloadBytes':sum(sum(f['parts']) for f in files),'largestChunkBytes':max(max(f['parts']) for f in files),'formats':list(formats),'broadcast':True})
    print('Complete Vercel playtest build:',OUT,flush=True)


if __name__=='__main__':main()

