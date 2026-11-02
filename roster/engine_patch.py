"""Preserve the supplied XI before the native Selections screen is built.

Inject two small hooks into the supported browser build's auto-selection routine.
The original selector still assigns keeper, bowling and fielding duties. It sees
only the starting XI; immediately before its final fielding rebuild we restore
reserves and the supplied batting order. No polling of a partly drawn UI.
"""
import hashlib
import json
from .refresh import ROOT

SUPPORTED_SHA256 = '8f04a1da726f2fea836aafb3a9eb5b73853b467d765798218932a59156574fdf'
VERSION = 'ordered-xi-reserves-v1'
FLAGS = 0x00b00000  # Unallocated guest-address gap after PE image, below guest heap.
TARGET = 'f_00417330'
FINALIZE = 'f_00414950'


def uint(value):
    out = bytearray()
    while True:
        byte = value & 127
        value >>= 7
        out.append(byte | (128 if value else 0))
        if not value:
            return bytes(out)


def sint(value):
    out = bytearray()
    while True:
        byte = value & 127
        value >>= 7
        done = (value == 0 and not byte & 64) or (value == -1 and byte & 64)
        out.append(byte | (0 if done else 128))
        if done:
            return bytes(out)


def read_uint(data, pos):
    result = shift = 0
    while True:
        byte = data[pos]
        pos += 1
        result |= (byte & 127) << shift
        if byte < 128:
            return result, pos
        shift += 7


def string(data, pos):
    size, pos = read_uint(data, pos)
    return data[pos:pos+size].decode(), pos+size


def sections(data):
    if data[:8] != b'\0asm\x01\0\0\0':
        raise ValueError('Invalid browser engine')
    pos = 8
    result = []
    while pos < len(data):
        kind = data[pos]
        size, start = read_uint(data, pos+1)
        result.append((kind, data[start:start+size]))
        pos = start+size
    return result


def function_names(parts):
    for kind, payload in parts:
        if kind != 0:
            continue
        name, pos = string(payload, 0)
        if name != 'name':
            continue
        while pos < len(payload):
            subsection = payload[pos]
            size, start = read_uint(payload, pos+1)
            if subsection == 1:
                count, cursor = read_uint(payload, start)
                names = {}
                for _ in range(count):
                    index, cursor = read_uint(payload, cursor)
                    text, cursor = string(payload, cursor)
                    names[text] = index
                return names
            pos = start+size
    raise ValueError('Browser build has no function symbols')


def imported_functions(payload):
    count, pos = read_uint(payload, 0)
    functions = 0
    for _ in range(count):
        _, pos = string(payload, pos)
        _, pos = string(payload, pos)
        kind, pos = payload[pos], pos+1
        if kind == 0:
            _, pos = read_uint(payload, pos)
            functions += 1
        elif kind in (1, 2):
            if kind == 1:
                pos += 1  # funcref
            flags, pos = read_uint(payload, pos)
            _, pos = read_uint(payload, pos)
            if flags & 1:
                _, pos = read_uint(payload, pos)
        elif kind == 3:
            pos += 2
        elif kind == 4:
            _, pos = read_uint(payload, pos)
            _, pos = read_uint(payload, pos)
        else:
            raise ValueError('Unsupported Wasm import kind')
    return functions


# Wasm instruction helpers. All guest accesses allow byte alignment.
def c(value): return b'\x41' + sint(value)
def get(index): return b'\x20' + uint(index)
def put(index): return b'\x21' + uint(index)
def load(offset=0, op=0x28): return bytes([op, 0]) + uint(offset)
def store(offset=0, op=0x36): return bytes([op, 0]) + uint(offset)
ADD, SUB, MUL, AND = b'\x6a', b'\x6b', b'\x6c', b'\x71'
COPY, FILL = b'\xfc\x0a\0\0', b'\xfc\x0b\0'
IF, END = b'\x04\x40', b'\x0b'


