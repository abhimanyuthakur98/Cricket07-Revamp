"""Minimal BIGF reader and bounded EA RefPack decoder, with append-only replacement."""
import struct


def expand(payload, prefix=None):
    if len(payload) < 5 or payload[1] != 0xfb or payload[0] & 0x3e != 0x10:
        return payload
    width = 4 if payload[0] & 0x80 else 3
    cursor = 2 + (width if payload[0] & 1 else 0)
    expected = int.from_bytes(payload[cursor:cursor + width], 'big')
    if expected > 100_000_000:
        raise ValueError('Unreasonable expanded member size')
    cursor += width
    output = bytearray()
    def take(count):
        nonlocal cursor
        block = payload[cursor:cursor + count]
        if len(block) != count:
            raise ValueError('Truncated RefPack block')
        cursor += count
        return block
    while cursor < len(payload):
        if prefix is not None and len(output) >= prefix:
            return bytes(output[:prefix])
        command = take(1)[0]
        distance = length = 0
        if command >= 0xfc:
            output.extend(take(command & 3))
            break
        if command >= 0xe0:
            literals = ((command & 31) + 1) * 4
        elif command >= 0xc0:
            a, b, c = take(3)
            literals = command & 3
            length = ((command & 12) << 6) + c + 5
            distance = ((command & 16) << 12) + a * 256 + b + 1
        elif command >= 0x80:
            a, b = take(2)
            literals = a >> 6
            length = (command & 63) + 4
            distance = ((a & 63) << 8) + b + 1
        else:
            a = take(1)[0]
            literals = command & 3
            length = ((command >> 2) & 7) + 3
            distance = ((command & 96) << 3) + a + 1
        output.extend(take(literals))
        if distance:
            if distance > len(output):
                raise ValueError('Invalid RefPack back reference')
            for _ in range(length):
                output.append(output[-distance])
        if len(output) > expected:
            raise ValueError('RefPack expanded past its declared size')
    if len(output) != expected:
        raise ValueError('RefPack size mismatch')
    return bytes(output)


class BigArchive:
    def __init__(self, path):
        self.path = path
        self.entries = {}
        with open(path, 'rb') as stream:
            head = stream.read(16)
            if head[:4] != b'BIGF':
                raise ValueError('Expected a BIGF archive')
            count, header_size = struct.unpack_from('>II', head, 8)
            index = stream.read(header_size - 16)
            cursor = 0
            for _ in range(count):
                position = cursor + 16
                offset, size = struct.unpack_from('>II', index, cursor)
                cursor += 8
                end = index.index(0, cursor)
                name = index[cursor:end].decode('ascii')
                cursor = end + 1
                self.entries[name] = (offset, size, position)

    def read(self, name, prefix=None):
        offset, size, _ = self.entries[name]
        with open(self.path, 'rb') as stream:
            stream.seek(offset)
            return expand(stream.read(size), prefix=prefix)

    def replace_into(self, target, replacements):
        import shutil
        shutil.copyfile(self.path, target)
        with open(target, 'r+b') as stream:
            for name, content in replacements.items():
                _, _, index_position = self.entries[name]
                stream.seek(0, 2)
                offset = stream.tell()
                stream.write(content)  # Uncompressed BIGF members are supported by the game.
                stream.seek(index_position)
                stream.write(struct.pack('>II', offset, len(content)))
            stream.seek(0, 2)
            size = stream.tell()
            stream.seek(4)
            stream.write(struct.pack('<I', size))  # EA BIGF's total size is little endian.
