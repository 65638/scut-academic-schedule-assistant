"""Present a freshly read personal-table CSV with M1/M2 sources and history."""

import argparse
from datetime import datetime
import json
from pathlib import Path

from notice_runtime import notice_snapshot
from presentation import (SHANGHAI, build_report, find_conflicts, find_free_slots,
                          opening, render_analysis, render_report, suggest_preparation)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('welcome', 'week', 'tonight', 'week-brief', 'conflicts', 'free', 'prepare'))
    parser.add_argument('--existing', type=Path, help='CSV freshly read from the current account')
    parser.add_argument('--mode', choices=('real', 'example'), default='real')
    parser.add_argument('--today')
    parser.add_argument('--out', type=Path)
    parser.add_argument('--format', choices=('md', 'json'), default='md')
    for option in ('start', 'end', 'day-start', 'day-end', 'event-id', 'not-before'):
        parser.add_argument('--' + option)
    parser.add_argument('--minutes', type=int)
    args = parser.parse_args()
    try:
        now = datetime.now(SHANGHAI)
        today = args.today or now.date().isoformat()
        if args.command == 'welcome':
            result = opening()
        else:
            if args.existing is None:
                parser.error('查询需要 --existing，指向本轮本人在线表快照')
            if args.mode == 'example' and args.today is None:
                parser.error('示例查询需要显式指定 --today')
            bundle = notice_snapshot(args.existing.read_text(encoding='utf-8-sig'), args.mode, today)
            if args.command in ('week', 'tonight', 'week-brief'):
                result = build_report(bundle, args.command)
                if args.format == 'md':
                    result = render_report(result)
            elif args.command == 'conflicts':
                result = find_conflicts(bundle)
            else:
                if not all((args.start, args.end, args.day_start, args.day_end)):
                    parser.error('空档与准备建议需要 --start --end --day-start --day-end')
                window = (args.start, args.end, args.day_start, args.day_end)
                if args.command == 'free':
                    result = find_free_slots(bundle, *window)
                else:
                    if not args.event_id or args.minutes is None:
                        parser.error('准备建议需要 --event-id 和 --minutes')
                    floor = args.not_before
                    if floor is None and args.mode == 'real' and today == now.date().isoformat():
                        floor = now.isoformat()
                    result = suggest_preparation(bundle, args.event_id, args.minutes, *window, not_before=floor)
            if args.command in ('conflicts', 'free', 'prepare') and args.format == 'md':
                result = render_analysis(result, args.command)
        output = result if isinstance(result, str) else json.dumps(result, ensure_ascii=False, indent=2) + '\n'
        if args.out:
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(output, encoding='utf-8')
        else:
            print(output, end='')
    except (ValueError, KeyError, OSError) as error:
        parser.error(str(error))


if __name__ == '__main__':
    main()
