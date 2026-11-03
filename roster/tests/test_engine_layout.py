import hashlib
import json
from contextlib import ExitStack
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from roster import engine_patch, ui_engine
from roster.engine_layout import guest_base_pointer


class EngineLayoutTests(unittest.TestCase):
    def test_unknown_download_reports_its_fingerprint(self):
        data = b'an unverified upstream engine'
        with self.assertRaisesRegex(ValueError, hashlib.sha256(data).hexdigest()):
            guest_base_pointer(data)

    def test_prepared_cache_tracks_source_and_detects_corruption(self):
        for module in (engine_patch, ui_engine):
            with self.subTest(module=module.__name__), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                source = root / 'local_runtime/web/build/cricket07.wasm'
                source.parent.mkdir(parents=True)
                source.write_bytes(b'verified older runtime')
                with ExitStack() as stack:
                    stack.enter_context(patch.object(module, 'ROOT', root))
                    stack.enter_context(patch.object(module, 'guest_base_pointer', return_value=559428))
                    build = stack.enter_context(patch.object(module, 'patch', side_effect=lambda data: b'patched:' + data))
                    if module is ui_engine:
                        stack.enter_context(patch.object(module, 'patch_delivery', side_effect=lambda data, pointer: data))
                    output = module.prepare()
                    self.assertEqual(module.prepare(), output)
                    self.assertEqual(build.call_count, 1, 'A valid prepared engine is reused')
                    source.write_bytes(b'verified newer runtime')
                    module.prepare()
                    self.assertEqual(build.call_count, 2, 'Changing runtime invalidates the prepared cache')
                    self.assertIn(b'newer runtime', output.read_bytes())
                    output.write_bytes(b'partial or corrupted engine')
                    module.prepare()
                    self.assertEqual(build.call_count, 3, 'Corrupt output is rebuilt even with a valid stamp')

    def test_existing_cache_cannot_bypass_download_verification(self):
        for module in (engine_patch, ui_engine):
            with self.subTest(module=module.__name__), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                source = root / 'local_runtime/web/build/cricket07.wasm'
                source.parent.mkdir(parents=True)
                source.write_bytes(b'unverified new runtime')
                prepared = root / 'local_runtime' / ('prepared-ui' if module is ui_engine else 'prepared') / 'cricket07.wasm'
                prepared.parent.mkdir(parents=True)
                prepared.write_bytes(b'existing cached engine')
                prepared.with_suffix('.version').write_text(json.dumps({
                    'version': module.VERSION,
                    'sourceSha256': hashlib.sha256(source.read_bytes()).hexdigest(),
                    'sha256': hashlib.sha256(prepared.read_bytes()).hexdigest(),
                }))
                with patch.object(module, 'ROOT', root), patch.object(module, 'patch') as build:
                    with self.assertRaisesRegex(ValueError, 'Unsupported browser engine'):
                        module.prepare()
                    build.assert_not_called()
