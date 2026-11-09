"""M2 + M0 integration. Plans notice writes without claiming cloud persistence."""
import argparse
from datetime import datetime
import json
from pathlib import Path

from m2.notice import (
    assess_relevance,
    build_bundle,
    compare_notice_versions,
    extract_notice,
    validate_candidate_extraction,
)
from runtime import current_bundle
from schedule import SHANGHAI, prepare_import, read_rows


EVENT_FIELDS = ("date", "start_time", "end_time", "location")
METADATA_FIELDS = ("audience", "materials")


def _result(**extra):
    value = {
        "records": [],
        "updates": [],
        "questions": [],
        "saved_to_cloud": False,
    }
    value.update(extra)
    return value


def _question(field, question):
    return {"field": field, "question": question}


def _flag(payload, field):
    value = payload.get(field, False)
    if not isinstance(value, bool):
        raise ValueError(f"{field} 必须是 JSON boolean")
    return value


def _validate_flags(payload):
    _flag(payload, "save_requested")
    _flag(payload, "applicability_confirmed")


def _source_with_history(row):
    return json.loads(row["source"])


def _chain_sources(source):
    values = [source]
    values.extend(entry["source"] for entry in source.get("event_history", []))
    return values


def _all_source_uses(content):
    uses = []
    for row in read_rows(content):
        for source in _chain_sources(_source_with_history(row)):
            uses.append((row, source))
    return uses


def _same_source(left, right):
    return (
        left.get("id") == right.get("id")
        and left.get("text") == right.get("text")
        and left.get("mode") == right.get("mode")
    )


def _gate(extraction, payload):
    relevance = extraction["relevance"]
    if relevance == "不适用":
        return [_question("relevance", "该通知与当前画像不适用，未写入个人日程。")]
    needs_confirmation = (
        relevance == "可能相关"
        or extraction.get("missing_profile_question") is not None
    )
    if needs_confirmation and not _flag(payload, "applicability_confirmed"):
        return [_question(
            "applicability_confirmed",
            extraction.get("missing_profile_question") or "请确认该通知是否适用于你。",
        )]
    if not _flag(payload, "save_requested"):
        return [_question("save_requested", "已整理通知事项，是否保存到个人日程？")]
    return []


def _validated_extraction(payload, source):
    profile = payload.get("profile")
    candidate = payload.get("candidate_extraction")
    if candidate is None:
        return extract_notice(source, profile)
    return validate_candidate_extraction(source, candidate, profile)


def _notice_source(source, extraction, payload):
    enriched = dict(source)
    enriched["m2"] = {
        "extraction": dict(extraction),
        "profile": dict(payload.get("profile") or {}),
        "applicability_confirmed": _flag(payload, "applicability_confirmed"),
        "latest_source_id": source["id"],
        "source_chain": [source["id"]],
    }
    enriched["questions"] = []
    return enriched


def _check_notice_collision(content, source, event, mode):
    matching_rows = [row for row in read_rows(content) if row["id"] == event["id"]]
    for row, known_source in _all_source_uses(content):
        if known_source.get("id") != source["id"]:
            continue
        if not _same_source(known_source, source):
            raise ValueError("来源编号已存在但原文或模式不同，不能静默忽略或覆盖")
        if row["id"] != event["id"]:
            raise ValueError("来源编号已关联其他事项，不能重复建立新事项")
    if len(matching_rows) > 1:
        raise ValueError("同一事项编号对应多条记录，不能继续导入")
    if not matching_rows:
        return False
    row = matching_rows[0]
    known = _source_with_history(row)
    if row["mode"] != mode or row["source_id"] != source["id"]:
        raise ValueError("事项编号已被其他模式或来源占用")
    if not _same_source(known, source) or row["source_excerpt"] != event["source_excerpt"]:
        raise ValueError("事项编号已存在但来源内容不同，不能静默忽略或覆盖")
    return True


def prepare_notice(content, payload, now):
    _validate_flags(payload)
    source = payload.get("source", payload.get("input"))
    if source is None:
        raise ValueError("notice 输入需要 source 或 input")
    today = payload.get("today")
    if today is None:
        raise ValueError("notice 输入需要明确 today")
    if payload.get("mode", source["mode"]) != source["mode"]:
        raise ValueError("notice 输入模式与来源模式不一致")

    extraction = _validated_extraction(payload, source)
    bundle = build_bundle(
        source,
        extraction,
        today,
        payload.get("timezone", "Asia/Shanghai"),
        payload.get("campus", "大学城校区"),
    )
    bundle["sources"] = [_notice_source(source, extraction, payload)]
    result = _result(extraction=extraction, bundle=bundle, skipped_event_ids=[])
    questions = _gate(extraction, payload)
    if questions:
        result["questions"] = questions
        return result

    event = bundle["events"][0]
    if _check_notice_collision(content, source, event, bundle["mode"]):
        result["skipped_event_ids"] = [event["id"]]
        return result
    additions = prepare_import(content, bundle, now)
    result["records"] = additions["records"]
    result["skipped_event_ids"] = additions["skipped"]
    return result


