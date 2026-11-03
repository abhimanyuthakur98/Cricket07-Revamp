import struct
import unittest
from roster.selection_ui import hide_legacy_ratings, patch_package


class SelectionUiTests(unittest.TestCase):
    def test_rating_objects_stay_addressable_but_controls_keep_their_colors(self):
        rating = b'<Slider ID="27" CaretColor="f1e2b4ff" CurVal="64"></Slider>'
        digit = b'<GraphicButton ID="19" BGColor="f1e2b4ff" Texture="rate01"></GraphicButton>'
        label = b'<TextButton ID="26" Text="$5" FontColor="dcdcdcff"></TextButton>'
        control = b'<GraphicButton ID="2" BGColor="ffffffff" Texture="l1saf"></GraphicButton>'
        arrow = b'<ToggleButton ID="10" FontColor="dcdcdcff" Text="Australia"></ToggleButton>'
        xml = b'<Screen ID="11">' + rating + digit + label + control + arrow + b'</Screen>'
        patched = hide_legacy_ratings(xml)
        self.assertIn(control, patched)
        self.assertIn(arrow, patched)
        self.assertIn(b'ID="27" CaretColor="00000000" CurVal="64"', patched)
        self.assertIn(b'ID="19" BGColor="00000000" Texture="rate01"', patched)
        self.assertIn(b'Text="$5" FontColor="00000000"', patched)

    def test_package_updates_only_named_screen_and_its_index(self):
        payload = b'<Slider ID="27" CaretColor="ffffffff"></Slider>'
        entries = [b'team.rfe', b'stadium.rfe']
        size = 16 + sum(9 + len(name) for name in entries)
        index = b''.join(struct.pack('>II', size + i * len(payload), len(payload)) + name + b'\0'
                         for i, name in enumerate(entries))
        original = b'BIGF' + struct.pack('<I', size + 2 * len(payload)) + struct.pack('>II', 2, size) + index + payload * 2
        patched = patch_package(original, {'team.rfe'})
        first, length = struct.unpack_from('>II', patched, 16)
        self.assertEqual(patched[first:first + length], hide_legacy_ratings(payload))
        second_index = 16 + 9 + len(entries[0])
        self.assertEqual(patched[second_index:second_index + 8], original[second_index:second_index + 8])
        self.assertEqual(patched[size:size + len(payload) * 2], payload * 2)
        self.assertEqual(struct.unpack_from('<I', patched, 4)[0], len(patched))
