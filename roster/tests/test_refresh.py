from datetime import date
import copy
import json
from pathlib import Path
import tempfile
import unittest

from roster.refresh import build_format, ratings, refresh, summarize


def fixture():
    return {"info": {"gender": "male", "team_type": "international", "match_type": "ODI",
                     "dates": ["2026-10-30"], "players": {"India": ["A Batter", "B Bowler"], "England": ["C Player"]},
                     "registry": {"people": {"A Batter": "a", "B Bowler": "b", "C Player": "c"}}},
            "innings": [{"overs": [{"deliveries": [
                {"batter": "A Batter", "bowler": "C Player", "runs": {"batter": 4, "total": 4}},
                {"batter": "A Batter", "bowler": "C Player", "runs": {"batter": 0, "total": 2}, "extras": {"wides": 2}},
                {"batter": "A Batter", "bowler": "C Player", "runs": {"batter": 1, "total": 2}, "extras": {"noballs": 1}},
                {"batter": "A Batter", "bowler": "C Player", "runs": {"batter": 0, "total": 2}, "extras": {"legbyes": 2}},
                {"batter": "A Batter", "bowler": "C Player", "runs": {"batter": 0, "total": 0},
                 "wickets": [{"player_out": "A Batter", "kind": "run out"}]}
            ]}]}]}


class StatsTests(unittest.TestCase):
    def test_extras_and_run_out(self):
        stats = summarize(fixture())
        self.assertEqual(stats["A Batter"]["runs"], 5)
        self.assertEqual(stats["A Batter"]["ballsFaced"], 4)
        self.assertEqual(stats["A Batter"]["dismissals"], 1)
        self.assertEqual(stats["C Player"]["legalBalls"], 3)
        self.assertEqual(stats["C Player"]["conceded"], 8)
        self.assertEqual(stats["C Player"]["wickets"], 0)

    def test_bowler_credit_and_super_over(self):
        match = fixture()
        delivery = match["innings"][0]["overs"][0]["deliveries"][-1]
        delivery["wickets"][0].update(kind="caught", fielders=[{"name": "B Bowler"}])
        extra = copy.deepcopy(match["innings"][0])
        extra["super_over"] = True
        match["innings"].append(extra)
        stats = summarize(match)
        self.assertEqual(stats["C Player"]["wickets"], 1)
        self.assertEqual(stats["B Bowler"]["catches"], 1)
        self.assertEqual(stats["A Batter"]["runs"], 5)

    def test_formats_future_matches_and_duplicates(self):
        match = fixture()
        future = copy.deepcopy(match)
        future["info"]["dates"] = ["2026-11-10"]
        test = copy.deepcopy(match)
        test["info"]["match_type"] = "Test"
        data = build_format([("1", match), ("1", match), ("2", future), ("3", test)], "ODI", date(2026, 11, 2))
        india = next(t for t in data["teams"] if t["name"] == "India")
        self.assertTrue(all(p["matches"] == 1 for p in india["players"]))
        self.assertEqual(data["latestMatch"], "2026-10-30")

    def test_unknown_skills_are_not_invented(self):
        values = ratings([], date(2026, 11, 2), "ODI")
        self.assertIsNone(values["batting"])
        self.assertIsNone(values["bowling"])

    def test_unnamed_fielder(self):
        match = fixture()
        wicket = match["innings"][0]["overs"][0]["deliveries"][-1]["wickets"][0]
        wicket.update(kind="caught", fielders=[{"substitute": True}])
        self.assertEqual(summarize(match)["C Player"]["wickets"], 1)

    def test_better_form_increases_rating(self):
        low = summarize(fixture())["A Batter"]
        high = dict(low, runs=90, ballsFaced=60)
        day = date(2026, 11, 2)
        self.assertGreater(ratings([(day, high)], day, "ODI")["batting"], ratings([(day, low)], day, "ODI")["batting"])

    def test_failed_refresh_preserves_snapshot(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "rosters.json"
            target.write_text('{"previous": true}', encoding="utf-8")
            def unavailable(_):
                raise OSError("network unavailable")
            with self.assertRaises(OSError):
                refresh(target, date(2026, 11, 2), unavailable)
            self.assertEqual(json.loads(target.read_text()), {"previous": True})

    def test_inactive_players_are_excluded(self):
        match = fixture()
        match["info"]["dates"] = ["2026-01-01"]
        with self.assertRaises(ValueError):
            build_format([("old", match)], "ODI", date(2026, 11, 2))


if __name__ == "__main__":
    unittest.main()
