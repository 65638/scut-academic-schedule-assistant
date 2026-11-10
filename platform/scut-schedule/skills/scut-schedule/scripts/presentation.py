"""Stateless schedule presentation and suggestions; Python standard library only."""

import argparse
from copy import deepcopy
from datetime import date, datetime, time, timedelta, timezone
import json
from pathlib import Path


SHANGHAI = timezone(timedelta(hours=8))
FINISHED = {"completed", "cancelled"}
DEADLINES = {"submission"}
STATUS = {"not_started": "未开始", "in_progress": "进行中",
          "completed": "已完成", "cancelled": "已取消"}
FIELDS = {"date": "日期", "end_date": "结束日期", "start_time": "开始或截止时刻", "end_time": "结束时刻",
          "sent_on": "原消息发送日", "location": "地点", "source_excerpt": "原文片段",
          "materials": "材料", "audience": "适用对象", "status": "状态"}


def _day(value):
    parsed = date.fromisoformat(value)
    if parsed.isoformat() != value:
        raise ValueError("日期需使用 YYYY-MM-DD")
    return parsed


def _clock(value):
    parsed = time.fromisoformat(value)
    if parsed.tzinfo or parsed.second or parsed.microsecond or len(value) != 5:
        raise ValueError("时刻需使用 HH:MM，时区由 bundle 指定")
    return parsed


def _point(day, clock):
    return datetime.combine(_day(day), _clock(clock), SHANGHAI)


def _context(bundle):
    if bundle.get("mode") not in ("example", "real"):
        raise ValueError("需要明确 example 或 real 模式")
    if bundle.get("timezone") != "Asia/Shanghai":
        raise ValueError("当前仅支持 Asia/Shanghai")
    today = _day(bundle["today"])
    sources = {source["id"]: source for source in bundle["sources"]
               if source.get("mode", bundle["mode"]) == bundle["mode"]}
    events = []
    seen = set()
    all_sources = {source["id"]: source for source in bundle["sources"]}
    for event in bundle["events"]:
        source = all_sources.get(event.get("source_id"), {})
        if event.get("mode", source.get("mode", bundle["mode"])) != bundle["mode"]:
            continue
        if source.get("mode", bundle["mode"]) != bundle["mode"]:
            continue
        if event["id"] in seen:
            raise ValueError("事项编号重复，需由存储层核对后再呈现")
        seen.add(event["id"])
        if not isinstance(event.get("pending_fields", []), list):
            raise ValueError("pending_fields 应为数组；请先用 runtime.py snapshot 解码")
        for field in ("date", "end_date"):
            if event.get(field):
                _day(event[field])
        for field in ("start_time", "end_time"):
            if event.get(field):
                _clock(event[field])
        events.append(deepcopy(event))
    return today, sources, events


def _sort(event):
    return (event.get("date") or "9999", event.get("start_time") or "99:99", event["id"])


def _in_range(event, start, end):
    if not event.get("date"):
        return False
    first = _day(event["date"])
    last = _day(event.get("end_date") or event["date"])
    # An interval ending at midnight does not occupy the following day.
    if last > first and event.get("end_time") == "00:00":
        last -= timedelta(days=1)
    return first <= end and last >= start


def _pending(bundle, events, sources):
    pending = []
    for event in events:
        if event.get("status") in FINISHED:
            continue
        fields = list(event.get("pending_fields", []))
        if not event.get("date") and "date" not in fields:
            fields.append("date")
        if fields:
            pending.append(dict(event, pending_fields=fields))
    questions = []
    # Snapshot questions have already been resolved against current event dates.
    candidates = bundle.get("questions")
    if candidates is None:
        candidates = [dict(question, source_id=source["id"])
                      for source in sources.values() for question in source.get("questions", [])]
    for question in candidates:
        if question.get("source_id") and question["source_id"] not in sources:
            continue
        if not any(all(question.get(k) == entry.get(k) for k in question) for entry in questions):
            questions.append(deepcopy(question))
    return sorted(pending, key=_sort), questions


def _changes(bundle, events, start, end):
    collected = []
    event_ids = {event["id"] for event in events}
    candidates = list(bundle.get("changes", []))
    for event in events:
        candidates.extend(dict(change, event_id=event["id"]) for change in event.get("history", []))
    for change in candidates:
        if change.get("event_id") not in event_ids or not change.get("applied_at"):
            continue
        stamp = datetime.fromisoformat(change["applied_at"].replace("Z", "+00:00"))
        if stamp.tzinfo is None:
            raise ValueError("变更 applied_at 必须包含时区，不能猜测发生日期")
        if start <= stamp.astimezone(SHANGHAI).date() <= end and change not in collected:
            collected.append(deepcopy(change))
    return collected


