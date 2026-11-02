# Broadcast score ticker

Experimental branch: `codex/broadcast-ui`. Original native fonts are preserved.

Run the isolated preview:

```powershell
python -m roster.server --no-refresh --broadcast-ui --port 8009
```

Open http://localhost:8009/play/. The regular server on port 8008 retains its
original UI. The UI server uses a separate browser origin and `prepared-ui`
archive directory, so its generated engine and data do not replace the regular
build. Start a fresh Play Solo session after changing the UI code.

The ticker uses Inter, already bundled in the browser launcher, navy panels,
white score area and magenta accents. Batters and their runs/balls appear on the
left; score, overs, innings and run rate in the centre; current bowler figures,
overs and the current over's deliveries on the right. Country SVGs flank it.
The native scorebox window renderer skips the old strip in the UI build;
its original position/animation state emits the visibility pulse for the new
ticker. It therefore does not stay on screen throughout intros, menus or
replays. The six legacy delivery dots are skipped in the graphic renderer while
the bowling meter itself remains. Every illegal delivery adds an extra chip;
six legal deliveries are still required, and long overs wrap onto extra rows.
England and Scotland flags are simple local SVGs; West Indies has a maroon WI
regional marker, since it is not a single country. Other national flags are
cached from https://flagcdn.com/ and are served locally.

`broadcast-state.js` decodes the supported native match layout. `ui_engine.py`
adds a gated delivery ring in reserved guest memory at score commit; it never
writes native match fields or registers. The regular engine does not include
the delivery hook. Unsupported runtime versions are rejected.

Validation:

```powershell
python -m unittest discover -s roster/tests
node roster/tests/broadcast.mjs
node roster/tests/runtime_rosters.mjs
node roster/tests/engine_hook.mjs
```
