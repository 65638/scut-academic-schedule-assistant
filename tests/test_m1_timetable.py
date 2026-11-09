"""课表周次、单次编号和 M0 新增路径回归。"""

import importlib
import json
import sys
import unittest

from modules.m1.timetable import parse_timetable
from modules.m1.updates import plan_import
from test_runtime import NOW, ROOT, SCRIPTS


EXAMPLES = ROOT / "modules/m1/examples"


class TimetableTests(unittest.TestCase):
    def setUp(self):
        self.text = (EXAMPLES / "timetable.csv").read_text(encoding="utf-8")
        self.config = json.loads((EXAMPLES / "term-config.json").read_text(encoding="utf-8"))
        self.bundle = parse_timetable(self.text, self.config, file_name="timetable.csv")

    def test_each_even_odd_week_and_evidence(self):
        events = self.bundle["events"]
        self.assertEqual(
            [(e["date"], e["start_time"], e["end_time"]) for e in events],
            [("2026-11-17", "14:00", "15:35"), ("2026-11-24", "14:00", "15:35")],
        )
        self.assertEqual([e["source_excerpt"] for e in events], [self.text.splitlines()[1]] * 2)
        self.assertEqual([e["source_id"] for e in events], [self.bundle["sources"][0]["id"]] * 2)
        self.assertNotEqual(events[0]["id"], events[1]["id"])
        for parity, expected in (("双周", events[0]), ("单周", events[1])):
            with self.subTest(parity=parity):
                result = parse_timetable(self.text.replace("每周", parity), self.config)["events"]
                self.assertEqual([(e["id"], e["date"]) for e in result], [(expected["id"], expected["date"])])

    def test_partial_replay_adds_missing_occurrence_and_full_replay_skips_both(self):
        sys.path.insert(0, str(SCRIPTS))
        self.addCleanup(sys.path.remove, str(SCRIPTS))
        runtime = importlib.import_module("runtime")
        schedule = importlib.import_module("schedule")
        first, second = self.bundle["events"]
        saved = schedule.prepare_import("", dict(self.bundle, events=[first]), NOW)["csv"]
        current = runtime.current_bundle(saved, "example", self.config["today"])
        partial = plan_import(self.bundle, current)
        self.assertEqual(partial["skipped_event_ids"], [first["id"]])
        self.assertEqual(partial["bundle"]["events"], [second])
        result = schedule.prepare_import(saved, partial["bundle"], NOW)
        self.assertEqual(len(result["records"]), 1)

        restored = runtime.current_bundle(result["csv"], "example", self.config["today"])
        replay = plan_import(parse_timetable(self.text, self.config), restored)
        self.assertEqual(replay["bundle"]["events"], [])
        self.assertEqual(replay["skipped_event_ids"], [first["id"], second["id"]])

    def test_quoted_csv_row_is_preserved(self):
        text = self.text.replace("合成课表", '"合成,备注\n第二行"')
        source = parse_timetable(text, self.config)["events"][0]["source_excerpt"]
        self.assertEqual(source, text.split("\n", 1)[1].rstrip("\n"))
