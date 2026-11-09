"""按学期配置展开八列课表 CSV。"""

import argparse
import csv
from datetime import date, time, timedelta
import io
import json
from pathlib import Path
import re

from .message import CAMPUS, TIMEZONE, WEEKDAYS, _stable_id


COLUMNS = ("课程名", "星期", "开始节", "结束节", "起止周", "单双周", "校区教室", "备注")
WEEK_RANGE = re.compile(r"(?:第\s*)?([0-9]+)(?:\s*[-–—~～至]\s*([0-9]+))?\s*周?")
PARITY = {"每周": None, "单周": 1, "双周": 0}


def _rows(text):
    lines = io.StringIO(text, newline="").readlines()
    reader = csv.reader(lines, strict=True)
    header = next(reader, [])
    if len(header) != len(COLUMNS) or set(header) != set(COLUMNS):
        raise ValueError("课表 CSV 应包含约定的八列")
    start = reader.line_num
    for values in reader:
        excerpt = "".join(lines[start:reader.line_num]).rstrip("\r\n")
        row_number = start + 1
        start = reader.line_num
        if not values or not any(value.strip() for value in values):
            continue
        if len(values) != len(COLUMNS):
            raise ValueError(f"课表第 {row_number} 行应包含八列")
        yield row_number, dict(zip(header, (value.strip() for value in values))), excerpt


def _weekday(value):
    value = re.sub(r"^(?:星期|周)", "", value)
    if len(value) == 1 and value in "1234567":
        return int(value) - 1
    value = value.replace("天", "日")
    if len(value) == 1 and value in WEEKDAYS:
        return WEEKDAYS.index(value)
    raise ValueError("星期使用周一至周日或数字 1 至 7")


def _weeks(value, parity, teaching_weeks):
    match = WEEK_RANGE.fullmatch(value)
    if not match or parity not in PARITY:
        raise ValueError("起止周使用 12–13 周等范围，单双周填写每周、单周或双周")
    first = int(match[1])
    last = int(match[2] or match[1])
    if not 1 <= first <= last <= teaching_weeks:
        raise ValueError("起止周超出学期教学周范围")
    remainder = PARITY[parity]
    return (week for week in range(first, last + 1) if remainder is None or week % 2 == remainder)


def _period_bounds(first, last, periods):
    first, last = int(first), int(last)
    if not 1 <= first <= last or str(first) not in periods or str(last) not in periods:
        raise ValueError("开始节、结束节应按顺序填写配置中的节次")
    start = periods[str(first)][0]
    end = periods[str(last)][1]
    if (time.fromisoformat(start).strftime("%H:%M") != start
            or time.fromisoformat(end).strftime("%H:%M") != end or start >= end):
        raise ValueError("节次时刻应使用 HH:MM，结束须晚于开始")
    return first, last, start, end


def parse_timetable(csv_text, config, *, file_name=None):
    """返回普通 bundle。每次课程的编号以原定课次为准。"""
    mode = config["mode"]
    if mode not in ("example", "real") or config.get("timezone", TIMEZONE) != TIMEZONE:
        raise ValueError("请明确示例或真实模式，时区使用 Asia/Shanghai")
    term_start = date.fromisoformat(config["term_start"])
    if term_start.weekday() != 0:
        raise ValueError("学期起点应为第一教学周周一")
    text = csv_text.lstrip("\ufeff")
    source = {
        "id": _stable_id("timetable", mode, term_start.isoformat(), text),
        "type": "timetable",
        "title": "示例课表 CSV" if mode == "example" else "课表 CSV",
        "mode": mode,
        "text": text,
        "timetable": {
            "term_start": term_start.isoformat(),
            "references": config.get("references", []),
        },
    }
    if file_name:
        source["file_name"] = file_name

    events = {}
    for row_number, row, excerpt in _rows(text):
        try:
            title = row["课程名"]
            if not title:
                raise ValueError("请填写课程名")
            weekday = _weekday(row["星期"])
            first, last, start, end = _period_bounds(row["开始节"], row["结束节"], config["periods"])
            weeks = _weeks(row["起止周"], row["单双周"], config["teaching_weeks"])
        except ValueError as error:
            raise ValueError(f"课表第 {row_number} 行：{error}") from error
        for week in weeks:
            day = term_start + timedelta(weeks=week - 1, days=weekday)
            event_id = _stable_id("course", mode, term_start.isoformat(), title, week, weekday, first, last)
            event = {
                "id": event_id, "type": "course", "title": title,
                "date": day.isoformat(), "start_time": start, "end_time": end,
                "location": row["校区教室"] or None, "status": "not_started",
                "pending_fields": [], "source_id": source["id"], "source_excerpt": excerpt,
            }
            if event_id in events and events[event_id]["location"] != event["location"]:
                raise ValueError(f"课表第 {row_number} 行的同名课次有不同地点，请核对 CSV")
            events.setdefault(event_id, event)
    return {
        "mode": mode, "today": config.get("today"), "timezone": TIMEZONE,
        "campus": CAMPUS, "sources": [source], "events": list(events.values()),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", required=True, type=Path)
    parser.add_argument("--config", required=True, type=Path)
    args = parser.parse_args()
    try:
        text = args.csv.read_text(encoding="utf-8-sig")
        config = json.loads(args.config.read_text(encoding="utf-8-sig"))
        result = parse_timetable(text, config, file_name=args.csv.name)
    except (ValueError, KeyError, OSError, csv.Error) as error:
        parser.error(str(error))
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
