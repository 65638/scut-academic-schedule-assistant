"""M1 + M0 integration. Plans native library writes; never stores account state."""
import argparse
import csv
from datetime import datetime
import json
from pathlib import Path

from m1.message import parse_message
from m1.timetable import parse_timetable
from m1.updates import plan_import, propose_event_update, propose_location_update
from schedule import COLUMNS, SHANGHAI, prepare_import, read_rows


def current_bundle(content, mode, today):
    if mode not in ('example', 'real'):
        raise ValueError('需要明确真实或示例模式')
    events, sources, questions = [], {}, []
    for row in read_rows(content):
        if row['mode'] != mode:
            continue
        source = json.loads(row['source'])
        history = source.pop('event_history', [])
        event = {key: row[key] or None for key in COLUMNS
                 if key not in ('source', 'mode', 'campus', 'timezone')}
        event['pending_fields'] = json.loads(row['pending_fields'])
        event['history'] = history
        events.append(event)
        sources[source['id']] = source
        for entry in history:
            sources.setdefault(entry['source']['id'], entry['source'])
        for question in source.get('questions', []):
            if question['field'] == 'sent_on' and event['date']:
                continue
            if question not in questions:
                questions.append(question)
    return {'mode': mode, 'today': today, 'timezone': 'Asia/Shanghai',
            'campus': '大学城校区', 'events': events,
            'sources': list(sources.values()), 'questions': questions}


def _reuse_source(message, current):
    """Reuse a saved source on replay or when its sender date is supplied."""
    message = dict(message)
    if message.get('source_id'):
        return message
    matches = [s for s in current['sources'] if s.get('text') == message['text']]
    exact = [s for s in matches if s.get('sent_on') == message.get('sent_on')]
    candidates = (exact or [s for s in matches if s.get('sent_on') is None]
                  if message.get('sent_on') else matches)
    if len(candidates) > 1:
        raise ValueError('找到多条同原文来源，请选定原消息 source_id 后重试')
    if candidates:
        message['source_id'] = candidates[0]['id']
        if not message.get('sent_on'):
            message['sent_on'] = candidates[0].get('sent_on')
    return message


def _patch(row, values, source, kind, now):
    original = json.loads(row['source'])
    changes = {key: {'before': row[key] or None, 'after': value or None}
               for key, value in values.items() if row[key] != value}
    correction = dict(source, ingested_at=now)
    if kind == 'sender_date':
        changes['source.sent_on'] = {'before': original.get('sent_on'), 'after': source['sent_on']}
    original.setdefault('event_history', []).append({
        'kind': kind, 'event_id': row['id'], 'changes': changes,
        'source': correction, 'applied_at': now})
    if kind == 'sender_date':
        original['sent_on'] = source['sent_on']
    if kind == 'sender_date' or values.get('date'):
        original['questions'] = [q for q in original.get('questions', []) if q['field'] != 'sent_on']
    values = dict(values, source=json.dumps(original, ensure_ascii=False))
    return {'event_id': row['id'], 'properties': {key: {'text': value} for key, value in values.items()}}


def prepare_message(content, message, now):
    mode = message.get('mode', 'real')
    current = current_bundle(content, mode, message.get('today'))
    message = _reuse_source(message, current)
    incoming = parse_message(message)
    saved_dates = {event['id']: event.get('date') for event in current['events']}
    if all(event['date'] or saved_dates.get(event['id']) for event in incoming['events']):
        incoming['questions'] = [q for q in incoming.get('questions', []) if q['field'] != 'sent_on']
    incoming['sources'][0]['questions'] = incoming.get('questions', [])
    import_plan = plan_import(incoming, current)
    additions = prepare_import(content, import_plan['bundle'], now)
    updates = []
    rows = [row for row in read_rows(content) if row['mode'] == mode]
    # M1 intentionally skips duplicate IDs; date completion is an in-place write.
    for event in incoming['events']:
        matches = [row for row in rows if row['id'] == event['id'] or
                   (row['source_id'], row['source_excerpt']) == (event['source_id'], event['source_excerpt'])]
        if len(matches) > 1:
            raise ValueError('同一事项对应多条记录，请先选定要补充的原事项')
        if matches:
            row = matches[0]
            source = json.loads(row['source'])
            if not source.get('sent_on') and message.get('sent_on'):
                values = {}
                if not row['date'] and event['date']:
                    values['date'] = event['date']
                    values['pending_fields'] = json.dumps(
                        [field for field in json.loads(row['pending_fields']) if field != 'date'], ensure_ascii=False)
                updates.append(_patch(row, values, incoming['sources'][0], 'sender_date', now))
    return {'records': additions['records'], 'updates': updates,
            'skipped_event_ids': import_plan['skipped_event_ids'],
            'questions': incoming.get('questions', []), 'saved_to_cloud': False}


