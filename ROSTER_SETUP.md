# Cricket07 Revamp — first increment

This repository retains the upstream browser port and adds a real-data roster pipeline and browser preview. **The pipeline does not update the game's internal database yet.** A Cricket 07 installation, translated executable and compiled WebAssembly build are needed to implement and verify that step. No game assets or compiled game binary are included.

## Try the roster preview on Windows

Requires Python 3.10+; no packages or API keys.

```powershell
python -m roster.server
```

Open http://localhost:8007/rosters.html. At launch the server refreshes once per UTC day. The initial download includes the full men's Test, ODI and T20 international archives, so allow time for it to complete. It only retains players' recent results in the generated snapshot. If the source is unavailable, the last successful dated snapshot remains usable.

```powershell
python -m roster.refresh          # explicitly refresh the source data
python -m roster.server --no-refresh
python -m unittest discover -s roster/tests -v
```

`GET /api/rosters` provides the same document as `web/data/rosters.json`. Fetch it before a future game starts; do not change player ratings during a match. The preview also works on a static host with no API server. “Reload snapshot” reloads the published document; it does not trigger remote downloads.

## Data and ratings

Source: [Cricsheet](https://cricsheet.org/downloads/), [JSON format](https://cricsheet.org/format/json/), [licensing](https://cricsheet.org/licensing/). Match data is under the Open Data Commons Attribution License. The snapshot and preview include attribution. Rankings are our experimental calculations, not ICC ratings.

Each format uses up to 20 most recently appearing players per national team within 180 days. This is a recent-player pool, **not an official squad list**. Retirements, injuries, availability and the next selected XI cannot be verified from match appearances alone. Afghanistan coverage is withheld by the source. Teams with no qualifying data are omitted rather than filled with invented players. A team's latest match date and a warning after 30 days are shown.

Form uses up to 20 appearances in the last year with a 60-day half-life. Batting combines runs per dismissal and strike rate; bowling combines wickets per 100 balls and economy. Format-specific baselines and regression toward 50 limit small-sample extremes. Ratings range from 1–99, and unobserved batting/bowling remains null. Fielding ability, handedness, bowling style and captaincy are deliberately not fabricated. All three formats must refresh successfully before replacing the snapshot.

## Game integration still required

Follow the upstream README to compile and import your game. The original build instructions target Apple Silicon/macOS and require Ghidra and Emscripten; this data preview works independently on Windows.

Once a working game build and its data are available, inspect the database version, map stable Cricsheet IDs to game player slots, supply verified roles/handedness/styles and official squad overrides, and map the experimental ratings to confirmed in-game skill fields. Verify changed names, team selection and ratings in an actual match before enabling automatic patches. Keep original data for restoration. Online players must receive identical roster data and include its hash in the existing compatibility check.

## Daily snapshots

The `Refresh cricket rosters` GitHub workflow runs daily and on manual dispatch. It commits only the generated JSON when changed. Actions needs repository write permission; failed refreshes leave the last snapshot untouched. The workflow does not compile or host the game. Enable static hosting separately if you want a public preview; this repository may remain private.
