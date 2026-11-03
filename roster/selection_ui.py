"""Hide the native legacy team ratings while retaining their control objects.

Only generated archives change. Native handlers still find the same IDs; logos,
team arrows and all navigation keep their original XML and appearance.
"""
import re
import struct
from .archive import expand

PACKAGES = {
    '17a9f0c56eaaeb65f3773e549620b95f.big': {'fe_playnow_teamselect.rfe'},
    '07dcf08f10821076c608a7c01222f014.big': {'ko_teamselect.rfe'},
    'bd02c7e50e9c165b5ca754011e7a67ba.big': {'ts_teamselect.rfe'},
    'b563ba8e570ab5294d466752a853e294.big': {'ws_teamselect.rfe'},
    '846bf835a621a435a2366a391dcfa4eb.big': {'wc_teamselect.rfe', 'wc07_teamselect.rfe'},
}


def hide_legacy_ratings(xml):
    def node(match):
        tag, attrs = match[1], match[2]
        is_rating = (tag == b'Slider' or
                     tag == b'GraphicButton' and re.search(rb'Texture\s*=\s*"rate\d+"', attrs) or
                     tag == b'TextButton' and re.search(rb'Text\s*=\s*"\$[567]"', attrs))
        if not is_rating:
            return match[0]
        attrs = re.sub(rb'((?:BGColor|CaretColor|FontColor)\s*=\s*")[0-9a-fA-F]{8}(\")',
                       rb'\g<1>00000000\2', attrs)
        return b'<' + tag + attrs + b'>'
    return re.sub(rb'<(GraphicButton|Slider|TextButton)(\s[^>]*?)>', node, xml)


def patch_package(data, names):
    if data[:4] != b'BIGF':
        raise ValueError('Unsupported team-selection archive')
    count, header_size = struct.unpack_from('>II', data, 8)
    output = bytearray(data)
    cursor = 16
    for _ in range(count):
        offset, size = struct.unpack_from('>II', data, cursor)
        end = data.index(0, cursor + 8)
        name = data[cursor + 8:end].decode('ascii')
        if name in names:
            original = expand(data[offset:offset + size])
            patched = hide_legacy_ratings(original)
            struct.pack_into('>II', output, cursor, len(output), len(patched))
            output.extend(patched)
        cursor = end + 1
    if cursor > header_size:
        raise ValueError('Invalid team-selection archive index')
    struct.pack_into('<I', output, 4, len(output))
    return bytes(output)


def selection_replacements(archive):
    return {name: patch_package(archive.read(name), screens) for name, screens in PACKAGES.items()}
