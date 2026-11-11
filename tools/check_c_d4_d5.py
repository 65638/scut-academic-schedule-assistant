"""Reproduce the ten sourced notice checks without network or cloud writes."""
import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from modules.m2.cli import _compare, _extract
from modules.m2.notice import assess_relevance


FIXTURES = ROOT / "modules/m2/fixtures"
PACKAGE = "platform/scut-schedule/skills/scut-schedule/"
BASELINE = "eaaee4628bfd88e6c2c7264dbc495dacd85724cc"


def load(name):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def digest_text(path):
    # Git may check text out as CRLF; version the UTF-8 text with LF newlines.
    return hashlib.sha256((ROOT / path).read_text(encoding="utf-8").encode("utf-8")).hexdigest()


def version_entry(path):
    binary = path.endswith(".xlsx")
    return {"path": path, "sha256": hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
            if binary else digest_text(path), "hash_kind": "raw_bytes" if binary else "utf8_lf"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default="work/c-d4-d5-notices.json")
    args = parser.parse_args()
    handoff = load("handoff_c.json")
    full = load("u4_d2_d3_full_correction.json")
    real = load("real_job_subsidy.json")
    specs = [
        ("C01", "handoff_c.json", "input", "extract", handoff,
         handoff["expected_extraction"]),
        ("C02", "handoff_c_correction.json", "correction", "compare",
         load("handoff_c_correction.json"),
         load("handoff_c_correction_output.json")["update"]["changes"]),
        ("C03", "real_job_subsidy.json", "source", "extract", real,
         real["candidate_extraction"]),
        ("C04", "u4_d2_d3_full_correction.json", "original_source", "extract",
         {"source": full["original_source"], "profile": full["existing_profile"],
          "today": full["today"]},
         {"audience": "大学城校区A学院2023级本科生", "date": "2026-11-25",
          "time": "17:00", "materials": ["申请表"], "location": "A101",
          "relevance": "明确相关"}),
        ("C05", "u4_d2_d3_full_correction.json", "correction", "extract",
         {"source": full["correction"], "profile": full["existing_profile"],
          "today": full["today"],
          "candidate_extraction": full["corrected_candidate_extraction"]},
         full["corrected_candidate_extraction"]),
        ("C06", "u4_d2_d3_full_correction.json", "second_correction", "compare",
         {"original_source": full["correction"], "correction": full["second_correction"],
          "target_event_id": full["target_event_id"]}, full["expected_second_changes"]),
        ("C07", "u4_material_location_correction.json", "original_source", "extract",
         {"source": load("u4_material_location_correction.json")["original_source"],
          "today": "2026-11-16"},
         {"date": None, "time": None, "materials": ["身份证", "申请表"],
          "location": "A101", "audience": None, "relevance": "可能相关",
          "action": None, "source_excerpt": None}),
        ("C08", "u4_material_location_correction.json", "correction", "compare",
         load("u4_material_location_correction.json"),
         load("u4_material_location_correction_output.json")["update"]["changes"]),
        ("C09", "u4_end_time_correction.json", "original_source", "extract",
         {"source": load("u4_end_time_correction.json")["original_source"],
          "today": "2026-11-16"},
         {"date": None, "time": None, "materials": [], "audience": None,
          "relevance": "可能相关"}),
        ("C10", "u4_end_time_correction.json", "correction", "compare",
         load("u4_end_time_correction.json"),
         load("u4_end_time_correction_output.json")["update"]["changes"]),
    ]
    results = []
    source_ids = {load(name)[key]["id"] for _, name, key, *_ in specs}
    for number, name, key, command, payload, expected in specs:
        source = load(name)[key]
        output = _extract(payload) if command == "extract" else _compare(payload)
        actual = output["extraction"] if command == "extract" else output["update"]["changes"]
        fields = {field: {"expected": value, "actual": actual.get(field),
                          "passed": actual.get(field) == value}
                  for field, value in expected.items()}
        preserved = (output["bundle"]["sources"] == [source] if command == "extract"
                     else output["source"] == source)
        chain_ok = not source.get("corrects") or source["corrects"] in source_ids
        metadata = {field: source.get(field) for field in (
            "id", "mode", "publisher", "url", "file_name", "published_on", "ingested_at",
            "text_scope", "corrects")}
        missing = [field for field in ("publisher", "published_on", "ingested_at", "url")
                   if source.get(field) is None]
        results.append({
            "case": number, "fixture": "modules/m2/fixtures/" + name + "#" + key,
            "command": command,
            "candidate_origin": "既有人工核对候选；本次未调用模型"
                if "candidate_extraction" in payload else None,
            "source": source, "source_metadata": metadata,
            "missing_metadata": missing,
            "missing_metadata_note": "合成来源未提供的字段保持空；file_name是逻辑来源定位，fixture为实际路径"
                if source["mode"] == "example" else "官方原文节选，保留原收录时间",
            "source_preserved": preserved, "correction_parent_in_manifest": chain_ok,
            "field_checks": fields, "actual": actual,
            "passed": preserved and chain_ok and all(item["passed"] for item in fields.values()),
        })

    u1 = load("u1_d2_d3_cases.json")
    relevance = []
    for case in u1["cases"]:
        actual = assess_relevance(case["audience"], case["basis"], u1["profile"])
        relevance.append({"name": case["name"], "actual": actual,
                          "expected": case["expected"], "passed": actual == case["expected"]})

    pairs = [
        ("modules/m2/notice.py", PACKAGE + "scripts/m2/notice.py"),
        ("modules/m2/PROMPT.md", PACKAGE + "references/M2-PROMPT.md"),
    ]
    parity = [{"module": left, "packaged": right,
               "passed": digest_text(left) == digest_text(right)} for left, right in pairs]
    version_paths = [PACKAGE + "SKILL.md", "modules/m2/PROMPT.md", "modules/m2/cli.py",
                     PACKAGE + "scripts/notice_runtime.py",
                     "modules/m2/notice.py", "platform/scut-schedule/agents/scut-schedule.md",
                     PACKAGE + "scripts/knowledge_runtime.py", "knowledge/source_ledger.json",
                     "knowledge/official/scut_2027_graduate_job_subsidy.md",
                     "knowledge/official/scut_academic_calendar_2026_2027_1.md",
                     "knowledge/official/scut_academic_calendar_2026_2027_1.xlsx",
                     "knowledge/official/scut_university_town_schedule.md",
                     "tools/check_c_d4_d5.py"]
    version_paths += sorted({"modules/m2/fixtures/" + item[1] for item in specs})
    version_paths += ["modules/m2/fixtures/" + name for name in (
        "handoff_c_correction_output.json", "u4_material_location_correction_output.json",
        "u4_end_time_correction_output.json", "u1_d2_d3_cases.json")]
    report = {
        "checked_at": datetime.now(timezone(timedelta(hours=8))).isoformat(timespec="seconds"),
        "baseline_commit": BASELINE,
        "expert_version": "0.5.0",
        "coverage": "C D4/D5 工作树候选，本地10来源核对；不代表已发布0.5.0云端验收",
        "network_access": False, "cloud_writes": 0, "new_model_calls": 0,
        "selection": "未找到命名固定的10篇清单；从现有fixture选择10个不同来源，所有更正父来源均在清单内",
        "real_sources": 1, "synthetic_sources": 9,
        "unique_source_ids": len(source_ids),
        "source_ids_unique": len(source_ids) == len(specs),
        "notice_results": results,
        "u1_results": relevance, "module_package_parity": parity,
        "version_hash_algorithm": "SHA256; text=UTF-8/LF, xlsx=raw bytes; see hash_kind",
        "versions": [version_entry(path) for path in version_paths],
    }
    report["passed"] = report["source_ids_unique"] and all(item["passed"] for item in results + relevance + parity)
    destination = Path(args.out)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"notices_passed": sum(item["passed"] for item in results),
                      "notices_total": len(results), "u1_passed": sum(item["passed"] for item in relevance),
                      "parity_passed": sum(item["passed"] for item in parity), "passed": report["passed"]},
                     ensure_ascii=False))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
