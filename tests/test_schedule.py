"""Stateless business checks; these do not prove cloud persistence or isolation."""
import copy
import csv
import importlib.util
import io
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "platform/scut-schedule/skills/scut-schedule/scripts/schedule.py"


class ScheduleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.demo = json.loads((ROOT / "examples/m0-demo.json").read_text(encoding="utf-8"))

    def setUp(self):
        self.assertTrue(SCRIPT.is_file(), "The schedule helper has not been implemented")
        spec = importlib.util.spec_from_file_location("schedule", SCRIPT)
        self.schedule = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.schedule)

    def test_demo_preserves_source_and_unknown_end_time(self):
        result = self.schedule.prepare_import("", self.demo, "2026-11-08T17:30:00+08:00")
        rows = list(csv.DictReader(io.StringIO(result["csv"])))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["date"], "2026-11-17")
        self.assertEqual(rows[0]["start_time"], "19:00")
        self.assertEqual(rows[0]["end_time"], "")
        self.assertEqual(rows[0]["source_excerpt"], "明天19:00在A201开班会")
        source = json.loads(rows[0]["source"])
        self.assertEqual(source["sent_on"], "2026-11-16")
        self.assertEqual(source["ingested_at"], "2026-11-08T17:30:00+08:00")
        self.assertEqual(result["records"][0]["title"], {"text": "班会"})

    def test_repeat_import_preserves_user_changes_and_original_import_time(self):
        first = self.schedule.prepare_import("", self.demo, "2026-11-08T17:30:00+08:00")
        changed = first["csv"].replace("not_started", "completed").replace("A201", "A202")
        result = self.schedule.prepare_import(changed, self.demo, "2026-11-09T10:00:00+08:00")
        self.assertEqual(result["records"], [])
        self.assertEqual(result["skipped"], ["demo-event-001"])
        self.assertEqual(result["csv"], changed)

    def test_week_uses_monday_sunday_and_separates_real_from_example(self):
        bundle = copy.deepcopy(self.demo)
        bundle["events"] = []
        for ident, day in [("before", "2026-11-15"), ("monday", "2026-11-16"),
                           ("sunday", "2026-11-22"), ("after", "2026-11-23")]:
            event = dict(self.demo["events"][0], id=ident, date=day)
            bundle["events"].append(event)
        first = self.schedule.prepare_import("", bundle, "2026-11-08T17:30:00+08:00")
        real = copy.deepcopy(self.demo)
        real["mode"] = real["sources"][0]["mode"] = "real"
        real["events"][0]["id"] = "real-event"
        result = self.schedule.prepare_import(first["csv"], real, "2026-11-08T17:30:00+08:00")
        week = self.schedule.week(result["csv"], "2026-11-18", "example")
        self.assertEqual(week["start"], "2026-11-16")
        self.assertEqual(week["end"], "2026-11-22")
        self.assertEqual([row["id"] for row in week["events"]], ["monday", "sunday"])

    def test_bad_date_and_missing_source_do_not_produce_upload_payload(self):
        for change in ({"date": "2026-02-30"}, {"source_id": "missing"}):
            with self.subTest(change=change):
                bundle = copy.deepcopy(self.demo)
                bundle["events"][0].update(change)
                with self.assertRaises(ValueError):
                    self.schedule.prepare_import("", bundle, "2026-11-08T17:30:00+08:00")

    def test_wrong_table_is_not_treated_as_an_empty_schedule(self):
        with self.assertRaises(ValueError):
            self.schedule.prepare_import("id,title,status\nprobe-001,探针,completed\n",
                                         self.demo, "2026-11-08T17:30:00+08:00")


if __name__ == "__main__":
    unittest.main()