def _find_target(content, target_event_id, mode):
    matches = [row for row in read_rows(content) if row["id"] == target_event_id]
    if len(matches) > 1:
        raise ValueError("同一目标事项存在多条记录，不能应用更正")
    if not matches:
        return None
    if matches[0]["mode"] != mode:
        return None
    return matches[0]


def _find_chain_source(source, source_id):
    matches = [item for item in _chain_sources(source) if item.get("id") == source_id]
    if len(matches) > 1:
        raise ValueError("目标事项的来源链包含重复编号")
    return matches[0] if matches else None


def _replayed_correction(content, target_id, correction):
    uses = [
        (row, source) for row, source in _all_source_uses(content)
        if source.get("id") == correction["id"]
    ]
    if not uses:
        return False
    if any(row["id"] != target_id for row, _ in uses):
        raise ValueError("更正来源编号已用于其他事项")
    if any(not _same_source(source, correction) for _, source in uses):
        raise ValueError("更正来源编号已存在但原文或模式不同")
    return True


def _current_value(row, source, field):
    if field in EVENT_FIELDS:
        return row[field] or None
    extraction = source.get("m2", {}).get("extraction", {})
    return extraction.get(field)


def _correction_gate(source, changes, payload):
    if "audience" not in changes:
        return [], None
    after = changes["audience"]["after"]
    relevance = assess_relevance(after, payload["correction"]["text"], payload.get("profile"))
    if relevance["relevance"] == "不适用":
        return [_question("relevance", "更正后的适用对象与当前画像不符，未更新事项。")], relevance
    if not _flag(payload, "applicability_confirmed"):
        return [_question(
            "applicability_confirmed",
            relevance.get("missing_profile_question") or "适用对象已变化，请确认更正后的范围包含你。",
        )], relevance
    return [], relevance


def _corrected_values(event_id, source, correction, changes, payload, now, audience_relevance):
    values = {}
    extraction = dict(source.get("m2", {}).get("extraction", {}))
    for field, change in changes.items():
        if field in EVENT_FIELDS:
            values[field] = change["after"]
            if field == "date":
                extraction["date"] = change["after"]
            elif field == "start_time":
                extraction["time"] = change["after"]
            elif field == "location":
                extraction["location"] = change["after"]
        elif field in METADATA_FIELDS:
            extraction[field] = change["after"]
    if audience_relevance is not None:
        extraction["relevance"] = (
            "明确相关"
            if audience_relevance["relevance"] == "可能相关"
            and _flag(payload, "applicability_confirmed")
            else audience_relevance["relevance"]
        )
        extraction["basis"] = audience_relevance["basis"]
        extraction["missing_profile_question"] = None

    correction_source = dict(correction)
    correction_source.setdefault("ingested_at", now)
    history_entry = {
        "kind": "notice_correction",
        "event_id": event_id,
        "changes": changes,
        "source": correction_source,
        "applied_at": now,
    }
    source.setdefault("event_history", []).append(history_entry)
    m2 = source.setdefault("m2", {})
    m2["extraction"] = extraction
    m2["profile"] = dict(payload.get("profile") or m2.get("profile") or {})
    if audience_relevance is not None:
        m2["applicability_confirmed"] = _flag(
            payload, "applicability_confirmed"
        )
    else:
        m2.setdefault("applicability_confirmed", False)
    m2["latest_source_id"] = correction["id"]
    chain = list(m2.get("source_chain") or [source["id"]])
    if correction["id"] not in chain:
        chain.append(correction["id"])
    m2["source_chain"] = chain
    source["questions"] = []
    return values


def _correction_update(row, source, correction, changes, payload, now, audience_relevance):
    values = _corrected_values(row["id"], source, correction, changes, payload, now, audience_relevance)
    values["source"] = json.dumps(source, ensure_ascii=False)
    return {
        "event_id": row["id"],
        "properties": {key: {"text": value or ""} for key, value in values.items()},
    }


def _check_before_values(current, source, changes):
    for field, change in changes.items():
        if field not in EVENT_FIELDS + METADATA_FIELDS:
            raise ValueError(f"暂不支持原位应用更正字段 {field}")
        if _current_value(current, source, field) != change["before"]:
            raise ValueError(f"更正字段 {field} 的 before 与当前事项不一致")


