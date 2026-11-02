"""One-time generic skin-palette approximation from sourced player portraits.

This does not infer ethnicity or create an exact likeness. Height and weight are
not exposed by Cricket 07's Create Player editor and are not fabricated.
"""
from concurrent.futures import ThreadPoolExecutor
import io
import json
from pathlib import Path
import statistics
import sys
import urllib.request

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from roster.refresh import ROOT, atomic_json


def sample(image):
    image = image.convert('RGBA')
    w, h = image.size
    pixels = image.crop((round(w*.40),round(h*.29),round(w*.60),round(h*.51))).getdata()
    colors = [(r,g,b) for r,g,b,a in pixels if a>200 and r>g>b and r-b>15 and g-b<65 and r-g<85]
    if len(colors)<100:
        return None
    rgb = tuple(round(statistics.median(c[i] for c in colors)) for i in range(3))
    light = .2126*rgb[0]+.7152*rgb[1]+.0722*rgb[2]
    tone = next((tone for threshold,tone in [(180,2),(160,5),(135,9),(110,12),(85,15)] if light>=threshold),18)
    return {'skinPalette': tone, 'portraitSampleRGB': rgb,
            'method': 'Approximate generic palette from portrait cheek region; lighting affects accuracy.'}


def main():
    from PIL import Image
    profiles = json.loads((ROOT/'roster/player_profiles.json').read_text(encoding='utf-8'))
    output = ROOT/'roster/appearance_profiles.json'
    cached = json.loads(output.read_text(encoding='utf-8')) if output.exists() else {}
    def one(item):
        player_id, profile = item
        if player_id in cached or not profile.get('headshot'):
            return player_id, cached.get(player_id)
        try:
            url = profile['headshot']
            with urllib.request.urlopen(url,timeout=30) as response:
                data=response.read(4*1024*1024)
            result=sample(Image.open(io.BytesIO(data)))
            return player_id, {**result,'source':url,'name':profile['name']} if result else None
        except Exception as error:
            print('Portrait unavailable:',player_id,str(error),flush=True)
            return player_id,None
    with ThreadPoolExecutor(max_workers=4) as pool:
        for player_id, result in pool.map(one,profiles.items()):
            if result:
                cached[player_id]=result
    atomic_json(output,cached)
    print('Generic appearance references:',len(cached),flush=True)


if __name__=='__main__':
    main()
