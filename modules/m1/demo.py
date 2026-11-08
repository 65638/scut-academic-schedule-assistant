"""核对共享样例并输出实际的 M1 输入和结果。"""

import argparse
from copy import deepcopy
import json
from pathlib import Path

from .message import parse_message
from .updates import plan_import, propose_location_update


def demo_parse(fixtures):
    message = fixtures["input"]
    actual = parse_message(message)
    expected = deepcopy(fixtures["expected_bundle"])
    # 共享样例用占位编号，实际编号必须由输入稳定生成。
    source = actual["sources"][0]
    assert len({event["id"] for event in actual["events"]}) == 2
    assert actual == parse_message(message)
    expected["sources"][0].update(id=source["id"], title=source["title"])
    for event, expected_event in zip(actual["events"], expected["events"]):
        expected_event.update(id=event["id"], source_id=source["id"])
    assert actual == expected

    other_message = dict(message, sent_on="2026-11-30")
    other = parse_message(other_message)
    assert [event["date"] for event in other["events"]] == ["2026-12-01", "2026-12-04"]

    missing_message = dict(fixtures["missing_sender_date"]["input"], mode="example", today=message["sent_on"])
    missing = parse_message(missing_message)
    assert missing["sources"][0]["sent_on"] is None
    assert missing["events"][0]["date"] is None
    assert missing["events"][0]["start_time"] == "19:00"
    assert missing["events"][0]["pending_fields"] == ["date"]
    assert missing["questions"] == [{"field": "sent_on", "question": "请提供原消息的发送日期。"}]

    activity_excerpt = actual["events"][0]["source_excerpt"]
    reminder_text = f"{activity_excerpt}，请大家准时参加"
    reminder = parse_message(dict(message, text=reminder_text))
    assert reminder["sources"][0]["text"] == reminder_text
    assert len(reminder["events"]) == 1 and "questions" not in reminder
    activity = reminder["events"][0]
    assert activity["source_excerpt"] == activity_excerpt
    assert (activity["date"], activity["start_time"], activity["location"]) == ("2026-11-17", "19:00", "A201")

    unparsed_excerpt = "下周一交实验报告"
    mixed = parse_message(dict(message, text=f"{reminder_text}，{unparsed_excerpt}"))
    assert [event["source_excerpt"] for event in mixed["events"]] == [activity_excerpt]
    question, = mixed["questions"]
    assert question["field"] == "source_excerpt" and unparsed_excerpt in question["question"]

    return {
        "sample": {"input": message, "output": actual},
        "another_sent_on": {"input": other_message, "output": other},
        "missing_sent_on": {"input": missing_message, "output": missing},
    }


def demo_update(fixtures):
    current = fixtures["expected_bundle"]
    update_source = fixtures["update_source"]
    update_message = dict(fixtures["update_input"], title=update_source["title"])
    expected = dict(fixtures["expected_update"], source=update_source)
    exact = propose_location_update(update_message, current)
    assert exact == expected

    message = fixtures["input"]
    parsed = parse_message(message)
    initial = plan_import(parsed, dict(parsed, events=[]))
    assert initial == {"bundle": parsed, "skipped_event_ids": []}
    original = initial["bundle"]

    # 按标题关联实际解析出的事项，保留原来源和更正来源。
    implicit_message = dict(update_message)
    del implicit_message["target_event_id"]
    update = propose_location_update(implicit_message, original)
    activity, submission = original["events"]
    assert update == dict(expected, target_event_id=activity["id"])
    updated_activity = dict(activity, **update["changes"])
    updated = dict(
        original,
        events=[updated_activity, submission],
        sources=original["sources"] + [update["source"]],
    )

    replay = plan_import(parse_message(message), updated)
    after_replay = updated["events"] + replay["bundle"]["events"]
    assert replay["skipped_event_ids"] == [activity["id"], submission["id"]]
    summary = {
        "event_count": len(after_replay),
        "activity_location": after_replay[0]["location"],
        "submission_date": after_replay[1]["date"],
        "submission_time": after_replay[1]["start_time"],
    }
    assert summary == fixtures["expected_after_replay"]
    assert after_replay == [dict(activity, location="A202"), submission]

    # 旧记录的事项编号可以不同，仍可凭相同来源编号和片段识别重放。
    legacy_message = dict(message, source_id=current["sources"][0]["id"])
    assert plan_import(parse_message(legacy_message), current)["bundle"]["events"] == []

    another = parse_message(dict(message, sent_on="2026-11-30"))
    another_activity = another["events"][0]
    ambiguous_bundle = dict(
        original,
        events=original["events"] + [another_activity],
        sources=original["sources"] + another["sources"],
    )
    ambiguous = propose_location_update(implicit_message, ambiguous_bundle)
    assert ambiguous["target_event_id"] is None and ambiguous["changes"] == {}
    assert ambiguous["pending_fields"] == ["target_event_id"]
    assert [event["id"] for event in ambiguous["candidates"]] == [activity["id"], another_activity["id"]]
    chosen = dict(implicit_message, target_event_id=another_activity["id"])
    selected = propose_location_update(chosen, ambiguous_bundle)
    assert selected == dict(expected, target_event_id=another_activity["id"])

    return {
        "fixture_update": {"input": update_message, "output": exact},
        "replay": {
            "input": message,
            "applied_update": update,
            "skipped_event_ids": replay["skipped_event_ids"],
            "summary": summary,
            "events": after_replay,
            "sources": updated["sources"],
        },
        "ambiguous_target": {"input": implicit_message, "output": ambiguous},
        "selected_target": {"input": chosen, "output": selected},
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case", nargs="?", choices=["parse", "update"], default="parse")
    args = parser.parse_args()
    fixture_path = Path(__file__).resolve().parents[2] / "docs" / "协作" / "联调样例.json"
    fixtures = json.loads(fixture_path.read_text(encoding="utf-8"))["B"]
    result = demo_parse(fixtures) if args.case == "parse" else demo_update(fixtures)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
