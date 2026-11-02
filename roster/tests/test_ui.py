import unittest
import struct
from roster.ui_engine import delivery_hook, render_hook
from roster.engine_patch import uint


def delivery_fixture():
    def text(s):
        b=s.encode();return uint(len(b))+b
    def section(k,p):return bytes([k])+uint(len(p))+p
    body=uint(1)+uint(25)+b'\x7f'+delivery_hook()+b'\x0b'
    return (b'\0asm\x01\0\0\0'+section(1,b'\x01\x60\x01\x7f\0')+
            section(2,b'\x01'+text('env')+text('memory')+b'\x02\0'+uint(256))+
            section(3,b'\x01\0')+section(7,b'\x01'+text('run')+b'\0\0')+
            section(10,b'\x01'+uint(len(body))+body))


def render_fixture(graphic=False):
    def text(s):
        b=s.encode();return uint(len(b))+b
    def section(k,p):return bytes([k])+uint(len(p))+p
    # A normal draw reaches this marker. Suppressed nodes return before it.
    from roster.engine_patch import c, store
    body=uint(1)+uint(4)+b'\x7f'+render_hook(1,graphic)+c(0xb000a0)+c(1)+store()+b'\x0b'
    return (b'\0asm\x01\0\0\0'+section(1,b'\x01\x60\x01\x7f\0')+
            section(2,b'\x01'+text('env')+text('memory')+b'\x02\0'+uint(256))+
            section(3,b'\x01\0')+section(7,b'\x01'+text('run')+b'\0\0')+
            section(10,b'\x01'+uint(len(body))+body))


class UiTests(unittest.TestCase):
    def test_fixture_is_wasm(self):
        self.assertEqual(delivery_fixture()[:8], b'\0asm\x01\0\0\0')
