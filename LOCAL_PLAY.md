# Local Cricket07 Revamp

## Start playing

The runtime has already been installed in `local_runtime/` on this computer:

```powershell
python -m roster.server
```

Open http://localhost:8007/play/ and press **Play Solo**. There is no launcher format dropdown. Confirm your settings on the in-game Stadium Select screen: **1–20 overs → T20 international**, **50 overs → ODI**, **Unlimited Overs → Test**. The matching database is applied before squad selection, including when changing formats between Play Now matches. Each fresh launch refreshes the available match data and prepares all three databases.

The preview is at http://localhost:8007/rosters.html. `GET /api/rosters` serves its JSON; `POST /api/launch` prepares a patch and returns its hash, date and player count. If Cricsheet is unavailable, the last successful snapshot is used and the launcher displays the dated fallback warning.

## Setup on another computer

Requires Python 3.10+, a WebGPU browser and roughly 3 GB free across disk and browser storage:

```powershell
python -m pip install -r requirements-local.txt
python tools/setup_local.py
python -m roster.server
```

`setup_local.py` downloads the public playable site's runtime and game assets, including **full music and commentary**, verifying the manifest's SHA-1 content prefixes and sizes. Movies are omitted. Run setup again to upgrade an earlier Lite installation; the new manifest version makes the browser install the missing audio. These large files stay in ignored `local_runtime/` and are not uploaded to GitHub. Download source: https://cricket07.dhaiwat.com/ and its published manifest. The adapter recognizes the 620,140-byte database and supported executable; source MIT attribution remains in LICENSE while author branding is removed from the game launcher.

## Existing teams only

The allowlist was checked against the actual game's team metadata: Australia, Bangladesh, Bermuda, Canada, England, India, Ireland, Kenya, Namibia, Netherlands, New Zealand, Pakistan, Scotland, South Africa, Sri Lanka, United States of America, West Indies and Zimbabwe. No additional national teams are created. Teams without a complete recent XI retain their original squad. County/state teams and World XIs remain in the game but are not separate refresh targets. Some share player IDs with national teams and inherit changes to those reused IDs.

## Updates and limits

Each team uses the players named in its **latest available international match in that format**. No recent-player pool or form-based selection adds different players. Form still uses up to 20 appearances within one year with a 60-day half-life. Older last-known squads are retained with a stale date and unknown recent form. Cricsheet coverage can lag actual matches; the preview records the match date and ID.

Experimental 1–99 batting and bowling ratings map to the game's 1–62 skill fields. Names fit its 15-character limit. IDs are reused, donor career statistics are cleared and old star face/speed overrides are removed. Kits and animations remain original. The full original soundtrack and commentary are restored; new player names do not have newly recorded commentary clips.

Player bios are joined by stable Cricsheet IDs to public ESPN profiles; linked biographies, cached research and explicit sourced overrides provide fallbacks. The actual native role enum is written for every player, including keeper, opening batsman, pace/spin bowler and pace/spin all-rounder. A batter's occasional bowling no longer automatically changes his role to bowler. Unverified roles use labeled scorecard-workload inference. The game can arrange the XI itself; the membership remains the latest source match. Captain selection uses available format metadata, otherwise the first player.

`roster/player_profiles.json` records source URLs and missing measurements explicitly. Create Player supports facial features and skin palettes, **not numeric height or weight**. No measurements are invented or claimed to alter the model. A one-time `python tools/cache_player_appearance.py` uses available public portraits to approximate the generic skin palette, with lighting limitations recorded per player. This is not an exact face scan or player likeness. Unavailable portraits retain generic appearances. There is no inference from a player's name or nationality.

The pristine archive is never edited. Each launch rebuilds `local_runtime/prepared/Data/data.gob`, avoiding cumulative rating drift. The report records names, IDs, ratings, metadata coverage and hash. Saved careers/tournaments may use saved rosters; test with a fresh Play Now match. This local modified launcher supports solo play; online compatibility is not enabled.

## One-time logos

All 18 badges are bundled under `web/assets/teams/`. `sources.json` records ICC member profiles for most boards, Bermuda's official board and published USA/Zimbabwe marks. Trademarks remain with their owners.

The patch preserves resource names and unrelated county badges, replacing national menu textures and small flags. Edge-connected white matte is treated as transparent during encoding; enclosed white artwork and the original source pixels are preserved. The local preview applies the same alpha conversion. Converted FSH files are cached and invalidate when the PNGs or conversion version change. No logo downloads occur during launch. `python tools/setup_reference.py` deliberately refreshes reference assets.

## Checks

```powershell
python -m unittest discover -s roster/tests -v
node roster/tests/runtime_rosters.mjs
```

Tests cover match statistics, refresh failures, filtering, archive preservation, RefPack decoding, packed ratings and badge completeness. Browser verification reached the original game, showed updated badges on team selection and current player names on squad selection.
