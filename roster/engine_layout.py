"""Verified browser builds and their relocated guest-base pointer.

The November runtime adds host memory helpers and moves this Wasm data symbol.
Guest executable addresses and the native hook routines retain their layouts.
Never patch an engine merely because its function names look familiar.
"""
import hashlib

LEGACY_BASE_POINTER = 559428
SUPPORTED_ENGINES = {
    '8f04a1da726f2fea836aafb3a9eb5b73853b467d765798218932a59156574fdf': LEGACY_BASE_POINTER,
    'bdf208a1435fe4bdacbb3c469813cb311a2fc7d5adb5a3c11f675c75125d8352': 559636,
}


def guest_base_pointer(data):
    digest = hashlib.sha256(data).hexdigest()
    try:
        return SUPPORTED_ENGINES[digest]
    except KeyError:
        raise ValueError(
            f'Unsupported browser engine (SHA-256 {digest}). '
            'The downloaded runtime needs a verified compatibility update.'
        ) from None
