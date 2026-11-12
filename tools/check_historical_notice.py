"""Check the historical subsidy notice locally; never writes personal schedules."""
import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "platform/scut-schedule/skills/scut-schedule/scripts"
sys.path.insert(0, str(SCRIPTS))
from notice_runtime import prepare_notice
from presentation import build_report, render_report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--today", default="2026-11-12")
    parser.add_argument("--out-dir", type=Path, default=Path("work/c-final-history"))
    args = parser.parse_args()
    fixture = ROOT / "modules/m2/fixtures/real_job_subsidy.json"
    payload = json.loads(fixture.read_text(encoding="utf-8"))
    payload.update(today=args.today, save_requested=False, applicability_confirmed=False)
    now = datetime.now(timezone(timedelta(hours=8))).isoformat(timespec="seconds")
    plan = prepare_notice("", payload, now)
    report = build_report(plan["bundle"], "tonight")
    rendered = render_report(report)
    event, = plan["bundle"]["events"]
    extraction = plan["extraction"]
    source, = plan["bundle"]["sources"]
    checks = {
        "mode_is_real": report["mode"] == "real",
        "original_date_preserved": event["date"] == "2026-11-10",
        "individual_time_unknown": event["start_time"] is None and event["end_time"] is None,
        "original_source_preserved": all(source.get(key) == value for key, value in payload["source"].items()),
        "audience_still_needs_confirmation": extraction["relevance"] == "可能相关"
            and bool(extraction["missing_profile_question"]),
        "no_write_plan": plan["records"] == [] and plan["updates"] == []
            and plan["saved_to_cloud"] is False,
        "historical_node_is_overdue": any(item["id"] == event["id"] for item in report["overdue"]),
        "not_upcoming_due": all(item["id"] != event["id"] for item in report["due"]),
        "rendered_overdue": "逾期未完成（日期早于今天）" in rendered and "2026-11-10" in rendered,
    }
    policy_summary = ROOT / "knowledge/official/scut_2027_graduate_job_subsidy.md"
    version_paths = [fixture, policy_summary, SCRIPTS / "notice_runtime.py", SCRIPTS / "presentation.py",
                     SCRIPTS / "m2/notice.py", Path(__file__).resolve()]
    result = {
        "checked_at": now, "expert_version": "0.5.1", "baseline_commit": "2850893682147dd641055647f485f912fe185f9e",
        "scope": "本地只读解读场景，使用既有人工核对候选；没有实际云端记录或新模型调用",
        "today": args.today, "timezone": "Asia/Shanghai", "cloud_writes": 0,
        "meaning": "过期的是2026-11-10集中申请节点，不表示整个补贴项目关闭；补充申报政策见原通知",
        "policy_context_source": policy_summary.relative_to(ROOT).as_posix(),
        "render_scope": "以下M3报告只呈现未保存bundle的逾期分类；保存门槛问题另见questions，不是完整产品回复",
        "fixture": fixture.relative_to(ROOT).as_posix(),
        "input_overrides": {"today": args.today, "save_requested": False, "applicability_confirmed": False},
        "event": event, "extraction": extraction, "questions": plan["questions"],
        "source_metadata": {key: source.get(key) for key in
            ("id", "mode", "url", "published_on", "ingested_at", "text_scope")},
        "overdue_event_ids": [item["id"] for item in report["overdue"]],
        "due_event_ids": [item["id"] for item in report["due"]],
        "checks": checks, "passed": all(checks.values()),
        "versions": [{"path": path.relative_to(ROOT).as_posix(),
                      "sha256_utf8_lf": hashlib.sha256(path.read_text(encoding="utf-8").encode("utf-8")).hexdigest()}
                     for path in version_paths],
    }
    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "核对结果.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    context = (
        "# 历史集中申请节点的本地分类证据\n\n"
        f"查询日期：{args.today}（Asia/Shanghai）；专家脚本版本：0.5.1。\n\n"
        "以下是未保存 bundle 的 M3 分类输出，不是平台截图、个人表快照或完整产品回复。"
        "报告中的‘待确认’只统计 bundle 问题；通知保存流程另有以下适用性问题，仍需确认：\n\n"
        + "\n".join("- " + item["question"] for item in plan["questions"])
        + "\n\n2026-11-10 集中申请节点保留原日期并归入逾期；补充申请政策须另看官方原文，"
        "本次分类不判断整个补贴项目是否关闭。没有执行云端读写。\n\n---\n\n"
    )
    (args.out_dir / "本地真实模式呈现.md").write_text(context + rendered, encoding="utf-8")
    print(json.dumps({"passed": result["passed"], "checks": len(checks), "cloud_writes": 0}, ensure_ascii=False))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
