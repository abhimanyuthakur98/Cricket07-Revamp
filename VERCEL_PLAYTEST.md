# Free Vercel playtest

Import `abhimanyuthakur98/Cricket07-Revamp`, production branch
`codex/broadcast-ui`, into the `xzm1` personal Hobby account. Use the repository
root; `vercel.json` supplies the build command and output directory. Do not
enable a Pro trial or add paid services.

The Git build downloads the verified browser runtime and game assets using the
existing setup script, applies the current custom squads and broadcast UI, and
creates a static deployment in `dist-vercel`. No serverless Function or database
is needed. No game binaries are committed to Git. Keep the original MIT notice.

Large game files are split into 8 MiB uncompressed gzip parts for static CDN
delivery. First-time visitors download the game automatically, with progress,
resumable chunks and browser storage; later visits reuse their cached files.
Full music and commentary are included. The generated `deployment-report.json`
states the actual download size. The build contains all three format databases
and the patched Wasm engine. SharedArrayBuffer requires the COOP/COEP headers
configured in `vercel.json` and a browser with WebGPU support.

This is a solo-play playtest build. Friends can each play matches in their own
browser; a head-to-head multiplayer signalling service is not included.
Roster changes take effect on a new Git deployment, using
`roster/custom_players.json` as the current authoritative source.

Local packaging check:

```powershell
python tools/build_vercel.py
python tools/check_vercel_build.py
```
