# Squad strength and player form

Play Now team selection shows separate **Test**, **ODI** and **T20** squad strengths
beside each team's badge, where the original overall number appeared. There is
no separate ratings box below the game. Values use a 1–99 scale in a vertical
stack headed **T20**, **ODI**, **Test**, with each value underneath its
label and the selected format highlighted in gold. T20 covers matches of 20 overs
or fewer. Hover a format for batting/bowling strength and its source XI date.
These use each format's latest installed starting XI, rather than country
reputation or the strength of reserves. They describe the supplied format XIs;
manual changes in the native XI editor are not included in this comparison.
Unavailable ratings appear as **—**, and **\*** marks a limited recent sample.
Teams without a complete refreshed XI do not
receive a rating for the original retained squad.
The original native overall number and batting/bowling/fielding bars are hidden
on this screen so they cannot conflict with the squad-based values.

## What the official systems measure

ICC team ratings use points divided by the match/series total, rounded; they
measure team results separately in each format. They are not obtained by
averaging a squad's player ratings. ICC player points use a moving average on a
0–1000 scale, with different factors by format
([ICC methodology](https://www.icc-cricket.com/about/cricket/icc-rankings/index)).
Player ratings consider career performances with greater emphasis on recent
matches, opposition strength and scorecard context. ICC's all-rounder index is
batting points × bowling points / 1000. ICC does not publish a comparable
statistical fielding/keeper rating
([ICC player-rating FAQ](https://www.icc-cricket.com/rankings/faqs)).

Our **Squad Strength** is a game model built from the available squad and its
recent player form. It does not reproduce ICC points or claim to include ICC's
opposition and pitch adjustments.

## Player inputs already used by the game

The refresh calculates batting and bowling form separately for each format,
using up to 20 appearances in the past 365 days. Each match's statistics receive
weight `0.5 ** (age in days / 60)`. Let `R`, `B`, `D`, `L`, `C`, `W` be weighted
runs, balls faced, dismissals, legal balls bowled, runs conceded and wickets.

| Input | Test | ODI | T20 |
| --- | ---: | ---: | ---: |
| Baseline strike rate | 50 | 85 | 130 |
| Baseline economy | 3.2 | 5.5 | 8.0 |

```text
SR = 100 × R / B
AVG = R / max(1, D)
raw batting = 50 + 0.25 × (SR − baseline SR) + 0.6 × (min(AVG, 100) − 25)
batting = clamp(round(50 + (raw batting − 50) × B / (B + 120)), 1, 99)

ECON = 6 × C / L
WP100 = 100 × W / L
raw bowling = 50 + 5 × (baseline economy − ECON) + 5 × (WP100 − 3)
bowling = clamp(round(50 + (raw bowling − 50) × L / (L + 120)), 1, 99)
```

No balls faced/bowled means the respective rating is unknown. Smoothing toward
50 limits extreme ratings from small samples. The existing confidence flag is
established when `max(B, L) ≥ 120`, otherwise limited. These player ratings
already affect the game's skills; this change adds their squad-level display.
Data availability can lag real matches, so source XI dates matter.

## Aggregating a format XI

1. **Batting** is the weighted mean in batting order, using weights
   `[1, 1, 1, 1, 1, .9, .8, .5, .35, .25, .2]`. This emphasizes the top order
   while retaining batting depth. At least six known batting ratings and 70%
   of the order's total weight are required. Unknown values are omitted and
   incomplete coverage is marked with an asterisk.
2. **Bowling** is the equal-weight mean of the four principal bowlers in Tests,
   or five in ODI/T20. Candidates have a bowling/all-rounder role or at least
   60 recent legal balls; candidates are selected by recent legal-ball workload.
   All attack slots must have known bowling ratings. This avoids selecting
   occasional bowlers just for an unusually high rating.
3. **Overall** is the harmonic mean: `2 × batting × bowling / (batting + bowling)`.
   A weak attack or batting lineup therefore reduces the overall rating.
   Display rounding happens only after aggregation. Reserves do not contribute.

No invented fielding or keeping component is added. The model lives in
`web/squad-rating-model.mjs`; `roster/squad_ratings.py` exports player inputs and
installed slot mappings from the actual preparation reports.

## Overs labels

Matches of 1–20 overs use the T20 squad but display the actual length: **T5**,
**T10**, **T15**, **T20**, and so on. Fifty overs display **ODI**, and unlimited
overs display **TEST**. Other positive quotas display their actual overs rather
than being mislabeled ODI. Both the live broadcast and launcher status use the
same formatter.

Validation: `python -m unittest discover -s roster/tests`,
`node roster/tests/squad_ratings.mjs`, `node roster/tests/runtime_rosters.mjs`.
