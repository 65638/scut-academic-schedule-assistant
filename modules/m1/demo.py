"""核对共享样例并输出实际的 M1 输入和结果。"""

from copy import deepcopy
import json
from pathlib import Path

from .message import parse_message


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

    return {
        "sample": {"input": message, "output": actual},
        "another_sent_on": {"input": other_message, "output": other},
        "missing_sent_on": {"input": missing_message, "output": missing},
    }


def main():
    fixture_path = Path(__file__).resolve().parents[2] / "docs" / "协作" / "联调样例.json"
    fixtures = json.loads(fixture_path.read_text(encoding="utf-8"))["B"]
    print(json.dumps(demo_parse(fixtures), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
