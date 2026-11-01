"""Cache one-time badge replacements, preserving texture names and unrelated teams."""
import hashlib
import json
import re
import struct
from .refresh import ROOT
from .teams import TEAMS


def logo_replacements(archive):
    from PIL import Image, ImageOps
    directory = ROOT / 'web/assets/teams'
    paths = {slug: directory / (slug + '.png') for _, slug in TEAMS.values()}
    missing = [slug for slug, path in paths.items() if not path.exists()]
    if missing:
        raise ValueError('Missing logo assets: ' + ', '.join(missing))
    fingerprint = hashlib.sha256(b''.join(paths[k].read_bytes() for k in sorted(paths))).hexdigest()
    cache = ROOT / 'local_runtime/badges'
    cache.mkdir(parents=True, exist_ok=True)
    index = cache / 'index.json'
    if index.exists():
        saved = json.loads(index.read_text())
        if saved['fingerprint'] == fingerprint:
            return {name: (cache / name).read_bytes() for name in saved['files']}
    result = {}
    images = {slug: Image.open(path).convert('RGBA') for slug,path in paths.items()}
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
