"""Build attributed, format-specific recent-player pools from Cricsheet JSON.

No API key or third-party packages. Run: python -m roster.refresh
"""
import argparse
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
import io
import json
from pathlib import Path
import tempfile
import urllib.request
import zipfile
from .teams import TEAMS

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "web" / "data" / "rosters.json"
SOURCES = {"Test": "tests", "ODI": "odis", "T20": "t20s"}
NO_BOWLER_CREDIT = {"retired hurt", "run out", "obstructing the field", "retired out"}


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                     delete=False, suffix=".tmp") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        temp = Path(handle.name)
    temp.replace(path)


def download_matches(format_name):
    url = f"https://cricsheet.org/downloads/{SOURCES[format_name]}_male_json.zip"
    request = urllib.request.Request(url, headers={"User-Agent": "Cricket07-Revamp/1.0"})
    with urllib.request.urlopen(request, timeout=120) as response:
        payload = response.read(200 * 1024 * 1024 + 1)
    if len(payload) > 200 * 1024 * 1024:
        raise ValueError("Source archive exceeded 200 MB")
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        for entry in archive.infolist():
            if not entry.filename.endswith(".json"):
                continue
            if entry.file_size > 20 * 1024 * 1024:
                raise ValueError("Source match exceeded 20 MB")
            yield entry.filename, json.loads(archive.read(entry))


def match_date(match):
    # Completed dates avoid using an unfinished Test's future days.
    return max(date.fromisoformat(str(d)) for d in match["info"]["dates"])


def new_stats():
    return dict(runs=0, ballsFaced=0, dismissals=0, legalBalls=0,
                conceded=0, wickets=0, catches=0, stumpings=0,
                battingInnings=0, battingPositionTotal=0, openingSpells=0)


def summarize(match):
    """Count batting/bowling correctly around extras, run-outs and super overs."""
    result = defaultdict(new_stats)
    for innings in match.get("innings", []):
        if innings.get("super_over"):
            continue
        order, opening_bowlers = [], set()
        for over in innings.get("overs", []):
            for ball in over["deliveries"]:
                for name in (ball['batter'], ball.get('non_striker')):
                    if name and name not in order:
                        order.append(name)
                        result[name]['battingInnings'] += 1
                        result[name]['battingPositionTotal'] += len(order)
                if over.get('over', 99) < 2 and ball['bowler'] not in opening_bowlers:
                    opening_bowlers.add(ball['bowler'])
                    result[ball['bowler']]['openingSpells'] += 1
                bat, bowl = result[ball["batter"]], result[ball["bowler"]]
                extras = ball.get("extras", {})
                bat["runs"] += ball["runs"]["batter"]
                # A no-ball faced counts in batting strike rate; a wide does not.
                bat["ballsFaced"] += int(not extras.get("wides", 0))
                bowl["legalBalls"] += int(not (extras.get("wides", 0) or extras.get("noballs", 0)))
                bowl["conceded"] += ball["runs"]["total"] - extras.get("byes", 0) - extras.get("legbyes", 0) - extras.get("penalty", 0)
                for wicket in ball.get("wickets", []):
                    if wicket["kind"] != "retired hurt":
                        result[wicket["player_out"]]["dismissals"] += 1
                    if wicket["kind"] not in NO_BOWLER_CREDIT:
                        bowl["wickets"] += 1
                    for fielder in wicket.get("fielders", []):
                        if fielder.get("name") and wicket["kind"] in ("caught", "stumped"):
                            key = "stumpings" if wicket["kind"] == "stumped" else "catches"
                            result[fielder["name"]][key] += 1
    return result


def clamp(value):
    return max(1, min(99, round(value)))


def ratings(samples, as_of, format_name):
    # 60-day half-life; small samples regress toward neutral rather than becoming stars.
    weighted = defaultdict(float)
    for played, stats in samples:
        weight = 0.5 ** ((as_of - played).days / 60)
        for key, value in stats.items():
            weighted[key] += value * weight
    balls, legal = weighted["ballsFaced"], weighted["legalBalls"]
    baseline_sr = {"Test": 50, "ODI": 85, "T20": 130}[format_name]
    baseline_econ = {"Test": 3.2, "ODI": 5.5, "T20": 8.0}[format_name]
    batting = bowling = None
    if balls:
        sr = 100 * weighted["runs"] / balls
        avg = weighted["runs"] / max(1, weighted["dismissals"])
        raw = 50 + (sr - baseline_sr) * 0.25 + (min(avg, 100) - 25) * 0.6
        batting = clamp(50 + (raw - 50) * balls / (balls + 120))
    if legal:
        economy = 6 * weighted["conceded"] / legal
        wickets_per_100 = 100 * weighted["wickets"] / legal
        raw = 50 + (baseline_econ - economy) * 5 + (wickets_per_100 - 3) * 5
        bowling = clamp(50 + (raw - 50) * legal / (legal + 120))
    return {"batting": batting, "bowling": bowling,
            "confidence": "established" if max(balls, legal) >= 120 else "limited",
            "scale": "1–99; mapped to 1–62 in the game"}


