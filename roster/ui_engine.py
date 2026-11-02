"""Read-only delivery telemetry for the isolated broadcast UI engine.

The hook runs at the native score-commit entry, with the finalized delivery
result, before its counters reset or batters change ends. Only reserved memory
is written; CPU registers, native locals and simulation memory are untouched.
"""
import hashlib
import struct
from .engine_patch import (ROOT, SUPPORTED_SHA256, patch, sections, function_names,
                           imported_functions, read_uint, uint, c, get, put, load,
                           store, ADD, MUL, AND, IF, END)

RING = 0xb01000
ENABLE = 0xb00080
VERSION = 'broadcast-replacement-v8'


def delivery_hook():
    # f_00472690's original locals are 1..18; ours are 19..25.
    b = c(559428)+load()+put(19)
    b += get(19)+c(ENABLE)+ADD+load(op=0x2d)+c(1)+b'\x46'+IF
    b += get(19)+c(0x9a48b0)+ADD+put(20)
    b += get(20)+load(0x211fc)+b'\x45'+IF
    b += get(19)+c(RING)+ADD+put(21)
    b += get(21)+load(4)+put(22)
    b += get(21)+c(16)+ADD+get(22)+c(127)+AND+c(32)+MUL+ADD+put(23)
    b += get(20)+load(0x21218,0x2d)+put(24)
    b += get(20)+load(0xd540)+put(25)
    def field(offset, value):
        return get(23)+value+store(offset)
    b += field(0,get(20)+load(0x58c9,0x2d))
    b += field(4,get(20)+load(0x58c6,0x2f))
    b += field(8,get(20)+load(0x21216,0x2f))
    kind = get(20)+load(0x2121c,0x2d)+b'\x04\x7f'+c(4)+b'\x05'
    kind += get(24)+c(2)+AND+b'\x04\x7f'+c(2)+b'\x05'
    kind += get(24)+c(1)+AND+b'\x04\x7f'+c(3)+b'\x05'+c(1)+END+END+END
    b += field(12,kind)
    b += field(16,get(20)+load(0x2121c,0x2d))
    b += get(25)+IF
    b += field(20,get(19)+get(25)+ADD+load(op=0x2f))+END
    b += field(24,get(24))
    # Publish count last: the JS thread never reads a partly written record.
    b += get(21)+get(22)+c(1)+ADD+store(4)
    b += get(21)+c(0x43303742)+store()
    b += END+END
    return b


def render_hook(first_local, graphic=False):
    """Suppress only scorebox windows / delivery dots; retain native animations.

    Window render methods and graphic render methods all use thiscall/ret 4.
    The native strip's own visible X position drives a pulse for the browser
    replacement. No blanket gameplay visibility or simulation state changes.
    """
    base,node,ident,scene=range(first_local,first_local+4)
    b=c(559428)+load()+put(base)
    b+=get(base)+c(ENABLE+1)+ADD+load(op=0x2d)+c(1)+b'\x46'+IF
    b+=get(base)+c(0x95bfe8)+ADD+load()+put(scene)
    b+=get(scene)+IF
    b+=get(base)+get(scene)+ADD+load(4,0x2f)+c(1)+b'\x46'+IF
    b+=get(base)+get(0)+load(4)+ADD+put(node)
    b+=get(node)+load(4,0x2f)+put(ident)
    ids=(10,330,420)
    condition=b''
    for i in ids:
        condition+=get(ident)+c(i)+b'\x46'+(b'\x72' if condition else b'')
    b+=condition+IF
    if not graphic:
        b+=get(ident)+c(10)+b'\x46'+IF
        b+=get(base)+c(0xb00088)+ADD+get(node)+get(base)+b'\x6b'+store()
        b+=get(base)+c(0xb00084)+ADD
        b+=get(base)+c(0xb00084)+ADD+load()+c(1)+ADD+store()
        b+=END
    b+=get(0)+get(0)+load()+c(-256)+AND+c(1)+b'\x72'+store()
    b+=get(0)+get(0)+load(16)+c(8)+ADD+store(16)+b'\x0f'
    b+=END+END+END+END
    return b


def patch_delivery(data):
    parts=sections(data)
    names=function_names(parts)
    target=names['f_00472690']-imported_functions(next(p for k,p in parts if k==2))
    reset_target=names['f_004ee350']-imported_functions(next(p for k,p in parts if k==2))
    render_targets={names[n]-imported_functions(next(p for k,p in parts if k==2)): graphic
                    for n,graphic in [('f_00723160',False),('f_007234e0',False)]}
    output=bytearray(data[:8])
    for kind,payload in parts:
        if kind==10:
            count,pos=read_uint(payload,0)
            bodies=[]
            for index in range(count):
                size,start=read_uint(payload,pos)
                body=payload[start:start+size]
                if index==target:
                    groups,cursor=read_uint(body,0)
                    n,cursor=read_uint(body,cursor)
                    if groups!=1 or n!=18 or body[cursor]!=0x7f:
                        raise ValueError('Unsupported native delivery routine')
                    body=uint(1)+uint(25)+b'\x7f'+delivery_hook()+body[cursor+1:]
                elif index==reset_target:
                    groups,cursor=read_uint(body,0)
                    for _ in range(groups):
                        _,cursor=read_uint(body,cursor)
                        cursor+=1
                    reset=c(559428)+load()+c(RING)+ADD+c(0)+store()
                    reset+=c(559428)+load()+c(RING+4)+ADD+c(0)+store()
                    body=body[:cursor]+reset+body[cursor:]
                elif index in render_targets:
                    groups,cursor=read_uint(body,0)
                    locals_count=0
                    for _ in range(groups):
                        n,cursor=read_uint(body,cursor)
                        locals_count+=n
                        cursor+=1
                    # Keep every original local index; append four i32 locals.
                    header=uint(groups+1)+body[len(uint(groups)):cursor]+uint(4)+b'\x7f'
                    body=header+render_hook(locals_count+1,render_targets[index])+body[cursor:]
                bodies.append(uint(len(body))+body)
                pos=start+size
            payload=uint(count)+b''.join(bodies)
        output+=bytes([kind])+uint(len(payload))+payload
    return bytes(output)


def prepare():
    original=(ROOT/'local_runtime/web/build/cricket07.wasm').read_bytes()
    if hashlib.sha256(original).hexdigest()!=SUPPORTED_SHA256:
        raise ValueError('Unsupported broadcast engine')
    target=ROOT/'local_runtime/prepared-ui/cricket07.wasm'
    stamp=target.with_suffix('.version')
    if target.exists() and stamp.exists() and stamp.read_text()==VERSION:
        return target
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_bytes(patch_delivery(patch(original)))
    stamp.write_text(VERSION)
    return target
