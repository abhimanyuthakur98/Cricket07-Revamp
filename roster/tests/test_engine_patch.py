import unittest
from roster.engine_patch import hooks, uint, get, patch


def hook_fixture(base_pointer=559428):
    """Small module with a mock native selector between the real injected hooks."""
    def text(value):
        data=value.encode()
        return uint(len(data))+data
    def section(kind, payload):
        return bytes([kind])+uint(len(payload))+payload
    entry, final=hooks(base_pointer)
    body=uint(4)+uint(12)+b'\x7f'+uint(7)+b'\x7f'+uint(2)+b'\x7e'+uint(1)+b'\x7f'
    body+=entry+get(0)+b'\x10\0'+final+b'\x0b'
    return (b'\0asm\x01\0\0\0'+section(1,b'\x01\x60\x01\x7f\0')+
            section(2,uint(2)+text('env')+text('memory')+b'\x02\0'+uint(256)+
                    text('env')+text('native')+b'\0\0')+
            section(3,b'\x01\0')+section(7,b'\x01'+text('run')+b'\0\x01')+
            section(10,b'\x01'+uint(len(body))+body))


class EnginePatchTests(unittest.TestCase):
    def test_unknown_engine_is_rejected(self):
        with self.assertRaisesRegex(ValueError,'Unsupported browser engine'):
            patch(b'another version')