def prepare_timetable(content, csv_text, config, now, *, file_name=None):
    current = current_bundle(content, config['mode'], config.get('today'))
    incoming = parse_timetable(csv_text, config, file_name=file_name)
    import_plan = plan_import(incoming, current)
    additions = prepare_import(content, import_plan['bundle'], now)
    return {'records': additions['records'], 'updates': [], 'questions': [],
            'skipped_event_ids': import_plan['skipped_event_ids'], 'saved_to_cloud': False}


def _update_plan(content, proposal, kind, now):
    result = {'records': [], 'updates': [], 'questions': [], 'saved_to_cloud': False}
    if proposal.get('question'):
        result.update(candidates=proposal['candidates'], questions=[{
            'field': 'target_event_id', 'question': proposal['question']}])
    elif proposal['changes']:
        row = next(row for row in read_rows(content) if row['id'] == proposal['target_event_id'])
        values = dict(proposal['changes'])
        if 'date' in values:
            values['pending_fields'] = json.dumps(
                [field for field in json.loads(row['pending_fields']) if field != 'date'], ensure_ascii=False)
        result['updates'].append(_patch(row, values, proposal['source'], kind, now))
    return result


def prepare_location_update(content, message, now):
    current = current_bundle(content, message.get('mode', 'real'), message.get('today'))
    return _update_plan(content, propose_location_update(message, current), 'location', now)


def prepare_event_update(content, message, now):
    current = current_bundle(content, message.get('mode', 'real'), message.get('today'))
    return _update_plan(content, propose_event_update(message, current), message['kind'], now)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['message', 'location', 'timetable', 'update', 'snapshot'])
    parser.add_argument('--existing', type=Path, help='CSV freshly read from the current personal table')
    parser.add_argument('--input', type=Path, help='JSON for message/location/update')
    parser.add_argument('--csv', type=Path, help='Eight-column timetable CSV')
    parser.add_argument('--config', type=Path, help='Timetable term and period configuration JSON')
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--mode', choices=['example', 'real'], default='real')
    parser.add_argument('--today')
    args = parser.parse_args()
    try:
        content = args.existing.read_text(encoding='utf-8-sig') if args.existing else ''
        now = datetime.now(SHANGHAI).isoformat(timespec='seconds')
        if args.command == 'snapshot':
            today = args.today or datetime.now(SHANGHAI).date().isoformat()
            result = current_bundle(content, args.mode, today)
        elif args.command == 'timetable':
            if not args.csv or not args.config:
                parser.error('timetable 需要 --csv 和 --config')
            result = prepare_timetable(
                content, args.csv.read_text(encoding='utf-8-sig'),
                json.loads(args.config.read_text(encoding='utf-8-sig')), now, file_name=args.csv.name)
        else:
            if not args.input:
                parser.error('message/location/update 需要 --input')
            message = json.loads(args.input.read_text(encoding='utf-8-sig'))
            action = {'message': prepare_message, 'location': prepare_location_update,
                      'update': prepare_event_update}[args.command]
            result = action(content, message, now)
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    except (ValueError, KeyError, OSError, csv.Error) as error:
        parser.error(str(error))
    print(json.dumps({'output': str(args.out), 'records': len(result.get('records', [])),
                      'updates': len(result.get('updates', [])), 'questions': result.get('questions', []),
                      'saved_to_cloud': False}, ensure_ascii=False))


if __name__ == '__main__':
    main()
