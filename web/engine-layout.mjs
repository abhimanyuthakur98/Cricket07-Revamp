// Relocated Wasm symbols for the two hash-verified builds in engine_layout.py.
// Check the guest executable before any overlay can read or write guest memory.
export const GUEST_BASE_POINTERS = [559428, 559636];

export function readGuestBase(buffer) {
  const view = new DataView(buffer);
  for (const pointer of GUEST_BASE_POINTERS) {
    if (pointer + 4 > buffer.byteLength) continue;
    const base = view.getUint32(pointer, true);
    if (!base || base + 0xb02010 > buffer.byteLength) continue;
    if (view.getUint16(base + 0x400000, true) === 0x5a4d &&
        view.getUint32(base + 0x40003c, true) === 0x128 &&
        view.getUint16(base + 0x487930, true) === 0xe8b8) return base;
  }
  return null;
}