def hooks():
    # Original locals 1..12 are untouched. New locals:
    # 13 guest base, 14 team ID, 15 side, 16 team pointer, 17 enabled,
    # 18 app pointer, 19 reserve count, 20/21 saved i64s, 22 saved u16.
    entry = c(559428)+load()+put(13)
    this = get(13)+get(0)+load(4)+ADD
    entry += this+load(56)+put(14)+this+load(52)+put(15)
    entry += get(13)+c(0x817d48)+ADD+get(14)+c(2808)+MUL+ADD+put(16)
    entry += get(14)+c(67)+b'\x49'+get(15)+c(2)+b'\x49'+AND+IF
    entry += get(13)+c(FLAGS)+ADD+get(14)+ADD+load(op=0x2d)+c(1)+b'\x46'
    entry += get(16)+load(40)+get(14)+b'\x46'+AND+put(17)
    entry += get(17)+IF
    entry += get(16)+load(22,0x29)+put(20)+get(16)+load(30,0x29)+put(21)
    entry += get(16)+load(38,0x2f)+put(22)
    entry += get(16)+c(22)+ADD+c(0)+c(18)+FILL
    entry += END+END

    final = get(17)+IF
    final += get(13)+get(0)+load(4)+ADD+c(224)+SUB+put(18)
    final += get(18)+c(0xfc)+ADD+get(15)+c(22)+MUL+ADD+get(16)+c(22)+COPY
    final += get(16)+get(20)+store(22,0x37)+get(16)+get(21)+store(30,0x37)
    final += get(16)+get(22)+store(38,0x3b)
    final += get(18)+c(0x168)+ADD+get(15)+c(18)+MUL+ADD+get(16)+c(22)+ADD+c(18)+COPY
    # The engine stores the last reserve index, not its length.
    final += c(0)+put(19)
    for index in range(9):
        final += get(16)+load(22+index*2,0x2f)+IF+get(19)+c(1)+ADD+put(19)+END
    final += get(18)+c(0x18c)+ADD+get(15)+ADD
    final += get(19)+b'\x04\x7f'+get(19)+c(1)+SUB+b'\x05'+c(0)+END+store(op=0x3a)
    final += get(13)+c(0x92f8c0)+ADD+get(15)+c(2808)+MUL+ADD+get(16)+c(40)+COPY
    final += END
    return entry, final


def patch(data):
    if hashlib.sha256(data).hexdigest() != SUPPORTED_SHA256:
        raise ValueError('Unsupported browser engine for ordered XIs; keep the supported local runtime')
    parts = sections(data)
    names = function_names(parts)
    imported = imported_functions(next(p for k,p in parts if k == 2))
    target = names[TARGET]-imported
    call = b'\x10'+uint(names[FINALIZE])
    entry, final = hooks()
    output = bytearray(data[:8])
    for kind, payload in parts:
        if kind == 10:
            count, pos = read_uint(payload, 0)
            bodies = []
            for index in range(count):
                size, start = read_uint(payload, pos)
                body = payload[start:start+size]
                if index == target:
                    groups, cursor = read_uint(body, 0)
                    local_count, cursor = read_uint(body, cursor)
                    if groups != 1 or local_count != 12 or body[cursor] != 0x7f or body.count(call) != 1:
                        raise ValueError('Unexpected selector function layout')
                    instructions = body[cursor+1:]
                    at = instructions.index(call)
                    locals_header = uint(4)+uint(12)+b'\x7f'+uint(7)+b'\x7f'+uint(2)+b'\x7e'+uint(1)+b'\x7f'
                    body = locals_header+entry+instructions[:at]+final+instructions[at:]
                bodies.append(uint(len(body))+body)
                pos = start+size
            payload = uint(count)+b''.join(bodies)
        output += bytes([kind])+uint(len(payload))+payload
    return bytes(output)


def prepare():
    source = ROOT/'local_runtime/web/build/cricket07.wasm'
    target = ROOT/'local_runtime/prepared/cricket07.wasm'
    stamp = target.with_suffix('.version')
    original = source.read_bytes()
    if hashlib.sha256(original).hexdigest() != SUPPORTED_SHA256:
        raise ValueError('Unsupported browser engine for ordered XIs; keep the supported local runtime')
    if target.exists() and stamp.exists():
        try:
            saved = json.loads(stamp.read_text())
            if saved.get('version') == VERSION and saved.get('sha256') == hashlib.sha256(target.read_bytes()).hexdigest():
                return target
        except ValueError:
            pass
    target.parent.mkdir(parents=True, exist_ok=True)
    data = patch(original)
    temporary = target.with_suffix('.tmp')
    temporary.write_bytes(data)
    temporary.replace(target)
    stamp.write_text(json.dumps({'version': VERSION, 'sha256': hashlib.sha256(data).hexdigest()}))
    return target


if __name__ == '__main__':
    print(prepare())

