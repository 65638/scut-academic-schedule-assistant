"""使用现有 M0 写入载荷与 A 快照验证 M1 更新的本地往返。"""

import importlib
import json
import sys
import unittest

from modules.m1.message import parse_message
from modules.m1.timetable import parse_timetable
from modules.m1.updates import plan_import, propose_event_update
from test_runtime import NOW, ROOT, SCRIPTS, apply_plan


class M1WorkflowTests(unittest.TestCase):
    def setUp(self):
        sys.path.insert(0, str(SCRIPTS))
        self.addCleanup(sys.path.remove, str(SCRIPTS))
        self.runtime = importlib.import_module("runtime")
        self.schedule = importlib.import_module("schedule")
        examples = ROOT / "modules/m1/examples"
        self.messages = json.loads((examples / "d2-d3-workflow.json").read_text(encoding="utf-8"))
        config = json.loads((examples / "term-config.json").read_text(encoding="utf-8"))
        self.timetable = parse_timetable((examples / "timetable.csv").read_text(encoding="utf-8"), config)
        self.assignment = parse_message(self.messages["assignment"])

    def snapshot(self, content):
        return self.runtime.current_bundle(content, "example", "2026-11-16")

    def apply_update(self, content, kind):
        proposal = propose_event_update(self.messages[kind], self.snapshot(content))
        row = next(row for row in self.schedule.read_rows(content) if row["id"] == proposal["target_event_id"])
        patch = self.runtime._patch(row, proposal["changes"], proposal["source"], kind, NOW)
        return apply_plan(content, {"records": [], "updates": [patch]})

    def test_assignment_requirements_deadline_and_completed_round_trip(self):
        content = self.schedule.prepare_import("", self.assignment, NOW)["csv"]
        original = self.snapshot(content)
        event = original["events"][0]
        self.assertEqual((event["type"], event["date"], event["start_time"], event["end_time"]),
                         ("submission", "2026-11-20", "20:00", None))
        self.assertEqual(original["sources"][0]["submission_requirements"], {event["id"]: ["PDF"]})

        content = self.apply_update(content, "postpone")
        content = self.apply_update(content, "complete")
        incoming = parse_message(self.messages["assignment"])
        replay = self.schedule.prepare_import(content, incoming, NOW)
        self.assertEqual(replay["records"], [])
        restored = self.snapshot(replay["csv"])
        after = restored["events"][0]
        self.assertEqual((after["id"], after["source_id"]), (event["id"], event["source_id"]))
        self.assertEqual((after["date"], after["start_time"], after["status"]), ("2026-11-22", "21:00", "completed"))
        self.assertEqual(restored["sources"][0]["submission_requirements"], {event["id"]: ["PDF"]})
        self.assertEqual([h["kind"] for h in after["history"]], ["postpone", "complete"])
        self.assertEqual(after["history"][1]["source"]["text"], self.messages["complete"]["text"])

    def test_only_selected_occurrence_moves_and_cancel_survives_replay(self):
        content = self.schedule.prepare_import("", self.timetable, NOW)["csv"]
        first, second = self.snapshot(content)["events"]
        ambiguous = dict(self.messages["reschedule"])
        del ambiguous["target_date"]
        result = propose_event_update(ambiguous, self.snapshot(content))
        self.assertIsNone(result["target_event_id"])
        self.assertEqual(result["changes"], {})
        self.assertEqual([e["id"] for e in result["candidates"]], [first["id"], second["id"]])

        content = self.apply_update(content, "reschedule")
        moved, untouched = self.snapshot(content)["events"]
        self.assertEqual((moved["id"], moved["date"], moved["location"]),
                         (first["id"], "2026-11-18", "大学城校区 B202"))
        self.assertEqual(untouched, second)
        content = self.apply_update(content, "cancel")
        replay = plan_import(self.timetable, self.snapshot(content))
        self.assertEqual(replay["skipped_event_ids"], [first["id"], second["id"]])
        after = self.schedule.prepare_import(content, replay["bundle"], NOW)
        self.assertEqual(after["records"], [])
        restored, untouched = self.snapshot(after["csv"])["events"]
        self.assertEqual((restored["id"], restored["date"], restored["location"], restored["status"]),
                         (first["id"], "2026-11-18", "大学城校区 B202", "cancelled"))
        self.assertEqual(restored["source_id"], first["source_id"])
        self.assertEqual(restored["source_excerpt"], first["source_excerpt"])
        self.assertEqual(restored["history"][0]["source"]["text"], self.messages["reschedule"]["text"])
        self.assertEqual(untouched, second)

    def test_invalid_updates_cannot_overwrite_identity_or_reverse_time(self):
        current = dict(self.timetable, events=self.timetable["events"] + self.assignment["events"])
        for kind, changes in (
            ("reschedule", {"id": "other-id"}),
            ("reschedule", {"start_time": "16:00"}),
            ("postpone", {"date": "2026-11-19"}),
        ):
            with self.subTest(kind=kind, changes=changes), self.assertRaises(ValueError):
                propose_event_update(dict(self.messages[kind], changes=changes), current)
