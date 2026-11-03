"""Read-only match, shot and panel telemetry for the broadcast UI engine.

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
PANELS = (101, 102, 103, 201, 202, 300, 360, 370, 400, 500, 310)
PANEL_STATE = 0xb00100
SHOT = 0xb000c0
WICKET = 0xb00200
BALL_START = 0xb00240
SPEED = 0xb00280
VERSION = 'broadcast-live-feedback-v17'


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
    # BatTiming getter f_00441f50: app -> batting team -> striker -> zone.
    # Seven means no attempted shot. Publish a native zone, never infer from runs.
    b += field(28,c(7))
    b += get(19)+c(0x817580)+ADD+load()+put(25)
    b += get(25)+IF
    b += get(19)+get(25)+ADD+load(0x2740)+put(25)
    b += get(25)+IF
    b += get(19)+get(25)+ADD+load(0xb8)+put(25)
    b += get(25)+IF
    b += field(28,get(19)+get(25)+ADD+load(0x2d8))
    b += END+END+END
    # Remember the departing player before the incoming batter replaces the
    # striker pointers. f_00441770 uses 0x2121b == 1 for the striker, else non-striker.
    b += get(20)+load(0x2121c,0x2d)+IF
    def wicket_field(offset, value):
        return get(19)+c(WICKET)+ADD+value+store(offset)
    departing = get(20)+load(0x2121b,0x2d)+c(1)+b'\x46\x04\x7f'
    departing += get(20)+load(0xd538)+b'\x05'+get(20)+load(0xd53c)+END
    b += wicket_field(12,departing)
    b += wicket_field(8,get(20)+load(0x58c9,0x2d))
    b += wicket_field(16,get(20)+load(0xd564))
    b += wicket_field(4,get(22)+c(1)+ADD)
    b += wicket_field(0,c(0x43303757))+END
    # Publish count last: the JS thread never reads a partly written record.
    b += get(21)+get(22)+c(1)+ADD+store(4)
    b += get(21)+c(0x43303742)+store()
    b += END+END
    return b


def shot_hook(first_local):
    """Snapshot the actual contact zone before f_005566f0 clamps it to 1..5."""
    base, batter = first_local, first_local+1
    b = c(559428)+load()+put(base)
    b += get(base)+c(ENABLE)+ADD+load(op=0x2d)+c(1)+b'\x46'+IF
    # The real collision passes false at [esp+8]. Trajectory prediction calls
    # pass true and must not manufacture a player shot/contact notification.
    b += get(base)+get(0)+load(16)+ADD+load(8,0x2d)+b'\x45'+IF
    b += get(base)+get(0)+load(4)+ADD+put(batter)
    def field(offset, value):
        return get(base)+c(SHOT)+ADD+value+store(offset)
    b += field(8,get(batter)+load(0x2d8))
    b += field(12,get(base)+c(RING+4)+ADD+load())
    b += field(16,get(base)+c(0x9a48b0+0x58c9)+ADD+load(op=0x2d))
    b += field(20,get(base)+c(BALL_START+4)+ADD+load())
    b += field(4,get(base)+c(SHOT+4)+ADD+load()+c(1)+ADD)
    b += field(0,c(0x43303754))+END+END
    return b


def ball_start_hook(first_local):
    """Publish the active batter's per-ball reset, without changing the game."""
    base, actor = first_local, first_local+1
    b = c(559428)+load()+put(base)
    b += get(base)+c(ENABLE)+ADD+load(op=0x2d)+c(1)+b'\x46'+IF
    b += get(base)+c(0x817580)+ADD+load()+put(actor)
    b += get(actor)+IF
    b += get(base)+get(actor)+ADD+load(0x2740)+put(actor)
    b += get(actor)+IF
    b += get(base)+get(actor)+ADD+load(0xb8)+put(actor)
    b += get(actor)+get(0)+load(4)+b'\x46'+IF
    def field(offset, value):
        return get(base)+c(BALL_START)+ADD+value+store(offset)
    b += field(8,get(base)+c(RING+4)+ADD+load())
    b += field(12,get(base)+c(0x9a48b0+0x58c9)+ADD+load(op=0x2d))
    b += field(4,get(base)+c(BALL_START+4)+ADD+load()+c(1)+ADD)
    b += field(0,c(0x4330374e))
    b += END+END+END+END
    return b


