# Broadcast score ticker

The broadcast UI uses browser text for the score ticker and informational cards.

Run the isolated preview:

```powershell
python -m roster.server --no-refresh --broadcast-ui --port 8009
```

Open http://localhost:8009/play/. The regular server on port 8008 retains its
original UI. The UI server uses a separate browser origin and `prepared-ui`
archive directory, so its generated engine and data do not replace the regular
build. Start a fresh Play Solo session after changing the UI code.

The ticker uses Inter, already bundled in the browser launcher, translucent navy
surfaces, subtle blur and magenta accents. Text stays fully opaque for readability.
The game canvas fills the stage, including fullscreen; no footer space or black
bands are added for the broadcast. The translucent strip spans 96% of the
stage, with 2% side margins, using the space beneath the native bowling gauge.
With feedback visible its height is 13% of the stage; its top stays below the
gauge's last graphic. Type scales with both viewport dimensions so short, wide
fullscreen layouts also fit. The feedback row collapses when it has no result
or speed to show; the main score and player text retain their size.
The format label follows the actual quota: T5, T10, T15, T20, ODI for 50 overs,
and TEST for unlimited overs. Short matches still use the T20 squad database.
Play Now team selection shows Test, ODI and T20 starting-XI strengths beside
each team's badge in place of the original overall number. T20, ODI and Test
are stacked vertically, with each label above its value; the selected format is gold.
Hovering a format shows batting/bowling strength and its
source date. There is no extra selection footer or ratings box. The ratings
disappear outside this selection screen. See [RATINGS.md](RATINGS.md) for the
calculation and source limits.
Automatic batter/bowler stat cards and over-announcement cards are suppressed;
the broadcast already contains those running figures. Batters and their runs/balls appear on the
left; score, overs, innings and run rate in the centre; current bowler figures,
overs and the current over's deliveries on the right. Country SVGs flank it.
Delivery speed appears in the lower row at the far right, beneath the bowler's
figures and over history, with a `Delivery Speed` label and a bold value. It uses
the game's measured release speed for both player and computer bowling. Native
delivery event 65 publishes the bowler's MPH/KPH values into reserved telemetry
memory, before the score changes. The readout respects the native unit preference,
retains the released ball's value and clears on the next-ball reset or a change
of bowler/innings. It does not depend on the old score strip's rotating text or
visibility. The six ball
icons beneath the bowling gauge are removed from the generated UI archive;
the gauge, release controls, delivery selection and radar remain intact.
The native scorebox window renderer skips the old strip in the UI build;
its original position/animation state emits the visibility pulse for the new
ticker. It therefore does not stay on screen throughout intros, menus or
replays. The legacy ball-history window is skipped while the bowling meter,
delivery selection controls and radar remain. Every illegal delivery adds an extra chip;
six legal deliveries are still required. Long overs wrap onto extra rows within
the bowling panel, with smaller chips to keep the strip clear of the gauge.
England and Scotland flags are simple local SVGs; West Indies has a maroon WI
regional marker, since it is not a single country. Other national flags are
cached from https://flagcdn.com/ and are served locally.

`broadcast-state.js` decodes the supported native match layout. `ui_engine.py`
adds a gated delivery ring in reserved guest memory at score commit; it never
writes native match fields or registers. The regular engine does not include
the delivery hook. `roster/engine_layout.py` pins each verified runtime and its
guest-base pointer; `engine-layout.mjs` resolves the matching loaded executable
for both the broadcast and selection ratings. Unsupported runtime versions are
rejected, and prepared engines are invalidated when their source changes.

During a limited-overs chase the ticker shows the target, runs needed, legal balls
remaining and required run rate: `runs needed × 6 / balls remaining`
([formula reference](https://cricketcals.com/required-run-rate)). Wides and no-balls
do not consume a ball. A finished chase or exhausted innings never divides by zero.
In the fourth innings of a Test the target includes both teams' earlier innings;
there is no invented limited-overs quota or required rate.

The dismissal card follows the original game's dismissal scene (native window
103), with no browser display timer. Its native active/hidden state controls
when the card appears and clears; skipping the scene clears it immediately,
and a next-ball reset prevents stale information carrying into play. The native
delivery hook records the departing player's record before the striker/non-striker
pointers change, including non-striker run-outs. When the native dismissal scene
opens, the card freezes that player's final name, runs, balls and strike rate.
The card sits near the bottom where the original dismissal information appears.
The score footer and timing hide during this scene.

Zero-run dismissals retain the original animated duck in native window 310 and
its `duck01`–`duck16` frame callback, rather than replacing it with an emoji or
another timed card. The broadcast also hides while that native duck is visible.
The engine preserves window callbacks/transforms and suppresses only child
drawing for replaced information windows, leaving the duck's renderer intact.

Shot timing appears **inside the broadcast strip's dedicated lower row**, as
`Shot Timing : Ideal`, with a prominent coloured result badge. The row pairs
shot timing on the left with delivery speed on the right, using the broadcast's
existing navy and magenta style. The scale, separate floating timing card and
timing totals are removed. Feedback starts only at actual contact, or when a
delivery completes as a miss or a leave. A live timing zone or an AI shot plan
at ball release cannot display a result. Feedback lasts five seconds, or until
the active batter resets for the next ball, whichever comes first. Brief native
score-strip slide-outs and post-shot controller handoffs cannot consume it.
Menus, pauses, replays and dismissal notices still hide it immediately. The same
feedback is shown for player and AI batting, with no human-controller condition.

The native `BatTiming` zones supply **Too Early**, **Early**, **Good**, **Ideal**,
**Late** and **Too Late**. Ideal is green, Good is yellow, and the other outcomes
are red. Real collision snapshots preserve the zone before the native routine
clamps it. Trajectory-prediction calls are excluded. Missed attempts also use
the completed delivery's native zone; an attempted shot with no actual contact
shows **Miss**, or **Late Miss** for the late zones. A completed delivery with no
attempted shot shows **Leave** in neutral grey. A next-ball pulse prevents delayed results from the
previous ball reappearing. No separate shot-selection grade is displayed:
the current adapter has no verified native quality grade for that calculation.
Native selection controls, bowling meter and radar remain available.

For the normal local address, start with `python -m roster.server --broadcast-ui`
and open http://localhost:8007/play/. Reload and launch a fresh Play Solo session
after changing engine hooks.

Validation:

```powershell
python -m unittest discover -s roster/tests
node roster/tests/broadcast.mjs
node roster/tests/runtime_rosters.mjs
node roster/tests/squad_ratings.mjs
node roster/tests/engine_hook.mjs
```