def build_report(bundle, kind="week"):
    """Return a structured week/tonight report without modifying the input."""
    if kind not in ("week", "tonight", "week-brief"):
        raise ValueError("报告类型需为 week、tonight 或 week-brief")
    today, sources, events = _context(bundle)
    if kind != "tonight":
        start = today - timedelta(days=today.weekday())
        end = start + timedelta(days=6)
        schedule_start, schedule_end = start, end
    else:
        start, end = today, today + timedelta(days=2)
        schedule_start = schedule_end = today + timedelta(days=1)
    active = [event for event in events if event.get("status") not in FINISHED]
    scheduled = sorted([event for event in (events if kind == "week" else active) if event.get("status") != "cancelled"
                        and _in_range(event, schedule_start, schedule_end)], key=_sort)
    due = sorted([event for event in active if event["type"] in DEADLINES and event.get("date")
                  and start <= _day(event["date"]) <= end], key=_sort)
    overdue = sorted([event for event in active if event["type"] in DEADLINES and event.get("date")
                      and _day(event["date"]) < today], key=_sort)
    pending, questions = _pending(bundle, events, sources)
    changes = _changes(bundle, events, start if kind != "tonight" else today,
                       end if kind != "tonight" else today)
    conflicts = find_conflicts(bundle)
    relevant_ids = {event['id'] for event in active
                    if not event.get('date') or _in_range(event, schedule_start, schedule_end)}
    return {"kind": kind, "mode": bundle["mode"], "today": today.isoformat(),
            "timezone": "Asia/Shanghai", "start": start.isoformat(), "end": end.isoformat(),
            "scheduled": scheduled, "due": due, "overdue": overdue,
            "pending": pending, "questions": questions, "changes": changes,
            "conflicts": [c for c in conflicts['conflicts'] if schedule_start <= _day(c['date']) <= schedule_end],
            "conflict_warnings": [w for w in conflicts['warnings'] if w['event_id'] in relevant_ids],
            "event_titles": {event["id"]: event["title"] for event in events},
            "sources": list(sources.values())}


def _interval(event):
    if event["type"] not in ("activity", "course") or event.get("status") in FINISHED:
        return None
    if not all(event.get(field) for field in ("date", "start_time", "end_time")):
        return None
    start = _point(event["date"], event["start_time"])
    end = _point(event.get("end_date") or event["date"], event["end_time"])
    return (start, end) if end > start else None


