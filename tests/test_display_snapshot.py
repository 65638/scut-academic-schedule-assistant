"""Check A's storage boundary with D's shared examples, without a cloud write."""

import importlib
import json
from pathlib import Path
import sys
import unittest

from test_notice_runtime import apply_plan


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "platform/scut-schedule/skills/scut-schedule"
NOW = "2026-11-17T10:00:00+08:00"


class DisplaySnapshotTests(unittest.TestCase):
    def test_shared_events_notice_history_and_questions_survive_one_snapshot(self):
        sys.path.insert(0, str(SKILL / "scripts"))
        self.addCleanup(sys.path.remove, str(SKILL / "scripts"))
        schedule = importlib.import_module("schedule")
        runtime = importlib.import_module("runtime")
        notices = importlib.import_module("notice_runtime")
        shared = json.loads((ROOT / "docs/协作/联调样例.json").read_text(encoding="utf-8"))
        bundle = shared["D"]["input_bundle"]
        # Existing saved statuses must reach D so it can filter alerts, not history.
        bundle["events"][0]["status"] = "completed"
        bundle["events"][1]["status"] = "cancelled"
        content = schedule.prepare_import("", bundle, NOW)["csv"]
        notice = json.loads((SKILL / "examples/m2-notice-save.json").read_text(encoding="utf-8"))
        correction = json.loads((SKILL / "examples/m2-notice-correction.json").read_text(encoding="utf-8"))
        content = apply_plan(content, notices.prepare_notice(content, notice, NOW))
        content = apply_plan(content, notices.prepare_correction(content, correction, NOW))
        message = {
            "text": "明天20:00在B101开M1混合讨论会，请大家准时参加，下周一交实验报告",
            "sent_on": "2026-11-16", "today": "2026-11-17", "mode": "example",
            "source_id": "display-mixed-message",
        }
        message_plan = runtime.prepare_message(content, message, NOW)
        self.assertFalse(message_plan["saved_to_cloud"])
        self.assertTrue(message_plan["questions"])
        content = apply_plan(content, message_plan)

        restored = notices.notice_snapshot(content, "example", "2026-11-17")
        events = {event["id"]: event for event in restored["events"]}
        for expected in bundle["events"]:
            self.assertEqual({key: events[expected["id"]][key] for key in expected}, expected)
            self.assertEqual(events[expected["id"]]["history"], [])
        self.assertEqual(restored["questions"], message_plan["questions"])
        saved_notice = events["handoff-c-event-001"]
        self.assertEqual((saved_notice["date"], saved_notice["start_time"]), ("2026-11-27", "17:00"))
        self.assertEqual(saved_notice["m2"]["extraction"]["materials"], ["报名表PDF"])
        self.assertEqual(saved_notice["history"][0]["changes"]["date"],
                         {"before": "2026-11-25", "after": "2026-11-27"})
        self.assertEqual(saved_notice["history"][0]["applied_at"], NOW)
        sources = {source["id"]: source for source in restored["sources"]}
        self.assertEqual(sources[correction["correction"]["id"]]["text"], correction["correction"]["text"])
        for source in bundle["sources"]:
            self.assertEqual(sources[source["id"]]["text"], source["text"])


if __name__ == "__main__":
    unittest.main()
