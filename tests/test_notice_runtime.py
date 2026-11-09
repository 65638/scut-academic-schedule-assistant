import copy
import csv
import importlib
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "platform/scut-schedule/skills/scut-schedule/scripts"
FIXTURES = ROOT / "modules/m2/fixtures"
NOW = "2026-11-09T12:00:00+08:00"


def apply_plan(content, plan):
    rows = list(csv.DictReader(io.StringIO(content))) if content else []
    for record in plan["records"]:
        rows.append({key: value["text"] for key, value in record.items()})
    for update in plan["updates"]:
        row = next(item for item in rows if item["id"] == update["event_id"])
        row.update({key: value["text"] for key, value in update["properties"].items()})
    if not rows:
        return content
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=list(rows[0]), lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()


def read_fixture(name):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


class NoticeRuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, str(SCRIPTS))
        cls.runtime = importlib.import_module("notice_runtime")

    @classmethod
    def tearDownClass(cls):
        sys.path.remove(str(SCRIPTS))

    def notice_payload(self, save=True, confirmed=False):
        fixture = read_fixture("handoff_c.json")
        return {
            "source": fixture["input"],
            "profile": fixture["profile"],
            "today": fixture["today"],
            "candidate_extraction": fixture["expected_extraction"],
            "save_requested": save,
            "applicability_confirmed": confirmed,
        }

    def save_notice(self, payload=None, content=""):
        plan = self.runtime.prepare_notice(content, payload or self.notice_payload(), NOW)
        return apply_plan(content, plan), plan

    def correction_payload(self, save=True):
        fixture = read_fixture("handoff_c_correction.json")
        return dict(
            fixture,
            mode="example",
            profile={
                "campus": "大学城校区",
                "education_level": "undergraduate",
            },
            save_requested=save,
            applicability_confirmed=False,
        )

    def test_import_query_and_new_process_snapshot_restore_m2(self):
        content, plan = self.save_notice()
        self.assertEqual(len(plan["records"]), 1)
        self.assertEqual(plan["updates"], [])
        source = json.loads(plan["records"][0]["source"]["text"])
        fixture_source = self.notice_payload()["source"]
        self.assertEqual(source["text"], fixture_source["text"])
        self.assertEqual(source["published_on"], fixture_source["published_on"])
        self.assertEqual(source["m2"]["extraction"]["materials"], ["报名表PDF"])

        snapshot = self.runtime.notice_snapshot(content, "example", "2026-11-16")
        self.assertEqual(snapshot["events"][0]["m2"]["extraction"]["relevance"], "明确相关")
        self.assertEqual(snapshot["events"][0]["history"], [])

        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            shutil.copytree(SCRIPTS, base / "scripts", ignore=shutil.ignore_patterns("__pycache__"))
            existing = base / "schedule.csv"
            existing.write_text(content, encoding="utf-8")
            result = subprocess.run(
                [
                    sys.executable,
                    "-X",
                    "utf8",
                    str(base / "scripts/notice_runtime.py"),
                    "snapshot",
                    "--existing",
                    str(existing),
                    "--mode",
                    "example",
                    "--today",
                    "2026-11-16",
                    "--out",
                    str(base / "snapshot.json"),
                ],
                cwd=base,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            restored = json.loads((base / "snapshot.json").read_text(encoding="utf-8"))
            self.assertEqual(restored["events"][0]["m2"]["extraction"]["materials"], ["报名表PDF"])

    def test_relevance_and_save_gates_produce_zero_writes(self):
        no_save = self.runtime.prepare_notice("", self.notice_payload(save=False), NOW)
        self.assertEqual(no_save["records"] + no_save["updates"], [])
        self.assertEqual(no_save["questions"][0]["field"], "save_requested")

        not_applicable = self.notice_payload()
        not_applicable["profile"] = dict(not_applicable["profile"], campus="五山校区")
        not_applicable["candidate_extraction"] = dict(
            not_applicable["candidate_extraction"],
            relevance="不适用",
            missing_profile_question=None,
        )
        rejected = self.runtime.prepare_notice("", not_applicable, NOW)
        self.assertEqual(rejected["records"] + rejected["updates"], [])
        self.assertEqual(rejected["questions"][0]["field"], "relevance")

        possible = self.notice_payload()
        possible["profile"] = {"education_level": "undergraduate"}
        possible["candidate_extraction"] = dict(
            possible["candidate_extraction"],
            relevance="可能相关",
            missing_profile_question="请确认你的校区。",
        )
        pending = self.runtime.prepare_notice("", possible, NOW)
        self.assertEqual(pending["records"] + pending["updates"], [])
        self.assertEqual(pending["questions"][0]["field"], "applicability_confirmed")
        possible["applicability_confirmed"] = True
        confirmed = self.runtime.prepare_notice("", possible, NOW)
        self.assertEqual(len(confirmed["records"]), 1)
        saved_source = json.loads(confirmed["records"][0]["source"]["text"])
        self.assertEqual(saved_source["questions"], [])

        for field in ("save_requested", "applicability_confirmed"):
            with self.subTest(field=field):
                invalid = self.notice_payload()
                invalid[field] = "false"
                with self.assertRaisesRegex(ValueError, "JSON boolean"):
                    self.runtime.prepare_notice("", invalid, NOW)

    def test_replay_preserves_user_location_status_and_rejects_source_collision(self):
        content, _ = self.save_notice()
        rows = list(csv.DictReader(io.StringIO(content)))
        rows[0]["location"] = "用户地点"
        rows[0]["status"] = "completed"
        output = io.StringIO(newline="")
        writer = csv.DictWriter(output, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
        changed = output.getvalue()

        replay = self.runtime.prepare_notice(changed, self.notice_payload(), NOW)
        self.assertEqual(replay["records"] + replay["updates"], [])
        self.assertEqual(replay["skipped_event_ids"], ["handoff-c-event-001"])
        restored = self.runtime.notice_snapshot(changed, "example", "2026-11-16")["events"][0]
        self.assertEqual((restored["location"], restored["status"]), ("用户地点", "completed"))

        colliding = self.notice_payload()
        colliding["source"] = dict(colliding["source"], text=colliding["source"]["text"] + "补充")
        with self.assertRaisesRegex(ValueError, "来源编号已存在"):
            self.runtime.prepare_notice(changed, colliding, NOW)

    def test_date_correction_history_replay_and_unrelated_event(self):
        content, _ = self.save_notice()
        other = self.notice_payload()
        other["source"] = dict(other["source"], id="other-notice-001", title="其他通知")
        other["candidate_extraction"] = dict(other["candidate_extraction"])
        content, _ = self.save_notice(other, content)
        before_other = next(row for row in csv.DictReader(io.StringIO(content)) if row["id"] == "other-event-001")

        payload = self.correction_payload()
        plan = self.runtime.prepare_correction(content, payload, NOW)
        self.assertEqual(len(plan["updates"]), 1)
        changed = apply_plan(content, plan)
        rows = list(csv.DictReader(io.StringIO(changed)))
        target = next(row for row in rows if row["id"] == "handoff-c-event-001")
        after_other = next(row for row in rows if row["id"] == "other-event-001")
        self.assertEqual(target["date"], "2026-11-27")
        self.assertEqual(after_other, before_other)
        stored = json.loads(target["source"])
        self.assertEqual(stored["m2"]["latest_source_id"], "handoff-c-notice-002")
        self.assertEqual(stored["event_history"][0]["changes"]["date"], {
            "before": "2026-11-25", "after": "2026-11-27"
        })
        self.assertEqual(stored["event_history"][0]["source"]["text"], payload["correction"]["text"])

        replay = self.runtime.prepare_correction(changed, payload, NOW)
        self.assertEqual(replay["updates"], [])
        self.assertEqual(replay["skipped_event_ids"], ["handoff-c-event-001"])
        snapshot = self.runtime.notice_snapshot(changed, "example", "2026-11-16")
        self.assertEqual(len(snapshot["events"][0]["history"]), 1)

    def test_second_correction_uses_latest_source_and_current_before(self):
        content, _ = self.save_notice()
        first = self.correction_payload()
        content = apply_plan(content, self.runtime.prepare_correction(content, first, NOW))
        second_source = {
            "id": "handoff-c-notice-003",
            "type": "notice",
            "title": "示例报名通知再次更正",
            "mode": "example",
            "text": "【示例更正】报名表PDF提交截止由2026年11月27日17:00延长至2026年11月29日17:00。",
            "publisher": "示例发布单位（非真实学校机构）",
            "published_on": "2026-11-18",
            "file_name": "test_notice_runtime.py",
            "corrects": "handoff-c-notice-002",
        }
        second = {
            "original_source": first["correction"],
            "correction": second_source,
            "target_event_id": "handoff-c-event-001",
            "mode": "example",
            "profile": first["profile"],
            "save_requested": True,
        }
        content = apply_plan(content, self.runtime.prepare_correction(content, second, NOW))
        row = next(csv.DictReader(io.StringIO(content)))
        self.assertEqual(row["date"], "2026-11-29")
        self.assertEqual(len(json.loads(row["source"])["event_history"]), 2)

        stale = copy.deepcopy(second)
        stale["correction"]["id"] = "handoff-c-notice-stale"
        stale["correction"]["text"] = "截止由2026年11月25日17:00延长至2026年11月30日17:00。"
        stale["correction"]["corrects"] = "handoff-c-notice-003"
        stale["original_source"] = second_source
        with self.assertRaisesRegex(ValueError, "before 与当前事项不一致"):
            self.runtime.prepare_correction(content, stale, NOW)

    def test_invalid_correction_target_chain_mode_and_id_collision_are_rejected(self):
        content, _ = self.save_notice()
        missing = self.correction_payload()
        missing["target_event_id"] = "missing"
        self.assertEqual(
            self.runtime.prepare_correction(content, missing, NOW)["questions"][0]["field"],
            "target_event_id",
        )

        invalid_chain = self.correction_payload()
        invalid_chain["correction"] = dict(invalid_chain["correction"], corrects="other")
        with self.assertRaisesRegex(ValueError, "最新来源"):
            self.runtime.prepare_correction(content, invalid_chain, NOW)

        cross_mode = self.correction_payload()
        cross_mode["correction"] = dict(cross_mode["correction"], mode="real")
        with self.assertRaisesRegex(ValueError, "同一模式"):
            self.runtime.prepare_correction(content, cross_mode, NOW)

        rows = list(csv.DictReader(io.StringIO(content)))
        duplicate = dict(rows[0], mode="real")
        duplicate_source = json.loads(duplicate["source"])
        duplicate_source["mode"] = "real"
        duplicate["source"] = json.dumps(duplicate_source, ensure_ascii=False)
        output = io.StringIO(newline="")
        writer = csv.DictWriter(output, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows + [duplicate])
        with self.assertRaisesRegex(ValueError, "多条记录"):
            self.runtime.prepare_correction(output.getvalue(), self.correction_payload(), NOW)

        content = apply_plan(
            content, self.runtime.prepare_correction(content, self.correction_payload(), NOW)
        )
        collision = self.correction_payload()
        collision["correction"] = dict(collision["correction"], text="同编号不同原文")
        with self.assertRaisesRegex(ValueError, "编号已存在"):
            self.runtime.prepare_correction(content, collision, NOW)

        for field in ("save_requested", "applicability_confirmed"):
            with self.subTest(field=field):
                invalid_flag = self.correction_payload()
                invalid_flag[field] = "false"
                with self.assertRaisesRegex(ValueError, "JSON boolean"):
                    self.runtime.prepare_correction(content, invalid_flag, NOW)

    def test_unrecognized_correction_is_a_zero_write_question(self):
        content, _ = self.save_notice()
        payload = self.correction_payload()
        payload["correction"] = dict(
            payload["correction"],
            id="handoff-c-notice-unknown",
            text="通知增加一段说明，其余事项不变。",
        )
        result = self.runtime.prepare_correction(content, payload, NOW)
        self.assertEqual(result["records"] + result["updates"], [])
        self.assertEqual(result["questions"][0]["field"], "source_excerpt")

    def test_audience_extension_requires_confirmation_and_updates_metadata_only(self):
        fixture = read_fixture("u4_audience_correction.json")
        source = fixture["original_source"]
        payload = {
            "source": source,
            "profile": {
                "college": "A学院",
                "grade": "2023级",
                "education_level": "undergraduate",
            },
            "today": "2026-11-16",
            "save_requested": True,
        }
        content, _ = self.save_notice(payload)
        correction = dict(
            fixture,
            mode="example",
            profile=payload["profile"],
            save_requested=True,
            applicability_confirmed=False,
        )
        pending = self.runtime.prepare_correction(content, correction, NOW)
        self.assertEqual(pending["updates"], [])
        self.assertEqual(pending["questions"][0]["field"], "applicability_confirmed")
        correction["applicability_confirmed"] = True
        changed = apply_plan(content, self.runtime.prepare_correction(content, correction, NOW))
        row = next(csv.DictReader(io.StringIO(changed)))
        source_data = json.loads(row["source"])
        self.assertIn("2022级", source_data["m2"]["extraction"]["audience"])
        self.assertEqual(source_data["m2"]["extraction"]["relevance"], "明确相关")
        self.assertIsNone(source_data["m2"]["extraction"]["missing_profile_question"])
        self.assertEqual(source_data["m2"]["extraction"]["basis"], fixture["correction"]["text"])
        self.assertNotIn("audience", row)

    def test_combined_correction_updates_old_audience_or_adds_new_audience(self):
        fixture = read_fixture("u4_audience_correction.json")
        original = dict(fixture["original_source"],
                        text=fixture["original_source"]["text"] + "办理地点为A101。")
        correction = dict(
            fixture["correction"],
            text="截止日期由2026年11月25日17:00调整为2026年11月27日18:00，新增A学院2022级本科生为适用对象。"
                 "所需材料由申请表调整为申请表、证明材料；办理地点由A101改为B202。",
        )
        profile = {"college": "A学院", "grade": "2023级", "education_level": "undergraduate"}
        payload = {
            "original_source": original, "correction": correction,
            "mode": "example", "today": "2026-11-16", "profile": profile,
            "save_requested": True, "applicability_confirmed": True,
        }
        original_input = {"source": original, "profile": profile, "today": payload["today"], "save_requested": True}
        content, _ = self.save_notice(original_input)
        target_id = fixture["target_event_id"]
        old_plan = self.runtime.prepare_correction(content, dict(payload, target_event_id=target_id), NOW)
        self.assertEqual(old_plan["records"], [])
        self.assertEqual([update["event_id"] for update in old_plan["updates"]], [target_id])
        self.assertEqual(old_plan["proposal"]["changes"]["date"], {"before": "2026-11-25", "after": "2026-11-27"})

        new_profile = dict(profile, grade="2022级")
        self.assertEqual(self.runtime.prepare_notice("", dict(original_input, profile=new_profile), NOW)["records"], [])
        new_payload = dict(payload, profile=new_profile, newly_applicable=True)
        pending = self.runtime.prepare_correction("", dict(new_payload, applicability_confirmed=False), NOW)
        self.assertEqual(pending["records"] + pending["updates"], [])
        self.assertEqual(pending["questions"][0]["field"], "applicability_confirmed")
        pending_save = self.runtime.prepare_correction("", dict(new_payload, save_requested=False), NOW)
        self.assertEqual(pending_save["records"] + pending_save["updates"], [])
        self.assertEqual(pending_save["questions"][0]["field"], "save_requested")
        existing = self.runtime.prepare_correction(content, new_payload, NOW)
        self.assertEqual(existing["records"] + existing["updates"], [])
        self.assertEqual(existing["questions"][0]["field"], "target_event_id")
        new_plan = self.runtime.prepare_correction("", new_payload, NOW)
        self.assertEqual(new_plan["updates"], [])
        self.assertEqual(len(new_plan["records"]), 1)

        for prior, plan, replay_payload in (
            (content, old_plan, dict(payload, target_event_id=target_id)),
            ("", new_plan, new_payload),
        ):
            with self.subTest(newly_applicable=not prior):
                changed = apply_plan(prior, plan)
                snapshot = self.runtime.notice_snapshot(changed, "example", payload["today"])
                event, = snapshot["events"]
                self.assertEqual((event["id"], event["source_id"]), (target_id, original["id"]))
                self.assertEqual((event["date"], event["start_time"], event["location"]),
                                 ("2026-11-27", "18:00", "B202"))
                self.assertEqual(event["m2"]["extraction"]["materials"], ["申请表", "证明材料"])
                self.assertEqual(event["history"][0]["source"], dict(correction, ingested_at=NOW))
                replay = self.runtime.prepare_correction(changed, replay_payload, NOW)
                self.assertEqual(replay["records"] + replay["updates"], [])
                self.assertEqual(replay["skipped_event_ids"], [target_id])
                original_replay = self.runtime.prepare_notice(changed, original_input, NOW)
                self.assertEqual(original_replay["records"] + original_replay["updates"], [])

    def test_real_notice_keeps_null_time_and_original_ingested_at(self):
        payload = read_fixture("real_job_subsidy.json")
        payload.update(save_requested=True, applicability_confirmed=True)
        content, plan = self.save_notice(payload)
        row = next(csv.DictReader(io.StringIO(content)))
        source = json.loads(row["source"])
        self.assertEqual(row["type"], "submission")
        self.assertEqual(row["date"], "2026-11-10")
        self.assertEqual(row["start_time"], "")
        self.assertEqual(source["ingested_at"], payload["source"]["ingested_at"])
        self.assertEqual(plan["saved_to_cloud"], False)

    def test_date_only_correction_preserves_prior_applicability_confirmation(self):
        payload = read_fixture("real_job_subsidy.json")
        payload.update(save_requested=True, applicability_confirmed=True)
        content, _ = self.save_notice(payload)
        correction_source = {
            "id": "scut-student-2026-1027-job-subsidy-correction",
            "type": "notice",
            "title": "求职补贴申请日期更正",
            "mode": "real",
            "text": "申请日期由2026年11月10日调整为2026年11月11日。",
            "publisher": payload["source"]["publisher"],
            "published_on": "2026-11-09",
            "ingested_at": "2026-11-09T13:00:00+08:00",
            "url": payload["source"]["url"],
            "corrects": payload["source"]["id"],
        }
        correction = {
            "original_source": payload["source"],
            "correction": correction_source,
            "target_event_id": "scut-student-2026-1027-job-subsidy-event",
            "mode": "real",
            "profile": payload["profile"],
            "save_requested": True,
            "applicability_confirmed": False,
        }
        changed = apply_plan(
            content, self.runtime.prepare_correction(content, correction, NOW)
        )
        snapshot = self.runtime.notice_snapshot(changed, "real", "2026-11-09")
        self.assertTrue(snapshot["events"][0]["m2"]["applicability_confirmed"])

    def test_packaged_m2_is_byte_identical(self):
        for name in ("notice.py", "__init__.py"):
            self.assertEqual(
                (ROOT / "modules/m2" / name).read_bytes(),
                (SCRIPTS / "m2" / name).read_bytes(),
            )

    def test_packaged_cli_notice_and_correction_examples(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            scripts = base / "scripts"
            shutil.copytree(SCRIPTS, scripts, ignore=shutil.ignore_patterns("__pycache__"))
            notice_input = ROOT / "platform/scut-schedule/skills/scut-schedule/examples/m2-notice-save.json"
            correction_input = ROOT / "platform/scut-schedule/skills/scut-schedule/examples/m2-notice-correction.json"
            notice_plan_path = base / "notice-plan.json"
            notice_result = subprocess.run(
                [
                    sys.executable,
                    "-X",
                    "utf8",
                    str(scripts / "notice_runtime.py"),
                    "notice",
                    "--input",
                    str(notice_input),
                    "--out",
                    str(notice_plan_path),
                ],
                cwd=base,
                capture_output=True,
                text=True,
            )
            self.assertEqual(notice_result.returncode, 0, notice_result.stderr)
            notice_plan = json.loads(notice_plan_path.read_text(encoding="utf-8"))
            self.assertEqual(len(notice_plan["records"]), 1)
            existing = base / "schedule.csv"
            existing.write_text(apply_plan("", notice_plan), encoding="utf-8")

            correction_plan_path = base / "correction-plan.json"
            correction_result = subprocess.run(
                [
                    sys.executable,
                    "-X",
                    "utf8",
                    str(scripts / "notice_runtime.py"),
                    "correction",
                    "--existing",
                    str(existing),
                    "--input",
                    str(correction_input),
                    "--out",
                    str(correction_plan_path),
                ],
                cwd=base,
                capture_output=True,
                text=True,
            )
            self.assertEqual(correction_result.returncode, 0, correction_result.stderr)
            correction_plan = json.loads(
                correction_plan_path.read_text(encoding="utf-8")
            )
            self.assertEqual(len(correction_plan["updates"]), 1)
            self.assertEqual(
                correction_plan["proposal"]["changes"]["date"]["after"],
                "2026-11-27",
            )


if __name__ == "__main__":
    unittest.main()
