"""Remove the six over-count icons from the broadcast build's bowling gauge.

The pinned compiled RFE uses string-table references for dimensions. Keep the
graphic objects and IDs so native over updates still find them, but give only
the twelve ball/background sprites zero width and height. Power/release,
special-delivery controls, spin and radar retain their original geometry.
"""
import hashlib
import struct
from .archive import expand

PACKAGE = '7ac69a95d810236a72e073135195d310.big'
SCREEN = 'ig_scorebox.rfe'
SCREEN_SHA256 = '88687d8aaf136e2e5926f8d522a4f363b8fe0d6398045cabb2f6e0700117f053'
BALL_NODES = tuple(range(7532, 8300, 64))


def hide_gauge_balls(data):
    if hashlib.sha256(data).hexdigest() != SCREEN_SHA256:
        raise ValueError('Unsupported bowling-gauge layout')
    output = bytearray(data)
    # The GraphicButton token (0x521) establishes this RFE's string-table base.
    strings = data.index(b'GraphicButton\0') - 0x521
    zero = data.index(b'\x000.000000\0', strings) + 1 - strings
    for node in BALL_NODES:
        # Width/Height attribute names and their original 16.000000 value.
        for offset, attribute in [(30, 0x4f8), (34, 0x509)]:
            key, value = struct.unpack_from('<HH', data, node + offset)
            if key != attribute or not data[strings + value:].startswith(b'16.000000\0'):
                raise ValueError('Unexpected bowling-ball dimensions')
            struct.pack_into('<H', output, node + offset + 2, zero)
    return bytes(output)


def bowling_replacements(archive):
    data = archive.read(PACKAGE)
    count, header_size = struct.unpack_from('>II', data, 8)
    output = bytearray(data)
    cursor, found = 16, False
    for _ in range(count):
        offset, size = struct.unpack_from('>II', data, cursor)
        end = data.index(0, cursor + 8)
        if data[cursor + 8:end].decode('ascii') == SCREEN:
            patched = hide_gauge_balls(expand(data[offset:offset + size]))
            struct.pack_into('>II', output, cursor, len(output), len(patched))
            output.extend(patched)
            found = True
        cursor = end + 1
    if not found or cursor > header_size:
        raise ValueError('Missing bowling-gauge screen')
    struct.pack_into('<I', output, 4, len(output))
    return {PACKAGE: bytes(output)}