def _slot(start, end):
    return {"date": start.date().isoformat(), "start_time": start.strftime("%H:%M"),
            "end_date": end.date().isoformat(), "end_time": end.strftime("%H:%M"),
            "minutes": int((end - start).total_seconds() // 60)}


def find_conflicts(bundle):
    """Half-open occupied intervals. Deadlines never occupy a time interval."""
    _, _, events = _context(bundle)
    intervals, warnings, conflicts = [], [], []
    for event in events:
        if event["type"] not in ("activity", "course") or event.get("status") in FINISHED:
            continue
        interval = _interval(event)
        if interval is None:
            warnings.append({"event_id": event["id"], "title": event["title"],
                             "reason": "日期或起止时刻不完整，或区间无效；未判断冲突，不推算时长或跨日。"})
        else:
            intervals.append((event, interval))
    for index, (first, (a_start, a_end)) in enumerate(intervals):
        for second, (b_start, b_end) in intervals[index + 1:]:
            start, end = max(a_start, b_start), min(a_end, b_end)
            if start < end:
                # Split cross-day overlap at midnight for date-specific presentation.
                while start < end:
                    stop = min(end, datetime.combine(start.date() + timedelta(days=1), time(), SHANGHAI))
                    conflicts.append(dict(_slot(start, stop), event_ids=[first["id"], second["id"]],
                                          titles=[first["title"], second["title"]]))
                    start = stop
    return {"mode": bundle["mode"], "conflicts": conflicts, "warnings": warnings}


def find_free_slots(bundle, start, end, day_start, day_end):
    """Find gaps in an explicit daily window; incomplete events remain warnings."""
    _, _, events = _context(bundle)
    first, last = _day(start), _day(end)
    if last < first or _clock(day_end) <= _clock(day_start):
        raise ValueError("日期范围或每日可安排时段无效；每日时段必须在同一天内")
    intervals = [interval for event in events if (interval := _interval(event))]
    slots = []
    day = first
    while day <= last:
        begin, finish = _point(day.isoformat(), day_start), _point(day.isoformat(), day_end)
        occupied = sorted((max(begin, a), min(finish, b)) for a, b in intervals
                          if a < finish and b > begin)
        cursor = begin
        for a, b in occupied:
            if cursor < a:
                slots.append(_slot(cursor, a))
            cursor = max(cursor, b)
        if cursor < finish:
            slots.append(_slot(cursor, finish))
        day += timedelta(days=1)
    warnings = [warning for warning in find_conflicts(bundle)["warnings"]
                if any(event["id"] == warning["event_id"] and
                       (not event.get("date") or _in_range(event, first, last)) for event in events)]
    return {"mode": bundle["mode"], "slots": slots, "warnings": warnings,
            "provisional": bool(warnings),
            "basis": "仅依据传入的完整课程和活动区间；缺时刻事项未占用，仍需核对。"}


def suggest_preparation(bundle, event_id, minutes, start, end, day_start, day_end, limit=2,
                        not_before=None):
    """Suggest independent continuous alternatives; never write or change a deadline."""
    today, _, events = _context(bundle)
    if not isinstance(minutes, int) or isinstance(minutes, bool) or minutes <= 0 or limit <= 0:
        raise ValueError("预计用时与候选数量必须是正整数")
    target = next((event for event in events if event["id"] == event_id), None)
    if not target or target["type"] not in DEADLINES or target.get("status") in FINISHED:
        raise ValueError("需选定一个未完成、未取消的提交事项")
    if not target.get("date") or not target.get("start_time"):
        raise ValueError("截止日期或时刻不完整，不能保证准备时段在截止前")
    if _day(start) < today:
        raise ValueError("准备时段的开始日期不能早于查看日")
    floor = datetime.combine(today, time(), SHANGHAI)
    if not_before is not None:
        floor = datetime.fromisoformat(not_before.replace("Z", "+00:00"))
        if floor.tzinfo is None or floor.astimezone(SHANGHAI).date() < today:
            raise ValueError("not_before 必须包含时区，且不能早于查看日")
        floor = floor.astimezone(SHANGHAI)
        if floor.second or floor.microsecond:
            floor = floor.replace(second=0, microsecond=0) + timedelta(minutes=1)
    elif _day(start) == today:
        raise ValueError("安排包含今天时，请提供 not_before 当前时刻，避免推荐已经过去的时段")
    available = find_free_slots(bundle, start, end, day_start, day_end)
    deadline = _point(target["date"], target["start_time"])
    candidates, available_minutes, largest = [], 0, 0
    for slot in available["slots"]:
        begin = max(_point(slot["date"], slot["start_time"]), floor)
        finish = min(_point(slot["end_date"], slot["end_time"]), deadline)
        duration = max(0, int((finish - begin).total_seconds() // 60))
        available_minutes += duration
        largest = max(largest, duration)
        if duration >= minutes and len(candidates) < limit:
            candidates.append(dict(_slot(begin, begin + timedelta(minutes=minutes)), label="建议"))
    return {"mode": bundle["mode"], "event_id": event_id, "title": target["title"],
            "deadline": {"date": target["date"], "time": target["start_time"]},
            "estimated_minutes": minutes, "candidates": candidates,
            "available_minutes": available_minutes, "largest_continuous_minutes": largest,
            "shortfall_minutes": max(0, minutes - available_minutes),
            "provisional": available["provisional"], "warnings": available["warnings"],
            "note": "候选为互斥备选，每个连续完成全部预计用时；未保存，不修改教师截止时间。"
                    if candidates else f"截止前可用 {available_minutes} 分钟，最长连续 {largest} 分钟；"
                    f"所需 {minutes} 分钟，合计还差 {max(0, minutes - available_minutes)} 分钟。未找到足够连续空档。"}


def opening(reminder="当前仅在查询时显示对话内临期提示，不提供后台主动推送。",
            collected_at=None):
    collected = f"\n资料收录：{collected_at}。" if collected_at else ""
    return ("欢迎使用华工校园学业日程助手，可整理消息、查看周计划与待确认事项。\n\n"
            "先输入「示例模式，载入示例」，再输入「示例模式，查询本周安排，今天为2026-11-16」。"
            "示例为合成数据，今天固定为2026-11-16；真实模式按北京时间当天查询。\n\n"
            f"提醒方式：{reminder}{collected}\n")


def _text(value):
    return str(value).replace("\n", " ").replace("\r", " ").replace("|", "／")


def _source_basis(source, excerpt=None):
    title = _text(source.get("title") or "来源信息未提供")
    if (source.get("url") or "").startswith(("https://", "http://")):
        basis = f"[{title}]({source['url']})"
    else:
        basis = title + (" " + _text(source["file_name"]) if source.get("file_name") else "")
    if excerpt:
        basis += "；原文：" + _text(excerpt)
    if source.get("ingested_at"):
        basis += "；收录：" + _text(source["ingested_at"])
    return basis


def _event_line(event, sources):
    day = event.get("date") or "日期待确认"
    start = event.get("start_time")
    if event["type"] in DEADLINES:
        stamp = f"截止 {start}" if start else "截止时刻未提供"
    elif start:
        if event.get("end_time"):
            end_day = event.get("end_date")
            stamp = f"{start}–{end_day + ' ' if end_day and end_day != event.get('date') else ''}{event['end_time']}"
        else:
            stamp = f"{start}（结束时刻未提供）"
    else:
        stamp = "时刻未提供"
    source = sources.get(event.get("source_id"), {})
    basis = _source_basis(source, event.get("source_excerpt"))
    corrections = []
    for entry in event.get("history", []):
        updated_source = entry.get("source", {})
        if entry.get("changes") and updated_source.get("text"):
            citation = _source_basis(updated_source, updated_source["text"])
            if citation not in corrections:
                corrections.append(citation)
    extraction = (event.get("m2") or source.get("m2") or {}).get("extraction", {})
    metadata = []
    requirements = source.get("submission_requirements", {}).get(event["id"], [])
    if requirements:
        metadata.append("提交要求：" + "、".join(requirements))
    if extraction.get("materials"):
        metadata.append("材料：" + "、".join(extraction["materials"]))
    for field, label in (("audience", "适用对象"), ("relevance", "相关性"),
                         ("basis", "判断依据"), ("entry", "办理入口")):
        if extraction.get(field):
            metadata.append(label + "：" + str(extraction[field]))
    if extraction.get("entry_url"):
        metadata.append("办理链接：" + extraction["entry_url"])
    extra = "。" + _text("；".join(metadata)) if metadata else ""
    pending = event.get("pending_fields", [])
    note = "；待确认：" + "、".join(FIELDS.get(field, field) for field in pending) if pending else ""
    correction_text = "。更正依据：" + "；".join(corrections) if corrections else ""
    return (f"- {_text(day)} {stamp}｜{_text(event['title'])}｜"
            f"{_text(event.get('location') or '地点未提供')}｜"
            f"{STATUS.get(event.get('status'), '状态未提供')}。原始依据：{basis}{note}{extra}{correction_text}")


def render_report(report):
    sources = {source["id"]: source for source in report["sources"]}
    week = report["kind"] != "tonight"
    mode = "示例模式" if report["mode"] == "example" else "真实模式"
    title = {"week": "本周安排", "week-brief": "本周简报", "tonight": "今晚简报"}[report["kind"]]
    lines = [f"# {title}", "",
             f"{mode}｜今天 {report['today']}｜北京时间", ""]
    sections = [(f"本周事项（{report['start']}～{report['end']}）" if week else "明天课程与活动",
                 report["scheduled"] if week else [event for event in report["scheduled"]
                                                    if event["type"] in ("course", "activity")]),
                ("本周截止" if week else f"三天内截止（{report['start']}～{report['end']}，含今天）", report["due"]),
                ("逾期未完成（日期早于今天）", report["overdue"]),
                (f"待确认（{len(report['pending'])} 个事项，{len(report['questions'])} 个来源问题）", report["pending"])]
    for title, events in sections:
        lines.extend([f"## {title}", ""])
        lines.extend(_event_line(event, sources) for event in events)
        if not events:
            lines.append("无。")
        if title.startswith("待确认"):
            for question in report["questions"]:
                source = sources.get(question.get("source_id"), {})
                basis = f"（来源：{_text(source['title'])}）" if source.get("title") else ""
                lines.append(f"- {_text(question['question'])}{basis}")
        lines.append("")
    lines.extend(["## 时间冲突", ""])
    for conflict in report['conflicts']:
        end_date = conflict['end_date'] + ' ' if conflict['end_date'] != conflict['date'] else ''
        lines.append(f"- {conflict['date']} {conflict['start_time']}–{end_date}{conflict['end_time']}｜"
                     f"{_text(' 与 '.join(conflict['titles']))}，重叠 {conflict['minutes']} 分钟。")
    if not report['conflicts']:
        lines.append("已知完整时段中未发现冲突。")
    for warning in report['conflict_warnings']:
        lines.append(f"- {_text(warning['title'])}：{_text(warning['reason'])}")
    lines.append("")
    lines.extend(["## " + ("本周实际变化" if week else "今天实际变化"), ""])
    for change in report["changes"]:
        title = report["event_titles"].get(change["event_id"], "事项")
        details = "；".join(f"{FIELDS.get(field, field)}：{value.get('before')} → {value.get('after')}"
                           for field, value in change.get("changes", {}).items())
        source = change.get('source', {})
        citation = '。更正依据：' + _source_basis(source, source.get('text')) if source.get('text') else ''
        lines.append(f"- {_text(change['applied_at'])}｜{_text(title)}｜{_text(details or change.get('kind', '变更'))}{citation}")
    if not report["changes"]:
        lines.append("无已提供的变更记录。")
    return "\n".join(lines) + "\n"


def render_analysis(result, kind):
    title = {'conflicts': '时间冲突', 'free': '可安排空档', 'prepare': '准备时段建议'}[kind]
    mode = '示例模式' if result['mode'] == 'example' else '真实模式'
    lines = [f'# {title}', '', mode + '｜北京时间', '']
    if kind == 'prepare':
        deadline = result['deadline']
        lines.extend([f"{_text(result['title'])}｜截止 {deadline['date']} {deadline['time']}｜"
                      f"预计用时 {result['estimated_minutes']} 分钟", ''])
    key = {'conflicts': 'conflicts', 'free': 'slots', 'prepare': 'candidates'}[kind]
    for slot in result[key]:
        last = slot['end_date'] + ' ' if slot['end_date'] != slot['date'] else ''
        label = _text(' 与 '.join(slot['titles'])) + '：' if kind == 'conflicts' else ''
        if kind == 'prepare':
            label = '建议：'
        lines.append(f"- {label}{slot['date']} {slot['start_time']}–{last}{slot['end_time']}，{slot['minutes']} 分钟。")
    if not result[key]:
        lines.append('已知完整时段中未发现冲突。' if kind == 'conflicts' else '未找到符合条件的时段。')
    if kind == 'free':
        lines.extend(['', result['basis']])
    if kind == 'prepare':
        lines.extend(['', result['note']])
    if result.get('warnings'):
        lines.extend(['', '待核对时段：'])
        lines.extend(f"- {_text(w['title'])}：{_text(w['reason'])}" for w in result['warnings'])
    return '\n'.join(lines) + '\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("welcome", "week", "tonight", "week-brief", "conflicts", "free", "prepare"))
    parser.add_argument("--input", type=Path, help="Decoded runtime snapshot bundle JSON")
    parser.add_argument("--out", type=Path)
    parser.add_argument("--format", choices=("json", "md"), default="md")
    parser.add_argument("--start")
    parser.add_argument("--end")
    parser.add_argument("--day-start")
    parser.add_argument("--day-end")
    parser.add_argument("--event-id")
    parser.add_argument("--minutes", type=int)
    parser.add_argument("--not-before", help="Current time with timezone when planning today")
    args = parser.parse_args()
    try:
        if args.command == "welcome":
            result = opening()
        else:
            if args.input is None:
                raise ValueError("需要 --input，内容为当前账号本轮在线快照解码后的 bundle")
            bundle = json.loads(args.input.read_text(encoding="utf-8-sig"))
            if args.command in ("week", "tonight", "week-brief"):
                result = build_report(bundle, args.command)
                if args.format == "md":
                    result = render_report(result)
            elif args.command == "conflicts":
                result = find_conflicts(bundle)
            else:
                if not all((args.start, args.end, args.day_start, args.day_end)):
                    raise ValueError("空档和准备建议需要 --start --end --day-start --day-end")
                options = (args.start, args.end, args.day_start, args.day_end)
                if args.command == "free":
                    result = find_free_slots(bundle, *options)
                else:
                    if not args.event_id or args.minutes is None:
                        raise ValueError("准备建议需要 --event-id 和 --minutes")
                    result = suggest_preparation(bundle, args.event_id, args.minutes, *options,
                                                 not_before=args.not_before)
            if args.command in ('conflicts', 'free', 'prepare') and args.format == 'md':
                result = render_analysis(result, args.command)
        output = result if isinstance(result, str) else json.dumps(result, ensure_ascii=False, indent=2) + "\n"
        if args.out:
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(output, encoding="utf-8")
        else:
            print(output, end="")
    except (ValueError, KeyError, TypeError, OSError) as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
