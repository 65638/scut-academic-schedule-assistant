import json
import unittest
from pathlib import Path

from modules.m2.cli import _extract
from modules.m2.notice import (
    assess_relevance,
    build_bundle,
    compare_notice_versions,
    extract_notice,
    refresh_sources,
    verify_handoff_dates,
)


FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


class NoticeExtractionTests(unittest.TestCase):
    def test_handoff_extraction_and_bundle(self) -> None:
        payload = json.loads((FIXTURES / "handoff_c.json").read_text(encoding="utf-8"))
        extraction = extract_notice(payload["input"], payload["profile"])

        self.assertEqual(payload["expected_extraction"], extraction)

        bundle = build_bundle(payload["input"], extraction, payload["today"])
        self.assertEqual("handoff-c-event-001", bundle["events"][0]["id"])
        self.assertEqual("submission", bundle["events"][0]["type"])
        self.assertEqual("2026-11-25", bundle["events"][0]["date"])
        self.assertEqual("17:00", bundle["events"][0]["start_time"])
        self.assertEqual(
            "请于2026年11月25日17:00前提交报名表PDF",
            bundle["events"][0]["source_excerpt"],
        )

    def test_relevance_mismatch_and_missing_profile(self) -> None:
        basis = "面向2022级A学院本科生。"
        mismatch = assess_relevance(
            "2022级A学院本科生",
            basis,
            {"grade": "2023级", "college": "A学院", "education_level": "undergraduate"},
        )
        self.assertEqual("不适用", mismatch["relevance"])

        missing = assess_relevance(
            "A学院本科生",
            "面向A学院本科生。",
            {"education_level": "undergraduate"},
        )
        self.assertEqual("可能相关", missing["relevance"])
        self.assertEqual("请确认你的学院。", missing["missing_profile_question"])

    def test_grade_prefix_is_not_part_of_college_or_major(self) -> None:
        matching = assess_relevance(
            "2022级A学院计算机专业本科生",
            "面向2022级A学院计算机专业本科生。",
            {
                "grade": "2022级",
                "college": "A学院",
                "major": "计算机专业",
                "education_level": "undergraduate",
            },
        )
        self.assertEqual("明确相关", matching["relevance"])

    def test_specific_graduate_levels_do_not_match_each_other(self) -> None:
        master_only = assess_relevance(
            "A学院硕士研究生",
            "面向A学院硕士研究生。",
            {"college": "A学院", "education_level": "doctor"},
        )
        doctor_only = assess_relevance(
            "A学院博士研究生",
            "面向A学院博士研究生。",
            {"college": "A学院", "education_level": "master"},
        )
        general_graduate = assess_relevance(
            "A学院研究生",
            "面向A学院研究生。",
            {"college": "A学院", "education_level": "doctor"},
        )
        self.assertEqual("不适用", master_only["relevance"])
        self.assertEqual("不适用", doctor_only["relevance"])
        self.assertEqual("明确相关", general_graduate["relevance"])

    def test_u1_relevance_fixture(self) -> None:
        payload = json.loads(
            (FIXTURES / "u1_relevance_cases.json").read_text(encoding="utf-8")
        )
        for case in payload["cases"]:
            with self.subTest(name=case["name"]):
                self.assertEqual(
                    case["expected"],
                    assess_relevance(
                        case["audience"], case["basis"], case["profile"]
                    ),
                )

    def test_d2_d3_u1_relevance_matrix(self) -> None:
        payload = json.loads(
            (FIXTURES / "u1_d2_d3_cases.json").read_text(encoding="utf-8")
        )
        for case in payload["cases"]:
            with self.subTest(name=case["name"]):
                self.assertEqual(
                    case["expected"],
                    assess_relevance(
                        case["audience"], case["basis"], payload["profile"]
                    ),
                )

        missing_other_constraints = assess_relevance(
            "大学城校区部分学院2023级本科生",
            "面向大学城校区部分学院2023级本科生。",
            {"college": "A学院"},
        )
        self.assertEqual("可能相关", missing_other_constraints["relevance"])
        self.assertEqual(
            "请确认你的校区、年级、培养层次，并确认A学院是否在通知所称部分学院名单中。",
            missing_other_constraints["missing_profile_question"],
        )

    def test_real_source_metadata_is_validated(self) -> None:
        source = {
            "id": "real-notice-001",
            "type": "notice",
            "title": "真实通知",
            "mode": "real",
            "text": "面向大学城校区全体本科生。",
            "publisher": "华南理工大学",
            "published_on": "2026-11-08",
            "url": "https://www.scut.edu.cn/example.htm",
            "ingested_at": "2026-11-09T00:30:00+08:00",
        }
        self.assertEqual(
            "明确相关",
            extract_notice(
                source,
                {"campus": "大学城校区", "education_level": "undergraduate"},
            )["relevance"],
        )

        unknown_date_source = dict(source)
        unknown_date_source["published_on"] = None
        extract_notice(unknown_date_source)

        invalid_values = {
            "publisher": "",
            "published_on": "2026-02-30",
            "url": "www.scut.edu.cn/example.htm",
            "ingested_at": "not-a-time",
        }
        for field, invalid_value in invalid_values.items():
            with self.subTest(field=field):
                invalid_source = dict(source)
                invalid_source[field] = invalid_value
                with self.assertRaises(ValueError):
                    extract_notice(invalid_source)

        timezone_missing = dict(source)
        timezone_missing["ingested_at"] = "2026-11-09T00:30:00"
        with self.assertRaisesRegex(ValueError, "must include a timezone"):
            extract_notice(timezone_missing)

        published_on_missing = dict(source)
        published_on_missing.pop("published_on")
        with self.assertRaisesRegex(ValueError, "published_on"):
            extract_notice(published_on_missing)

    def test_candidate_extraction_is_strictly_validated(self) -> None:
        payload = json.loads(
            (FIXTURES / "real_job_subsidy.json").read_text(encoding="utf-8")
        )
        valid_candidate = payload["candidate_extraction"]
        result = _extract(payload)
        self.assertEqual(valid_candidate, result["extraction"])

        invalid_candidates = []

        missing = dict(valid_candidate)
        missing.pop("action")
        invalid_candidates.append(("missing", missing))

        extra = dict(valid_candidate)
        extra["unsupported"] = None
        invalid_candidates.append(("extra", extra))

        invalid_values = {
            "action": 1,
            "materials": "申请表",
            "date": "2026-1-10",
            "time": "8:00",
            "relevance": "相关",
            "basis": "不在原文中的依据",
            "source_excerpt": "不在原文中的摘录",
            "entry_url": "/relative/path",
        }
        for field, value in invalid_values.items():
            invalid = dict(valid_candidate)
            invalid[field] = value
            invalid_candidates.append((field, invalid))

        for name, candidate in invalid_candidates:
            with self.subTest(name=name):
                invalid_payload = dict(payload)
                invalid_payload["candidate_extraction"] = candidate
                with self.assertRaises(ValueError):
                    _extract(invalid_payload)

    def test_candidate_rejects_unsupported_but_well_formed_values(self) -> None:
        payload = json.loads(
            (FIXTURES / "real_job_subsidy.json").read_text(encoding="utf-8")
        )
        candidate = payload["candidate_extraction"]
        unsupported_values = {
            "action": "提交优秀学生奖学金申请",
            "date": "2026-12-31",
            "time": "23:59",
            "materials": ["校长签署推荐信"],
            "entry": "教务处线下窗口",
            "entry_url": "https://example.com/apply",
            "location": "五山校区A101",
        }

        for field, value in unsupported_values.items():
            with self.subTest(field=field):
                invalid_payload = dict(payload)
                invalid_candidate = dict(candidate)
                invalid_candidate[field] = value
                invalid_payload["candidate_extraction"] = invalid_candidate
                with self.assertRaisesRegex(
                    ValueError,
                    "exact source.text excerpt|not supported|complete source.text URL",
                ):
                    _extract(invalid_payload)

    def test_candidate_url_prefix_is_rejected(self) -> None:
        payload = json.loads(
            (FIXTURES / "real_job_subsidy.json").read_text(encoding="utf-8")
        )
        candidate = dict(payload["candidate_extraction"])
        candidate["entry_url"] = "https://www.gdzwfw.gov.cn"
        payload["candidate_extraction"] = candidate
        with self.assertRaisesRegex(ValueError, "complete source.text URL"):
            _extract(payload)

    def test_event_date_must_match_the_same_source_excerpt(self) -> None:
        payload = json.loads(
            (FIXTURES / "real_job_subsidy.json").read_text(encoding="utf-8")
        )
        source = dict(payload["source"])
        source["text"] += "\n学生首次提交补贴申请不得晚于2027年4月30日。"
        payload["source"] = source
        candidate = dict(payload["candidate_extraction"])
        candidate["date"] = "2027-04-30"
        payload["candidate_extraction"] = candidate
        with self.assertRaisesRegex(ValueError, "supported by source_excerpt"):
            _extract(payload)

    def test_alternative_materials_must_remain_one_phrase(self) -> None:
        payload = json.loads((FIXTURES / "handoff_c.json").read_text(encoding="utf-8"))
        source = dict(payload["input"])
        source["text"] = (
            "面向大学城校区全体本科生，不限专业。"
            "请于2026年11月25日前提交身份证或护照。"
        )
        payload["input"] = source
        material_only = extract_notice(
            dict(source, text="提交身份证或护照。"), payload["profile"]
        )
        self.assertIsNone(material_only["action"])
        self.assertEqual(["身份证或护照"], material_only["materials"])
        self.assertIsNone(material_only["source_excerpt"])
        identity_proof = extract_notice(
            dict(source, text="提交身份证明。"), payload["profile"]
        )
        self.assertEqual(["身份证明"], identity_proof["materials"])
        alternative_list = extract_notice(
            dict(source, text="提交身份证、申请表任选其一。"), payload["profile"]
        )
        self.assertEqual(["身份证、申请表任选其一"], alternative_list["materials"])
        for text, expected in (
            ("提交身份证和申请表二选一。", ["身份证和申请表二选一"]),
            ("提交身份证和申请表。", ["身份证和申请表"]),
        ):
            with self.subTest(text=text):
                self.assertEqual(
                    expected,
                    extract_notice(dict(source, text=text), payload["profile"])["materials"],
                )
        negated_identity = extract_notice(
            dict(source, text="无需提交身份证，只需提交申请表。"), payload["profile"]
        )
        self.assertEqual(["只需提交申请表"], negated_identity["materials"])
        candidate = dict(payload["expected_extraction"])
        candidate.update(
            {
                "action": "提交身份证或护照",
                "date": "2026-11-25",
                "time": None,
                "materials": ["身份证", "护照"],
                "entry": None,
                "entry_url": None,
                "source_excerpt": "请于2026年11月25日前提交身份证或护照",
            }
        )
        payload["candidate_extraction"] = candidate
        with self.assertRaisesRegex(ValueError, "preserve an alternative"):
            _extract(payload)

    def test_explicitly_negated_action_is_rejected(self) -> None:
        payload = json.loads((FIXTURES / "handoff_c.json").read_text(encoding="utf-8"))
        source = dict(payload["input"])
        source["text"] = "面向大学城校区全体本科生，不限专业。无需提交申请表。"
        payload["input"] = source
        candidate = dict(payload["expected_extraction"])
        candidate.update(
            {
                "action": "提交申请表",
                "date": None,
                "time": None,
                "materials": [],
                "entry": None,
                "entry_url": None,
                "source_excerpt": "无需提交申请表",
            }
        )
        payload["candidate_extraction"] = candidate
        with self.assertRaisesRegex(ValueError, "explicitly negated"):
            _extract(payload)

    def test_candidate_time_uses_normalized_source_value(self) -> None:
        payload = json.loads((FIXTURES / "handoff_c.json").read_text(encoding="utf-8"))
        payload["input"] = dict(payload["input"])
        payload["input"]["text"] = payload["input"]["text"].replace(
            "17:00", "8：00"
        )
        candidate = dict(payload["expected_extraction"])
        candidate["time"] = "08:00"
        candidate["source_excerpt"] = "请于2026年11月25日8：00前提交报名表PDF"
        payload["candidate_extraction"] = candidate
        result = _extract(payload)
        self.assertEqual("08:00", result["bundle"]["events"][0]["start_time"])

    def test_candidate_relevance_rejects_explicit_profile_conflict(self) -> None:
        payload = json.loads((FIXTURES / "handoff_c.json").read_text(encoding="utf-8"))
        payload["candidate_extraction"] = payload["expected_extraction"]
        _extract(payload)

        conflicting_payload = dict(payload)
        conflicting_profile = dict(payload["profile"])
        conflicting_profile["campus"] = "五山校区"
        conflicting_payload["profile"] = conflicting_profile
        with self.assertRaisesRegex(ValueError, "conflicts with the profile"):
            _extract(conflicting_payload)

    def test_candidate_relevance_requires_missing_profile_confirmation(self) -> None:
        payload = json.loads((FIXTURES / "handoff_c.json").read_text(encoding="utf-8"))
        payload["candidate_extraction"] = payload["expected_extraction"]

        no_profile = dict(payload)
        no_profile.pop("profile")
        with self.assertRaisesRegex(ValueError, "conflicts with the profile"):
            _extract(no_profile)

        partial_profile = dict(payload)
        partial_profile["profile"] = {"education_level": "undergraduate"}
        with self.assertRaisesRegex(ValueError, "conflicts with the profile"):
            _extract(partial_profile)

    def test_candidate_audience_cannot_remove_source_constraints(self) -> None:
        payload = json.loads((FIXTURES / "handoff_c.json").read_text(encoding="utf-8"))
        for audience in (None, "大学城校区"):
            with self.subTest(audience=audience):
                invalid_payload = dict(payload)
                candidate = dict(payload["expected_extraction"])
                candidate["audience"] = audience
                invalid_payload["candidate_extraction"] = candidate
                with self.assertRaisesRegex(ValueError, "audience conflicts"):
                    _extract(invalid_payload)

    def test_heading_audience_cannot_be_removed_or_shortened(self) -> None:
        payload = json.loads(
            (FIXTURES / "real_job_subsidy.json").read_text(encoding="utf-8")
        )
        for audience, basis in (
            (None, None),
            ("2027年毕业学年的学生", "2027年毕业学年的学生"),
        ):
            with self.subTest(audience=audience):
                invalid_payload = dict(payload)
                candidate = dict(payload["candidate_extraction"])
                candidate.update(
                    {
                        "audience": audience,
                        "basis": basis,
                        "relevance": "明确相关",
                        "missing_profile_question": None,
                    }
                )
                invalid_payload["candidate_extraction"] = candidate
                with self.assertRaisesRegex(ValueError, "audience conflicts"):
                    _extract(invalid_payload)

    def test_heading_audience_requires_possible_relevance_and_question(self) -> None:
        payload = json.loads(
            (FIXTURES / "real_job_subsidy.json").read_text(encoding="utf-8")
        )
        candidate = dict(payload["candidate_extraction"])
        candidate["relevance"] = "明确相关"
        candidate["missing_profile_question"] = None
        payload["candidate_extraction"] = candidate
        with self.assertRaisesRegex(ValueError, "must be 可能相关"):
            _extract(payload)

    def test_conditional_account_materials_cannot_be_split(self) -> None:
        payload = json.loads(
            (FIXTURES / "real_job_subsidy.json").read_text(encoding="utf-8")
        )
        candidate = dict(payload["candidate_extraction"])
        candidate["materials"] = [
            "毕业生本人社保卡金融账户",
            "个人名下其他银行账户",
        ]
        payload["candidate_extraction"] = candidate
        with self.assertRaisesRegex(ValueError, "preserve an alternative"):
            _extract(payload)

    def test_real_candidate_builds_submission_with_exact_excerpt(self) -> None:
        payload = json.loads(
            (FIXTURES / "real_job_subsidy.json").read_text(encoding="utf-8")
        )
        result = _extract(payload)
        event = result["bundle"]["events"][0]
        candidate = payload["candidate_extraction"]

        self.assertEqual("submission", event["type"])
        self.assertEqual("2026-11-10", event["date"])
        self.assertIsNone(event["start_time"])
        self.assertEqual(candidate["source_excerpt"], event["source_excerpt"])
        self.assertNotEqual(payload["source"]["text"], event["source_excerpt"])

    def test_bundle_prefers_candidate_excerpt_and_location(self) -> None:
        payload = json.loads((FIXTURES / "handoff_c.json").read_text(encoding="utf-8"))
        candidate = dict(payload["expected_extraction"])
        candidate["location"] = "A101"
        extraction = candidate
        bundle = build_bundle(payload["input"], extraction, payload["today"])
        event = bundle["events"][0]
        self.assertEqual(candidate["source_excerpt"], event["source_excerpt"])
        self.assertEqual("A101", event["location"])

    def test_cli_extract_requires_explicit_today(self) -> None:
        payload = json.loads((FIXTURES / "handoff_c.json").read_text(encoding="utf-8"))
        payload.pop("today")
        with self.assertRaisesRegex(ValueError, "extract input requires today"):
            _extract(payload)

    def test_unknown_date_is_preserved_as_pending(self) -> None:
        source = {
            "id": "example-notice-unknown",
            "type": "notice",
            "title": "日期待公布的讲座",
            "mode": "example",
            "text": "面向大学城校区全体本科生。讲座日期待公布。",
            "publisher": "示例单位",
            "published_on": "2026-11-16",
            "file_name": "test_notice.py",
        }
        extraction = extract_notice(
            source,
            {"campus": "大学城校区", "education_level": "undergraduate"},
        )
        bundle = build_bundle(source, extraction, "2026-11-16")
        self.assertIsNone(bundle["events"][0]["date"])
        self.assertEqual(["date"], bundle["events"][0]["pending_fields"])


