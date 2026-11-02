import json
from pathlib import Path
import struct
import tempfile
import unittest
from roster.archive import BigArchive, expand
from roster.game_patch import game_name, skills, write_skills, player_type
from roster.refresh import ROOT
from roster.teams import TEAMS


class PatchTests(unittest.TestCase):
    def test_native_role_codes(self):
        self.assertEqual(player_type('wk', 1), 7)
        self.assertEqual(player_type('wk', 5), 8)
        self.assertEqual(player_type('bat', 4, bowls=True), 1)
        self.assertEqual(player_type('bat', 1), 2)
        self.assertEqual(player_type('bowl', 10, opening=True), 10)
        self.assertEqual(player_type('bowl', 10, spin=True), 4)
        self.assertEqual(player_type('allround', 6, spin=True), 5)
        self.assertEqual(player_type('allround', 6), 9)

    def test_literal_refpack(self):
        self.assertEqual(expand(bytes.fromhex('10fb000005e041424344fd45')), b'ABCDE')

    def test_overlapping_back_reference(self):
        self.assertEqual(expand(bytes.fromhex('10fb0000070d0041fc')), b'AAAAAAA')

    def test_invalid_reference_rejected(self):
        with self.assertRaises(ValueError):
            expand(bytes.fromhex('10fb0000030000fc'))

    def test_rating_words_preserve_reserved_bits(self):
        record = bytearray(360)
        struct.pack_into('<I', record, 100, 0xc0000000)
        values = [(i + 1) % 63 for i in range(40)]
        write_skills(record, values)
        self.assertEqual(skills(record), values)
        self.assertEqual(struct.unpack_from('<I',record,100)[0] & 0xc0000000, 0xc0000000)

    def test_name_does_not_overrun_record(self):
        self.assertEqual(len(game_name('Nithish Kumar Reddy')),16)
        self.assertTrue(game_name('Nithish Kumar Reddy').endswith(b'\0'))

    def test_snapshot_excludes_unavailable_teams(self):
        snapshot = json.loads((ROOT / 'web/data/rosters.json').read_text(encoding='utf-8'))
        for data in snapshot['formats'].values():
            for team in data['teams']:
                self.assertIn(team['name'], TEAMS)

    def test_badges_complete(self):
        self.assertEqual(len(TEAMS),18)
        for _,slug in TEAMS.values():
            self.assertTrue((ROOT / 'web/assets/teams' / (slug+'.png')).exists(),slug)

    def test_archive_replacement_preserves_original(self):
        with tempfile.TemporaryDirectory() as folder:
            source=Path(folder)/'original.big'
            target=Path(folder)/'patched.big'
            name=b'test.dat\0'
            header_size=16+8+len(name)
            original=b'BIGF'+struct.pack('<I',header_size+3)+struct.pack('>II',1,header_size)+struct.pack('>II',header_size,3)+name+b'old'
            source.write_bytes(original)
            BigArchive(source).replace_into(target,{'test.dat':b'new content'})
            self.assertEqual(BigArchive(target).read('test.dat'),b'new content')
            self.assertEqual(source.read_bytes(),original)