def speed_hook(first_local):
    """Capture native delivery event 65 after the bowler writes MPH and KPH.

    f_0056cee0 writes actor+0x340 (MPH), +0x344 (KPH), then calls
    f_0059eb10 with {event:65, actor}. Prediction and UI text are not involved.
    """
    base, packet, actor, record = range(first_local, first_local+4)
    b = c(559428)+load()+put(base)
    b += get(base)+c(ENABLE)+ADD+load(op=0x2d)+c(1)+b'\x46'+IF
    b += get(base)+c(0x9a48b0+0x211fc)+ADD+load()+b'\x45'+IF
    b += get(base)+get(0)+load(16)+ADD+load(4)+put(packet)
    b += get(packet)+IF
    b += get(base)+get(packet)+ADD+put(packet)
    b += get(packet)+load()+c(65)+b'\x46'+IF
    b += get(packet)+load(4)+put(actor)
    b += get(actor)+IF
    b += get(base)+get(actor)+ADD+put(actor)
    def field(offset, value):
        return get(base)+c(SPEED)+ADD+value+store(offset)
    b += field(8,get(actor)+load(0x340))
    b += field(12,get(actor)+load(0x344))
    b += field(16,get(base)+c(BALL_START+4)+ADD+load())
    b += field(20,get(base)+c(0x9a48b0+0x58c9)+ADD+load(op=0x2d))
    b += field(24,c(-1))
    b += get(base)+c(0x9a48b0+0xd540)+ADD+load()+put(record)
    b += get(record)+IF
    b += field(24,get(base)+get(record)+ADD+load(op=0x2f))+END
    b += field(28,get(base)+c(RING+4)+ADD+load())
    b += field(32,get(base)+c(0x9dc4f0+0x2c)+ADD+load(op=0x2d)+c(32)+AND)
    b += field(4,get(base)+c(SPEED+4)+ADD+load()+c(1)+ADD)
    b += field(0,c(0x43303756))
    return b+END+END+END+END+END


def render_hook(first_local, children=False):
    """Replace score/information windows; retain native controls and animations.

    Both window methods use thiscall/ret 4. Keep f_00723160's callbacks and
    transforms running; suppress only its child drawing in f_007234e0. Those
    callbacks advance the native presentation lifecycle and animations.
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
    if not children:
        # Preserve native panel timing and native formatted text in browser cards.
        for slot, ident_value in enumerate(PANELS):
            b+=get(ident)+c(ident_value)+b'\x46'+IF
            address=PANEL_STATE+slot*8
            b+=get(base)+c(address+4)+ADD+get(node)+get(base)+b'\x6b'+store()
            b+=get(base)+c(address)+ADD
            b+=get(base)+c(address)+ADD+load()+c(1)+ADD+store()+END
        b+=get(ident)+c(10)+b'\x46'+IF
        b+=get(base)+c(0xb00088)+ADD+get(node)+get(base)+b'\x6b'+store()
        b+=get(base)+c(0xb00084)+ADD
        b+=get(base)+c(0xb00084)+ADD+load()+c(1)+ADD+store()
        b+=END
        return b+END+END+END
    # Window 310 is the original animated duck, not an HTML replacement.
    # Its child graphic callback f_004b6200 must continue to animate duck01..16.
    ids=(10,330,335,420)+tuple(i for i in PANELS if i!=310)
    condition=b''
    for i in ids:
        condition+=get(ident)+c(i)+b'\x46'+(b'\x72' if condition else b'')
    b+=condition+IF
    b+=get(0)+get(0)+load()+c(-256)+AND+c(1)+b'\x72'+store()
    b+=get(0)+get(0)+load(16)+c(8)+ADD+store(16)+b'\x0f'
    b+=END+END+END+END
    return b


def patch_delivery(data):
    parts=sections(data)
    names=function_names(parts)
    target=names['f_00472690']-imported_functions(next(p for k,p in parts if k==2))
    reset_target=names['f_004ee350']-imported_functions(next(p for k,p in parts if k==2))
    shot_target=names['f_005566f0']-imported_functions(next(p for k,p in parts if k==2))
    ball_target=names['f_00555510']-imported_functions(next(p for k,p in parts if k==2))
    speed_target=names['f_0059eb10']-imported_functions(next(p for k,p in parts if k==2))
    render_targets={names[n]-imported_functions(next(p for k,p in parts if k==2)): children
                    for n,children in [('f_00723160',False),('f_007234e0',True)]}
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
                    reset+=c(559428)+load()+c(SHOT)+ADD+c(0)+store()
                    reset+=c(559428)+load()+c(SHOT+4)+ADD+c(0)+store()
                    reset+=c(559428)+load()+c(WICKET)+ADD+c(0)+store()
                    reset+=c(559428)+load()+c(WICKET+4)+ADD+c(0)+store()
                    reset+=c(559428)+load()+c(BALL_START)+ADD+c(0)+store()
                    reset+=c(559428)+load()+c(BALL_START+4)+ADD+c(0)+store()
                    reset+=c(559428)+load()+c(SPEED)+ADD+c(0)+store()
                    reset+=c(559428)+load()+c(SPEED+4)+ADD+c(0)+store()
                    body=body[:cursor]+reset+body[cursor:]
                elif index in (shot_target, ball_target, speed_target):
                    groups,cursor=read_uint(body,0)
                    locals_count=0
                    for _ in range(groups):
                        n,cursor=read_uint(body,cursor)
                        locals_count+=n
                        cursor+=1
                    extra=4 if index==speed_target else 2
                    header=uint(groups+1)+body[len(uint(groups)):cursor]+uint(extra)+b'\x7f'
                    hook={shot_target:shot_hook,ball_target:ball_start_hook,speed_target:speed_hook}[index]
                    body=header+hook(locals_count+1)+body[cursor:]
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
