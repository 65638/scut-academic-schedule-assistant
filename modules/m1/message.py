"""将首批校园消息转换为共享事项 JSON。"""

import argparse
from datetime import date, time, timedelta
from hashlib import sha256
import json
from pathlib import Path
import re
import sys


TIMEZONE = "Asia/Shanghai"
CAMPUS = "大学城校区"
RELATIVE_DAYS = {"今天": 0, "明天": 1, "后天": 2}
WEEKDAYS = "一二三四五六日"
DATE_AND_TIME = re.compile(
    r"(?P<day>[0-9]{4}-[0-9]{2}-[0-9]{2}|今天|明天|后天|本周[一二三四五六日天])"
    r"\s*(?:(?P<hour>[0-9]{1,2}):(?P<minute>[0-9]{2})\s*)?(?P<action>.+)"
)
ACTIVITY = re.compile(r"在(?P<location>[A-Za-z][0-9]+)开(?P<title>.+)")
SUBMISSION = re.compile(r"前(?:提交|交)(?P<title>.+)")


def _stable_id(prefix, *parts):
    data = json.dumps(parts, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return f"m1-{prefix}-{sha256(data).hexdigest()[:24]}"


def _source(message, mode):
    text = message["text"]
    sent_on = message.get("sent_on")
    default_title = "示例校园消息" if mode == "example" else "校园消息"
    return {
        "id": message.get("source_id") or _stable_id("message", mode, sent_on, text),
        "type": "message",
        "title": message.get("title") or default_title,
        "mode": mode,
        "text": text,
        "sent_on": sent_on,
    }


def _resolve_date(expression, sent_on):
    if expression[0].isdigit():
        return date.fromisoformat(expression).isoformat()
    if sent_on is None:
        return None
    if expression in RELATIVE_DAYS:
        return (sent_on + timedelta(days=RELATIVE_DAYS[expression])).isoformat()
    weekday = WEEKDAYS.index(expression[-1].replace("天", "日"))
    return (sent_on + timedelta(days=weekday - sent_on.weekday())).isoformat()


def _parse_event(excerpt, source, sent_on, position):
    match = DATE_AND_TIME.fullmatch(excerpt)
    if match is None:
        raise ValueError(f"暂不支持该消息片段「{excerpt}」")

    action = match["action"].strip()
    activity = ACTIVITY.fullmatch(action)
    submission = SUBMISSION.fullmatch(action)
    if activity:
        event_type = "activity"
        title = activity["title"]
        location = activity["location"]
    elif submission:
        event_type = "submission"
        title = "提交" + submission["title"]
        location = None
    else:
        raise ValueError(f"暂不支持该事项表达「{action}」")

    day = _resolve_date(match["day"], sent_on)
    start_time = None
    if match["hour"] is not None:
        start_time = time(int(match["hour"]), int(match["minute"])).strftime("%H:%M")
    return {
        "id": _stable_id("event", source["mode"], source["id"], position, excerpt),
        "type": event_type,
        "title": title,
        "date": day,
        "start_time": start_time,
        "end_time": None,
        "location": location,
        "status": "not_started",
        "pending_fields": ["date"] if day is None else [],
        "source_id": source["id"],
        "source_excerpt": excerpt,
    }


def parse_message(message):
    """接收共享样例中的 B.input 格式，返回可直接交换的 bundle。"""
    mode = message.get("mode", "real")
    if mode not in ("example", "real") or message.get("timezone", TIMEZONE) != TIMEZONE:
        raise ValueError("模式应为 example 或 real，时区应为 Asia/Shanghai")

    source = _source(message, mode)
    sent_on = date.fromisoformat(source["sent_on"]) if source["sent_on"] is not None else None
    excerpts = [part.strip() for part in re.split(r"[，,。；;\n]+", source["text"]) if part.strip()]
    if not excerpts:
        raise ValueError("请输入原消息")

    events = [
        _parse_event(excerpt, source, sent_on, position)
        for position, excerpt in enumerate(excerpts)
    ]
    bundle = {
        "mode": mode,
        "today": message.get("today", source["sent_on"]),
        "timezone": TIMEZONE,
        "campus": CAMPUS,
        "sources": [source],
        "events": events,
    }
    if any(event["date"] is None for event in events):
        bundle["questions"] = [{"field": "sent_on", "question": "请提供原消息的发送日期。"}]
    return bundle


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", help="消息 JSON 文件路径，或用 - 从标准输入读取")
    args = parser.parse_args()
    try:
        if args.input == "-":
            content = sys.stdin.read()
        else:
            content = Path(args.input).read_text(encoding="utf-8-sig")
        result = parse_message(json.loads(content))
    except (ValueError, KeyError, OSError) as error:
        parser.error(str(error))
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
