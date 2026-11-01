# Local Cricket07 Revamp

## Start playing

The runtime has already been installed in `local_runtime/` on this computer:

```powershell
python -m roster.server
```

Open http://localhost:8007/play/, choose **ODI**, **Test** or **T20** above the game and press **Play Solo**. The browser copies the Lite game into private storage on the first visit. Each launch in a fresh page refreshes Cricsheet, prepares the selected format's squad database and installs it before starting WebAssembly. Reload to start another format or refresh again. Select the corresponding match type inside the original game; the launch selector chooses roster data rather than changing match rules.

The preview is at http://localhost:8007/rosters.html. `GET /api/rosters` serves its JSON; `POST /api/launch` prepares a patch and returns its hash, date and player count. If Cricsheet is unavailable, the last successful snapshot is used and the launcher displays the dated fallback warning.

## Setup on another computer

Requires Python 3.10+, a WebGPU browser and roughly 1.5 GB free across disk and browser storage:

```powershell
python -m pip install -r requirements-local.txt
python tools/setup_local.py
python -m roster.server
```

`setup_local.py` downloads the public playable site's Lite assets and compiled browser runtime, verifying the site's SHA-1 content prefixes and sizes. It omits commentary, most music and movies. Original files, patched archives, conversion caches and runtime files stay in ignored `local_runtime/` and are not uploaded to GitHub. Source attribution is retained. Download source: https://cricket07.dhaiwat.com/ and its published manifest. The adapter currently recognizes the 620,140-byte database and rejects unsupported layouts.

## Existing teams only

The allowlist was checked against the actual game's team metadata: Australia, Bangladesh, Bermuda, Canada, England, India, Ireland, Kenya, Namibia, Netherlands, New Zealand, Pakistan, Scotland, South Africa, Sri Lanka, United States of America, West Indies and Zimbabwe. No additional national teams are created. Teams without a complete recent XI retain their original squad. County/state teams and World XIs remain in the game but are not separate refresh targets. Some share player IDs with national teams and inherit changes to those reused IDs.

## Updates and limits

The last 180 days of appearances define each player pool, capped at 20. Form uses the last 20 appearances within one year with a 60-day half-life. These are inferred pools rather than announced squads; retirement and injury decisions are not automatically verified. Cricsheet's missing/withheld coverage applies.

Experimental 1–99 batting and bowling ratings map to the game's 1–62 skill fields. Names fit its 15-character limit. IDs are reused, donor career statistics are cleared and old star face/speed overrides are removed. **Faces, kits, animations and commentary are not modernized.**

Role/style facts come from the linked public research in `roster/player_metadata.json` and separately sourced overrides. Unknown hands/styles retain the original slot's attributes and may need correction; the local patch report flags missing metadata. Wicketkeepers and a bowling group are prioritized for the initial XI. Captain selection uses available format metadata, otherwise the first player; it is not an official captaincy feed.

The pristine archive is never edited. Each launch rebuilds `local_runtime/prepared/Data/data.gob`, avoiding cumulative rating drift. The report records names, IDs, ratings, metadata coverage and hash. Saved careers/tournaments may use saved rosters; test with a fresh Play Now match. This local modified launcher supports solo play; online compatibility is not enabled.

## One-time logos

All 18 badges are bundled under `web/assets/teams/`. `sources.json` records ICC member profiles for most boards, Bermuda's official board and published USA/Zimbabwe marks. Trademarks remain with their owners.

The patch preserves resource names and unrelated county badges, replacing national menu textures and small flags. Converted FSH files are cached locally and invalidate only when the bundled PNGs change. No logo downloads occur during launch. `python tools/setup_reference.py` deliberately refreshes reference assets.

## Checks

```powershell
python -m unittest discover -s roster/tests -v
```

Tests cover match statistics, refresh failures, filtering, archive preservation, RefPack decoding, packed ratings and badge completeness. Browser verification reached the original game, showed updated badges on team selection and current player names on squad selection.
