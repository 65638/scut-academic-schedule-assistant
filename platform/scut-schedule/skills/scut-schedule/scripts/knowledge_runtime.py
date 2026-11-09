"""Search the public sources shipped with this skill; no network or account state."""

import argparse
import json
from pathlib import Path


REFERENCES = Path(__file__).resolve().parents[1] / "references"


def _entries():
    ledger = json.loads((REFERENCES / "knowledge/source_ledger.json").read_text(encoding="utf-8"))
    return [entry for entry in ledger["sources"]
            if entry["mode"] == "real" and entry.get("content_file")]


def _read(entry):
    document_path = REFERENCES / entry["content_file"]
    source_path = document_path.with_suffix(".source.json")
    source = json.loads(source_path.read_text(encoding="utf-8")) if source_path.exists() else None
    return dict(entry, document=document_path.read_text(encoding="utf-8"),
                content_kind="整理资料", source=source)


def search_public(query):
    """Match every whitespace-separated keyword in metadata or bundled text."""
    terms = query.casefold().split()
    if not terms:
        raise ValueError("请输入检索关键词")
    results = []
    for entry in _entries():
        document = _read(entry)
        source_text = document["source"]["text"] if document["source"] else ""
        searchable = "\n".join((entry["title"], entry["publisher"],
                                document["document"], source_text)).casefold()
        if all(term in searchable for term in terms):
            results.append(dict(entry, content_kind=document["content_kind"]))
    return results


def read_public(source_id):
    for entry in _entries():
        if entry["id"] == source_id:
            return _read(entry)
    raise ValueError(f"没有该公开来源：{source_id}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    search = commands.add_parser("search", help="按空格分隔的关键词检索随包资料")
    search.add_argument("--query", required=True)
    read = commands.add_parser("read", help="按来源编号读取整理资料与原文节选")
    read.add_argument("--source-id", required=True)
    for command in (search, read):
        command.add_argument("--out", type=Path)
    args = parser.parse_args()
    try:
        result = {"results": search_public(args.query)} if args.command == "search" else read_public(args.source_id)
    except ValueError as error:
        parser.error(str(error))
    output = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.out:
        args.out.write_text(output, encoding="utf-8")
    else:
        print(output, end="")


if __name__ == "__main__":
    main()
