import struct
import unittest
from pathlib import Path
from roster.archive import BigArchive, expand
from roster.bowling_ui import (PACKAGE, SCREEN, BALL_NODES, hide_gauge_balls,
                               bowling_replacements)


class BowlingUiTests(unittest.TestCase):
    def test_unknown_layout_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Unsupported bowling-gauge'):
            hide_gauge_balls(b'unknown layout')

    def test_only_ball_sprite_dimensions_change_in_generated_archive(self):
        path = Path(__file__).resolve().parents[2] / 'local_runtime/game/Data/data.gob'
        if not path.exists():
            self.skipTest('Pinned local game assets unavailable')
        archive = BigArchive(path)
        original = archive.read(PACKAGE)
        patched = bowling_replacements(archive)[PACKAGE]
        cursor = 16
        for _ in range(struct.unpack_from('>I', original, 8)[0]):
            start, length = struct.unpack_from('>II', original, cursor)
            end = original.index(0, cursor + 8)
            name = original[cursor + 8:end].decode('ascii')
            if name == SCREEN:
                old = expand(original[start:start + length])
                pos, size = struct.unpack_from('>II', patched, cursor)
                new = patched[pos:pos + size]
                self.assertEqual(len(old), len(new))
                allowed = {node + offset + byte for node in BALL_NODES
                           for offset in (32, 36) for byte in (0, 1)}
                changed = {i for i, (a, b) in enumerate(zip(old, new)) if a != b}
                self.assertTrue(changed)
                self.assertLessEqual(changed, allowed,
                                     'Controls, IDs, positions and every other sprite stay intact')
                strings = old.index(b'GraphicButton\0') - 0x521
                for node in BALL_NODES:
                    for offset in (32, 36):
                        value = struct.unpack_from('<H', new, node + offset)[0]
                        self.assertTrue(new[strings + value:].startswith(b'0.000000\0'))
            else:
                self.assertEqual(patched[cursor:cursor + 8], original[cursor:cursor + 8])
            cursor = end + 1
        self.assertEqual(struct.unpack_from('<I', patched, 4)[0], len(patched))