class NoticeChangeTests(unittest.TestCase):
    def test_d2_d3_complete_correction_changes_all_required_fields(self) -> None:
        payload = json.loads(
            (FIXTURES / "u4_d2_d3_full_correction.json").read_text(
                encoding="utf-8"
            )
        )
        result = compare_notice_versions(
            payload["original_source"],
            payload["correction"],
            payload["target_event_id"],
        )
        self.assertEqual(payload["expected_changes"], result["changes"])
        self.assertEqual(payload["correction"]["text"], result["source_excerpt"])

    def test_handoff_correction(self) -> None:
        payload = json.loads(
            (FIXTURES / "handoff_c_correction.json").read_text(encoding="utf-8")
        )
        update = compare_notice_versions(
            payload["original_source"],
            payload["correction"],
            payload["target_event_id"],
        )
        self.assertEqual("handoff-c-event-001", update["target_event_id"])
        self.assertEqual(
            {"date": {"before": "2026-11-25", "after": "2026-11-27"}},
            update["changes"],
        )

    def test_correction_uses_event_start_time_field(self) -> None:
        original = {
            "id": "n1",
            "type": "notice",
            "title": "报名通知",
            "mode": "example",
            "text": "请于2026年11月25日17:00前提交报名表。",
            "file_name": "original.json",
        }
        correction = {
            "id": "n2",
            "type": "notice",
            "title": "报名通知更正",
            "mode": "example",
            "text": "截止时间由2026年11月25日17:00更改为2026年11月25日18:30。",
            "file_name": "correction.json",
            "corrects": "n1",
        }
        result = compare_notice_versions(original, correction, "e1")
        self.assertEqual(
            {"start_time": {"before": "17:00", "after": "18:30"}},
            result["changes"],
        )

    def test_correction_detects_date_and_added_audience_together(self) -> None:
        original = {
            "id": "n1",
            "type": "notice",
            "title": "报名通知",
            "mode": "example",
            "text": "面向A学院本科生。请于2026年11月25日前提交申请。",
            "file_name": "original.json",
        }
        correction = {
            "id": "n2",
            "type": "notice",
            "title": "报名通知更正",
            "mode": "example",
            "text": "截止日期由2026年11月25日调整为2026年11月27日，新增B学院本科生为适用对象。",
            "file_name": "correction.json",
            "corrects": "n1",
        }
        changes = compare_notice_versions(original, correction, "e1")["changes"]
        self.assertEqual(
            {"before": "2026-11-25", "after": "2026-11-27"},
            changes["date"],
        )
        self.assertEqual(
            {"before": "A学院本科生", "after": "A学院本科生；B学院本科生"},
            changes["audience"],
        )

    def test_correction_detects_materials_and_location(self) -> None:
        original = {
            "id": "n1",
            "type": "notice",
            "title": "材料通知",
            "mode": "example",
            "text": "提交身份证、申请表，办理地点为A101。",
            "file_name": "original.json",
        }
        correction = {
            "id": "n2",
            "type": "notice",
            "title": "材料通知更正",
            "mode": "example",
            "text": "所需材料由身份证、申请表调整为身份证、证明材料；办理地点由A101改为B202。",
            "file_name": "correction.json",
            "corrects": "n1",
        }
        changes = compare_notice_versions(original, correction, "e1")["changes"]
        self.assertEqual(
            {"before": ["身份证", "申请表"], "after": ["身份证", "证明材料"]},
            changes["materials"],
        )
        self.assertEqual(
            {"before": "A101", "after": "B202"}, changes["location"]
        )

    def test_correction_detects_end_time(self) -> None:
        original = {
            "id": "n1",
            "type": "notice",
            "title": "活动通知",
            "mode": "example",
            "text": "活动结束时间为17:00。",
            "file_name": "original.json",
        }
        correction = {
            "id": "n2",
            "type": "notice",
            "title": "活动通知更正",
            "mode": "example",
            "text": "活动结束时间由17:00调整为18:30。",
            "file_name": "correction.json",
            "corrects": "n1",
        }
        changes = compare_notice_versions(original, correction, "e1")["changes"]
        self.assertEqual(
            {"before": "17:00", "after": "18:30"}, changes["end_time"]
        )

    def test_refresh_detects_added_and_corrected_sources(self) -> None:
        previous = [{"id": "n1", "text": "旧内容"}]
        current = [
            {"id": "n1", "text": "新内容"},
            {"id": "n2", "text": "新增内容"},
        ]
        result = refresh_sources(previous, current)
        self.assertEqual(["n2"], [source["id"] for source in result["added"]])
        self.assertEqual("n1", result["corrected"][0]["after"]["id"])

    def test_refresh_does_not_report_new_correction_as_added(self) -> None:
        previous = [{"id": "n1", "text": "旧内容"}]
        correction = {"id": "n2", "text": "更正内容", "corrects": "n1"}
        result = refresh_sources(previous, [correction])
        self.assertEqual([], result["added"])
        self.assertEqual(["n2"], [item["after"]["id"] for item in result["corrected"]])

    def test_u7_refresh_fixture(self) -> None:
        payload = json.loads(
            (FIXTURES / "refresh_sources.json").read_text(encoding="utf-8")
        )
        result = refresh_sources(
            payload["previous_sources"], payload["current_sources"]
        )
        self.assertEqual(payload["expected"], result)

    def test_b_relative_date_expectations(self) -> None:
        self.assertEqual(
            {"tomorrow": "2026-11-17", "this_friday": "2026-11-20"},
            verify_handoff_dates("2026-11-16"),
        )


if __name__ == "__main__":
    unittest.main()
