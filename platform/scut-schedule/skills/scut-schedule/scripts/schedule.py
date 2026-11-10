"""Prepare WorkBuddy table rows and query weeks; no credentials or persistence."""
import argparse
import csv
from datetime import date, datetime, time, timedelta, timezone
import io
import json
from pathlib import Path


COLUMNS = ["id", "type", "title", "date", "start_time", "end_time", "location",
           "status", "pending_fields", "source_id", "source_excerpt", "source",
           "mode", "campus", "timezone"]
SHANGHAI = timezone(timedelta(hours=8))


def read_rows(content):
    if not content:
        return []
    reader = csv.DictReader(io.StringIO(content.lstrip("\ufeff")))
    if set(reader.fieldnames or []) != set(COLUMNS):
        raise ValueError("表格字段不符合华工日程 v0，不能当作空表继续保存")
    rows = list(reader)
    if any(None in row or any(v is None for v in row.values()) for row in rows):
        raise ValueError("表格有不完整的行，请核对在线表格")
    return rows


def prepare_import(existing, bundle, imported_at):
    rows = read_rows(existing)
    seen = {row["id"] for row in rows}
    sources = {source["id"]: source for source in bundle["sources"]}
    mode = bundle["mode"]
    if mode not in ("example", "real") or bundle["timezone"] != "Asia/Shanghai":
        raise ValueError("需要明确真实或示例模式，时区使用 Asia/Shanghai")
    additions, skipped = [], []
    for event in bundle["events"]:
        if not event["id"] or not event["title"].strip():
            raise ValueError("事项需要编号和标题")
        if event["id"] in seen:
            skipped.append(event["id"])
            continue
        if event["source_id"] not in sources:
            raise ValueError("事项缺少对应来源")
        day = event.get("date")
        if day:
            if date.fromisoformat(day).isoformat() != day:
                raise ValueError("日期使用 YYYY-MM-DD")
        for key in ("start_time", "end_time"):
            value = event.get(key)
            if value and time.fromisoformat(value).strftime("%H:%M") != value:
                raise ValueError("时刻使用 HH:MM")
        if event["status"] not in ("not_started", "in_progress", "completed", "cancelled"):
            raise ValueError("未知事项状态")
        source = dict(sources[event["source_id"]])
        if source.get("mode", mode) != mode:
            raise ValueError("来源与事项的真实／示例标记不一致")
        source["mode"] = mode
        source["ingested_at"] = source.get("ingested_at") or imported_at
        # Row-specific metadata fits the existing source JSON column.
        if event.get("end_date"):
            end_day = date.fromisoformat(event["end_date"])
            if end_day.isoformat() != event["end_date"] or (day and end_day < date.fromisoformat(day)):
                raise ValueError("结束日期需为 YYYY-MM-DD，且不早于开始日期")
            source["event_end_date"] = event["end_date"]
        row = {key: event.get(key) or "" for key in COLUMNS}
        row.update(pending_fields=json.dumps(event.get("pending_fields", []), ensure_ascii=False),
                   source=json.dumps(source, ensure_ascii=False), mode=mode,
                   campus=bundle["campus"], timezone=bundle["timezone"])
        additions.append(row)
        seen.add(event["id"])
    if not additions:
        return {"csv": existing, "records": [], "skipped": skipped}
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=COLUMNS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows + additions)
    records = [{key: {"text": value} for key, value in row.items()} for row in additions]
    return {"csv": output.getvalue(), "records": records, "skipped": skipped}


def week(content, today, mode):
    current = date.fromisoformat(today)
    monday = current - timedelta(days=current.weekday())
    sunday = monday + timedelta(days=6)
    events, pending = [], []
    for row in read_rows(content):
        if row["mode"] != mode or row["status"] == "cancelled":
            continue
        if not row["date"]:
            pending.append(row)
        elif monday <= date.fromisoformat(row["date"]) <= sunday:
            events.append(row)
    events.sort(key=lambda row: (row["date"], row["start_time"], row["id"]))
    return {"mode": mode, "today": today, "start": monday.isoformat(),
            "end": sunday.isoformat(), "events": events, "pending": pending}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    prepare = commands.add_parser("prepare")
    prepare.add_argument("--bundle", required=True, type=Path)
    prepare.add_argument("--existing", type=Path)
    prepare.add_argument("--out-dir", required=True, type=Path)
    query = commands.add_parser("week")
    query.add_argument("--csv", required=True, type=Path)
    query.add_argument("--today")
    query.add_argument("--mode", choices=["example", "real"], required=True)
    args = parser.parse_args()
    if args.command == "prepare":
        existing = args.existing.read_text(encoding="utf-8-sig") if args.existing else ""
        result = prepare_import(existing, json.loads(args.bundle.read_text(encoding="utf-8-sig")),
                                datetime.now(SHANGHAI).isoformat(timespec="seconds"))
        args.out_dir.mkdir(parents=True, exist_ok=True)
        (args.out_dir / "schedule.csv").write_text(result["csv"], encoding="utf-8")
        (args.out_dir / "records.json").write_text(json.dumps(result["records"], ensure_ascii=False), encoding="utf-8")
        print(json.dumps({"prepared": len(result["records"]), "skipped": result["skipped"],
                          "saved_to_cloud": False}, ensure_ascii=False))
    else:
        if args.mode == "example" and not args.today:
            parser.error("示例模式需要 --today，M0 演示今天为 2026-11-16")
        today = args.today or datetime.now(SHANGHAI).date().isoformat()
        print(json.dumps(week(args.csv.read_text(encoding="utf-8-sig"), today, args.mode), ensure_ascii=False))


if __name__ == "__main__":
    main()
