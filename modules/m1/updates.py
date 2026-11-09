"""生成地点更正和重复导入的判定结果。"""

from datetime import date, time
import re

from .message import _source


LOCATION_UPDATE = re.compile(
    r"(?P<title>[^，,。；;\n]+?)地点(?:改到|改为)(?P<location>[^，,。；;\n]+)"
)
CANDIDATE_FIELDS = ("id", "title", "date", "start_time", "location", "status")
EDITABLE_FIELDS = {
    "postpone": {"date", "start_time"},
    "reschedule": {"date", "start_time", "end_time", "location"},
}
STATUS_CHANGES = {"cancel": "cancelled", "complete": "completed"}


def propose_location_update(message, current_bundle):
    """返回待保存的地点补丁，或返回候选事项供用户选择。"""
    text = message["text"]
    match = LOCATION_UPDATE.fullmatch(text.strip().rstrip("。！!"))
    if match is None or not match["location"].strip():
        raise ValueError("请提供事项名称和新的地点")

    title = match["title"].strip()
    candidates = [
        event for event in current_bundle["events"]
        if event["type"] == "activity" and event["title"] == title
    ]
    return _propose(message, current_bundle, candidates, {"location": match["location"].strip()}, "活动")


def _propose(message, current_bundle, candidates, changes, subject):
    mode = current_bundle["mode"]
    if message.get("mode", mode) != mode:
        raise ValueError("更正消息与当前事项的模式应一致")

    text = message["text"]
    if not text.strip():
        raise ValueError("请保留更正消息原文")
    source = _source(message, mode)
    result = {
        "target_event_id": None,
        "changes": {},
        "source_id": source["id"],
        "source_excerpt": text.strip(),
        "source": source,
    }
    target_id = message.get("target_event_id")
    selected = candidates
    if target_id:
        selected = [event for event in candidates if event["id"] == target_id]
    if len(selected) == 1:
        target = selected[0]
        result["target_event_id"] = target["id"]
        if any(entry["source"]["id"] == source["id"] for entry in target.get("history", [])):
            return result

        kind = message.get("kind")
        if kind == "postpone":
            old_date, old_time = target.get("date"), target.get("start_time")
            new_date, new_time = changes.get("date", old_date), changes.get("start_time", old_time)
            if old_date and new_date and (new_date < old_date or
                    (new_date == old_date and old_time and new_time and new_time < old_time)):
                raise ValueError("延期后的截止不能早于当前截止")
        elif kind == "reschedule":
            start = changes.get("start_time", target.get("start_time"))
            end = changes.get("end_time", target.get("end_time"))
            if start and end and start >= end:
                raise ValueError("调课后的结束时刻应晚于开始时刻")
        result["changes"] = {field: value for field, value in changes.items() if target.get(field) != value}
        return result

    result["candidates"] = [{key: event.get(key) for key in CANDIDATE_FIELDS} for event in candidates]
    result["pending_fields"] = ["target_event_id"]
    result["question"] = f"请选择要更正的{subject}。" if candidates else f"请确认要更正的{subject}名称。"
    return result


def propose_event_update(message, current_bundle):
    """根据原文与调用方核对过的结构化字段，提议延期、取消、完成或单次调课。"""
    kind = message["kind"]
    changes = message.get("changes", {})
    if kind in STATUS_CHANGES:
        if changes:
            raise ValueError("取消或完成只改变状态")
        changes = {"status": STATUS_CHANGES[kind]}
    elif kind not in EDITABLE_FIELDS or not changes or set(changes) - EDITABLE_FIELDS[kind]:
        raise ValueError("请明确操作和允许修改的字段")

    for field, value in changes.items():
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"请填写更正后的 {field}")
        if field == "date" and date.fromisoformat(value).isoformat() != value:
            raise ValueError("更正日期使用 YYYY-MM-DD")
        if field in ("start_time", "end_time") and time.fromisoformat(value).strftime("%H:%M") != value:
            raise ValueError("更正时刻使用 HH:MM")

    target_id = message.get("target_event_id")
    title = message.get("target_title")
    day = message.get("target_date")
    if not target_id and not title:
        raise ValueError("请提供目标事项编号或名称")
    event_type = {"postpone": "submission", "reschedule": "course"}.get(kind)
    candidates = [
        event for event in current_bundle["events"]
        if (not event_type or event["type"] == event_type)
        and (not title or event["title"] == title)
        and (not day or event.get("date") == day)
    ]
    return _propose(message, current_bundle, candidates, changes, "事项")


def plan_import(incoming_bundle, current_bundle):
    """返回可新增的 bundle 及被跳过的事项编号。"""
    if incoming_bundle["mode"] != current_bundle["mode"]:
        raise ValueError("导入消息与当前事项的模式应一致")

    seen_ids = {event["id"] for event in current_bundle["events"]}
    seen_excerpts = {
        (event["source_id"], event["source_excerpt"]) for event in current_bundle["events"]
        if event["type"] != "course"
    }
    additions, skipped = [], []
    for event in incoming_bundle["events"]:
        origin = (event["source_id"], event["source_excerpt"])
        # 同一 CSV 行会展开成多个独立课次，原文不能单独用于课次去重。
        if event["id"] in seen_ids or (event["type"] != "course" and origin in seen_excerpts):
            skipped.append(event["id"])
            continue
        additions.append(event)
        seen_ids.add(event["id"])
    return {"bundle": dict(incoming_bundle, events=additions), "skipped_event_ids": skipped}