def build_format(matches, format_name, as_of):
    history = defaultdict(list)
    names, latest, seen, latest_xi, appearances = {}, {}, set(), {}, {}
    for match_id, match in matches:
        info = match["info"]
        if info.get("gender") != "male" or info.get("team_type") != "international":
            continue
        if info.get("match_type") != format_name:
            continue
        played = match_date(match)
        if played > as_of:
            continue
        if match_id in seen:
            continue
        seen.add(match_id)
        if not match.get("innings"):
            continue
        stats = summarize(match) if played >= as_of - timedelta(days=365) else None
        registry = info.get("registry", {}).get("people", {})
        for team, squad in info["players"].items():
            if team not in TEAMS:
                continue
            # Deterministic tie-break for multiple matches on the same date.
            candidate = (played, str(match_id))
            if candidate > latest.get(team, (date.min, '')):
                latest[team] = candidate
                # Player lists are not guaranteed to be batting order. Use the
                # first innings' actual appearances, then uncalled batters.
                order = []
                for innings in match.get('innings', []):
                    if innings.get('team') != team or innings.get('super_over'):
                        continue
                    for over in innings.get('overs', []):
                        for ball in over['deliveries']:
                            for n in (ball['batter'], ball.get('non_striker')):
                                if n in squad and n not in order:
                                    order.append(n)
                    break
                order.extend(n for n in squad if n not in order)
                latest_xi[team] = [registry[n] for n in order]
            for name in squad:
                # Require stable source IDs; never merge people just by their name.
                player_id = registry[name]
                key = (team, player_id)
                if played >= appearances.get(key, date.min):
                    names[key] = name
                appearances[key] = max(appearances.get(key, date.min), played)
                if stats is not None:
                    history[key].append((played, stats.get(name, new_stats())))
    teams = defaultdict(list)
    for (team, player_id), samples in history.items():
        samples.sort(key=lambda item: item[0], reverse=True)
        last_played = samples[0][0]
        samples = samples[:20]
        totals = {key: sum(s[key] for _, s in samples) for key in new_stats()}
        teams[team].append({"id": player_id, "name": names[(team, player_id)],
                            "lastPlayed": last_played.isoformat(), "matches": len(samples),
                            "stats": totals, "ratings": ratings(samples, as_of, format_name)})
    result = []
    for team in sorted(latest):
        by_id = {p['id']: p for p in teams[team]}
        starters = latest_xi[team][:11]
        bench = sorted((i for (country,i), played in appearances.items()
                        if country == team and i not in starters
                        and played >= latest[team][0] - timedelta(days=180)),
                       key=lambda i: (appearances[(team,i)], i), reverse=True)
        selected = starters + bench[:20-len(starters)]
        for player_id in selected:
            if player_id not in by_id:
                by_id[player_id] = {'id': player_id, 'name': names[(team, player_id)],
                                    'lastPlayed': appearances[(team,player_id)].isoformat(), 'matches': 0,
                                    'stats': new_stats(), 'ratings': ratings([], as_of, format_name)}
        players = [{**by_id[i], 'startingXI': i in starters,
                    'battingOrder': starters.index(i)+1 if i in starters else None} for i in selected]
        result.append({"name": team, "gameTeamId": TEAMS[team][0],
                       "logo": 'assets/teams/' + TEAMS[team][1] + '.png',
                       "latestMatch": latest[team][0].isoformat(),
                       "latestMatchId": latest[team][1],
                       "startingXI": starters,
                       "stale": (as_of - latest[team][0]).days > 30,
                       "players": players})
    if not result:
        raise ValueError(f"No recent international {format_name} matches; keeping previous snapshot")
    return {"teams": result, "latestMatch": max(t["latestMatch"] for t in result)}


def refresh(output=OUTPUT, as_of=None, provider=download_matches):
    as_of = as_of or datetime.now(timezone.utc).date()
    formats = {}
    for name in SOURCES:
        print(f"Fetching {name} from Cricsheet…", flush=True)
        formats[name] = build_format(provider(name), name, as_of)
    snapshot = {"schemaVersion": 1, "asOf": as_of.isoformat(),
                "generatedAt": datetime.now(timezone.utc).isoformat(),
                "source": {"name": "Cricsheet", "url": "https://cricsheet.org/",
                           "license": "Open Data Commons Attribution License",
                           "licenseUrl": "https://cricsheet.org/licensing/"},
                "squadPolicy": "Starting XI and batting order from the latest available international match. Up to nine reserves from the same format's participants within 180 days of that match; reserves are not an official call-up list. Source coverage may lag real matches.",
                "ratingPolicy": "Last 20 appearances within 365 days; 60-day decay; small samples regress to 50. Batting uses average and strike rate; bowling uses wickets and economy. Missing skills remain unknown. These are experimental ratings, not ICC ratings.",
                "gameIntegration": "local-launch-patch",
                "formats": formats}
    # All formats must succeed before replacing a known-good snapshot.
    atomic_json(output, snapshot)
    return snapshot


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    refresh(args.output)
