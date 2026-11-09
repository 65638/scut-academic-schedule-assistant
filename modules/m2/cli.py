import argparse
import json
from pathlib import Path
from typing import Any, Dict, Optional, Sequence

from .notice import (
    build_bundle,
    compare_notice_versions,
    extract_notice,
    refresh_sources,
    validate_candidate_extraction,
)


def _read_json(path: str) -> Dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _write_json(value: Dict[str, Any], output: Optional[str]) -> None:
    text = json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    if output:
        Path(output).write_text(text, encoding="utf-8")
    else:
        print(text, end="")


def _extract(payload: Dict[str, Any]) -> Dict[str, Any]:
    source = payload.get("source", payload.get("input"))
    if source is None:
        raise ValueError("extract input requires source or input")
    today = payload.get("today")
    if today is None:
        raise ValueError("extract input requires today")
    if "candidate_extraction" in payload:
        extraction = validate_candidate_extraction(
            source, payload["candidate_extraction"], payload.get("profile")
        )
    else:
        extraction = extract_notice(source, payload.get("profile"))
    return {
        "extraction": extraction,
        "bundle": build_bundle(
            source,
            extraction,
            today=today,
            timezone=payload.get("timezone", "Asia/Shanghai"),
            campus=payload.get("campus", "大学城校区"),
        ),
    }


def _compare(payload: Dict[str, Any]) -> Dict[str, Any]:
    correction = payload["correction"]
    return {
        "update": compare_notice_versions(
            payload["original_source"],
            correction,
            payload["target_event_id"],
        ),
        "source": correction,
    }


def _refresh(payload: Dict[str, Any]) -> Dict[str, Any]:
    return refresh_sources(payload["previous_sources"], payload["current_sources"])


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m modules.m2.cli")
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("extract", "compare", "refresh"):
        command_parser = subparsers.add_parser(command)
        command_parser.add_argument("--input", required=True)
        command_parser.add_argument("--output")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> None:
    args = build_parser().parse_args(argv)
    payload = _read_json(args.input)
    handlers = {"extract": _extract, "compare": _compare, "refresh": _refresh}
    _write_json(handlers[args.command](payload), args.output)


if __name__ == "__main__":
    main()
