"""Cache one-time badge replacements, preserving texture names and unrelated teams."""
import hashlib
import json
import re
import struct
from collections import deque
from .refresh import ROOT
from .teams import TEAMS


def transparent_background(image):
    """Interpret edge-connected white matte as transparent during texture encoding.

    Source artwork stays unchanged. Enclosed white stars, lettering, tiger fur and
    shield details remain opaque; already-transparent artwork is preserved.
    """
    image = image.convert('RGBA').copy()
    width, height = image.size
    pixels = image.load()
    visited = set()
    queue = deque((x,y) for x in range(width) for y in (0,height-1))
    queue.extend((x,y) for y in range(height) for x in (0,width-1))
    while queue:
        x,y = queue.popleft()
        if (x,y) in visited:
            continue
        visited.add((x,y))
        r,g,b,a = pixels[x,y]
        if a > 0 and not (min(r,g,b) >= 220 and max(r,g,b)-min(r,g,b) <= 30):
            continue
        pixels[x,y] = (r,g,b,0)
        for nx,ny in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)):
            if 0 <= nx < width and 0 <= ny < height and (nx,ny) not in visited:
                queue.append((nx,ny))
    return image


def logo_replacements(archive):
    from PIL import Image, ImageOps
    directory = ROOT / 'web/assets/teams'
    paths = {slug: directory / (slug + '.png') for _, slug in TEAMS.values()}
    missing = [slug for slug, path in paths.items() if not path.exists()]
    if missing:
        raise ValueError('Missing logo assets: ' + ', '.join(missing))
    fingerprint = hashlib.sha256(b'edge-matte-alpha-v1' + b''.join(paths[k].read_bytes() for k in sorted(paths))).hexdigest()
    cache = ROOT / 'local_runtime/badges'
    cache.mkdir(parents=True, exist_ok=True)
    index = cache / 'index.json'
    if index.exists():
        saved = json.loads(index.read_text())
        if saved['fingerprint'] == fingerprint:
            return {name: (cache / name).read_bytes() for name in saved['files']}
    result = {}
    images = {slug: transparent_background(Image.open(path)) for slug,path in paths.items()}
    for name in archive.entries:
        if not name.endswith('.fsh'):
            continue
        head = archive.read(name, prefix=1024)
        if head[:4] != b'SHPI':
            continue
        count = struct.unpack_from('<I', head, 8)[0]
        if count > 100 or 16 + count * 8 > len(head):
            continue
        # Only candidate badge atlases; no stadium, kit or face processing.
        if not any(head[16+i*8:18+i*8] == b'fl' for i in range(count)):
            continue
        data = archive.read(name)
        offsets = [struct.unpack_from('<I', data, 20 + i*8)[0] for i in range(count)]
        sections = []
        modified = False
        for i, start in enumerate(offsets):
            end = offsets[i+1] if i+1 < count else len(data)
            section = data[start:end]
            label = re.search(rb'\x70\x10\x00\x00((?:fl|l1|l2|l3)[a-z0-9]+)\x00', section)
            if label:
                slug = label[1][2:].decode('ascii')
                if slug == 'sct':
                    slug = 'sco'
                if slug in images:
                    width,height = struct.unpack_from('<HH', section, 4)
                    fitted = ImageOps.contain(images[slug], (width,height), Image.Resampling.LANCZOS)
                    canvas = Image.new('RGBA', (width,height), (0,0,0,0))
                    canvas.alpha_composite(fitted, ((width-fitted.width)//2,(height-fitted.height)//2))
                    rgba = canvas.tobytes('raw', 'BGRA')
                    old_size = struct.unpack_from('<I', section, 0)[0] >> 8
                    if not 16 <= old_size <= len(section):
                        raise ValueError('Unsupported badge texture block')
                    size = 16 + len(rgba)
                    header = bytearray(section[:16])
                    struct.pack_into('<I', header, 0, (size << 8) | 0x7d)
                    section = bytes(header) + rgba + section[old_size:]
                    modified = True
            sections.append(section)
        if modified:
            # Keep the original directory, tag and alignment prefix before the first image.
            output = bytearray(data[:offsets[0]])
            for i, section in enumerate(sections):
                struct.pack_into('<I', output, 20+i*8, len(output))
                output.extend(section)
            struct.pack_into('<I', output, 4, len(output))
            result[name] = bytes(output)
            (cache / name).write_bytes(output)
    if not result:
        raise ValueError('No matching game badge textures found')
    index.write_text(json.dumps({'fingerprint':fingerprint,'files':list(result)}))
    return result
