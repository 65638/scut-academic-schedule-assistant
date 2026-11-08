"""生成地点更正和重复导入的判定结果。"""

import re

from .message import _source


LOCATION_UPDATE = re.compile(
    r"(?P<title>[^，,。；;\n]+?)地点(?:改到|改为)(?P<location>[^，,。；;\n]+)"
)
CANDIDATE_FIELDS = ("id", "title", "date", "start_time", "location", "status")


def propose_location_update(message, current_bundle):
    """返回待保存的地点补丁，或返回候选事项供用户选择。"""
    mode = current_bundle["mode"]
    if message.get("mode", mode) != mode:
        raise ValueError("更正消息与当前事项的模式应一致")

    text = message["text"]
    match = LOCATION_UPDATE.fullmatch(text.strip().rstrip("。！!"))
    if match is None or not match["location"].strip():
        raise ValueError("请提供事项名称和新的地点")

    title = match["title"].strip()
    candidates = [
        event for event in current_bundle["events"]
        if event["type"] == "activity" and event["title"] == title
    ]
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
        location = match["location"].strip()
        if target.get("location") != location:
            result["changes"]["location"] = location
        return result

    result["candidates"] = [{key: event.get(key) for key in CANDIDATE_FIELDS} for event in candidates]
    result["pending_fields"] = ["target_event_id"]
    result["question"] = "请选择要更正的活动。" if candidates else "请确认要更正的活动名称。"
    return result


def plan_import(incoming_bundle, current_bundle):
    """返回可新增的 bundle 及被跳过的事项编号。"""
    if incoming_bundle["mode"] != current_bundle["mode"]:
        raise ValueError("导入消息与当前事项的模式应一致")

    seen_ids = {event["id"] for event in current_bundle["events"]}
    seen_excerpts = {
        (event["source_id"], event["source_excerpt"]) for event in current_bundle["events"]
    }
    additions, skipped = [], []
    for event in incoming_bundle["events"]:
        origin = (event["source_id"], event["source_excerpt"])
        if event["id"] in seen_ids or origin in seen_excerpts:
            skipped.append(event["id"])
            continue
        additions.append(event)
        seen_ids.add(event["id"])
    return {"bundle": dict(incoming_bundle, events=additions), "skipped_event_ids": skipped}