def _prepare_newly_applicable(content, payload, original, correction, now):
    today = payload.get("today")
    if not today or original["id"] == correction["id"]:
        raise ValueError("新增更正事项需要 today 和独立的更正来源编号")
    extraction = _validated_extraction(payload, original)
    bundle = build_bundle(
        original, extraction, today,
        payload.get("timezone", "Asia/Shanghai"), payload.get("campus", "大学城校区"),
    )
    event = bundle["events"][0]
    event_id = event["id"]
    result = _result(skipped_event_ids=[])
    if _replayed_correction(content, event_id, correction):
        result["skipped_event_ids"] = [event_id]
        return result
    if _check_notice_collision(content, original, event, bundle["mode"]):
        result["questions"] = [_question("target_event_id", "该通知已有事项，请选定原事项后更新。")]
        return result

    proposal = compare_notice_versions(original, correction, event_id)
    changes = proposal["changes"]
    if extraction["relevance"] != "不适用" or "audience" not in changes:
        result["questions"] = [_question("relevance", "请核对画像是否由原通知不适用变为更正后适用。")]
        return result

    source = _notice_source(original, extraction, payload)
    _check_before_values(event, source, changes)
    result["proposal"] = proposal
    questions, relevance = _correction_gate(source, changes, payload)
    if questions:
        result["questions"] = questions
        return result
    if not _flag(payload, "save_requested"):
        result["questions"] = [_question("save_requested", "更正后的通知适用于你，是否新增到个人日程？")]
        return result

    event.update(_corrected_values(event_id, source, correction, changes, payload, now, relevance))
    if event["date"]:
        event["pending_fields"] = [field for field in event["pending_fields"] if field != "date"]
    bundle["sources"] = [source]
    additions = prepare_import(content, bundle, now)
    result.update(bundle=bundle, records=additions["records"], skipped_event_ids=additions["skipped"])
    return result


def prepare_correction(content, payload, now):
    _validate_flags(payload)
    correction = payload["correction"]
    original = payload["original_source"]
    target_id = payload.get("target_event_id")
    mode = payload.get("mode", correction.get("mode"))
    if mode not in ("example", "real"):
        raise ValueError("correction 需要明确 example 或 real 模式")
    if correction.get("mode") != mode or original.get("mode") != mode:
        raise ValueError("更正、原来源和目标事项必须使用同一模式")
    if _flag(payload, "newly_applicable"):
        if target_id:
            raise ValueError("已有目标事项时请走原位更正")
        return _prepare_newly_applicable(content, payload, original, correction, now)

    result = _result(skipped_event_ids=[])
    if not target_id:
        result["questions"] = [_question("target_event_id", "请选择要更正的通知事项。")]
        return result
    target = _find_target(content, target_id, mode)
    if target is None:
        result["questions"] = [_question("target_event_id", "没有找到该模式下的目标事项。")]
        return result
    stored = _source_with_history(target)

    if _replayed_correction(content, target_id, correction):
        result["skipped_event_ids"] = [target_id]
        return result

    latest_id = stored.get("m2", {}).get("latest_source_id", stored.get("id"))
    latest_source = _find_chain_source(stored, latest_id)
    if latest_source is None:
        raise ValueError("目标事项的最新来源无法从自身来源链恢复")
    if correction.get("corrects") != latest_id:
        raise ValueError("更正必须指向目标事项已应用的最新来源")
    if not _same_source(original, latest_source):
        raise ValueError("original_source 与目标事项的最新来源不一致")

    try:
        proposal = compare_notice_versions(original, correction, target_id)
    except ValueError as error:
        if str(error) != "no supported notice changes were found":
            raise
        result["questions"] = [_question(
            "source_excerpt", "没有识别出可安全应用的更正，请明确变化字段和前后值。"
        )]
        return result
    changes = proposal["changes"]
    _check_before_values(target, stored, changes)

    result["proposal"] = proposal
    questions, audience_relevance = _correction_gate(stored, changes, payload)
    if questions:
        result["questions"] = questions
        return result
    if not _flag(payload, "save_requested"):
        result["questions"] = [_question("save_requested", "已核对通知更正，是否更新个人日程？")]
        return result
    result["updates"] = [
        _correction_update(
            target, stored, correction, changes, payload, now, audience_relevance
        )
    ]
    return result


def notice_snapshot(content, mode, today):
    bundle = current_bundle(content, mode, today)
    sources = {source["id"]: source for source in bundle["sources"]}
    for event in bundle["events"]:
        source = sources.get(event["source_id"])
        if source and source.get("m2"):
            event["m2"] = source["m2"]
    return bundle


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["notice", "correction", "snapshot"])
    parser.add_argument("--existing", type=Path)
    parser.add_argument("--input", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--mode", choices=["example", "real"], default="real")
    parser.add_argument("--today")
    args = parser.parse_args()
    try:
        content = args.existing.read_text(encoding="utf-8-sig") if args.existing else ""
        if args.command == "snapshot":
            if args.mode == "example" and not args.today:
                parser.error("示例模式 snapshot 需要 --today")
            today = args.today or datetime.now(SHANGHAI).date().isoformat()
            result = notice_snapshot(content, args.mode, today)
        else:
            if not args.input:
                parser.error("notice/correction 需要 --input")
            payload = json.loads(args.input.read_text(encoding="utf-8-sig"))
            now = datetime.now(SHANGHAI).isoformat(timespec="seconds")
            action = prepare_notice if args.command == "notice" else prepare_correction
            result = action(content, payload, now)
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(
            json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except (ValueError, KeyError, OSError) as error:
        parser.error(str(error))
    print(json.dumps({
        "output": str(args.out),
        "records": len(result.get("records", [])),
        "updates": len(result.get("updates", [])),
        "questions": result.get("questions", []),
        "saved_to_cloud": False,
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
