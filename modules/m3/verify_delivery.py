"""Generate D4/D5 synthetic presentation evidence and verify source-package files.

Does not contact WorkBuddy, read personal snapshots, or write user tables.
"""

import argparse
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
from pathlib import Path
import re
import sys
from zipfile import ZipFile, ZIP_DEFLATED

from .presentation import (build_report, find_conflicts, find_free_slots, render_analysis,
                           render_report, suggest_preparation)


ROOT = Path(__file__).resolve().parents[2]
SKILL = ROOT / 'platform/scut-schedule/skills/scut-schedule'


def _write(path, content):
    path.write_text(content, encoding='utf-8')


def verify(out_dir):
    out_dir.mkdir(parents=True, exist_ok=True)
    plugin = ROOT / 'platform/scut-schedule'
    manifest = json.loads((plugin / '.codebuddy-plugin/plugin.json').read_text(encoding='utf-8'))
    version = manifest['version']
    if version != '0.5.0':
        raise ValueError('本任务的材料限定0.5.0；版本变化后请先更新说明')
    mirrors = [('modules/m3/presentation.py', 'scripts/presentation.py'),
               ('modules/m1/message.py', 'scripts/m1/message.py'),
               ('modules/m1/updates.py', 'scripts/m1/updates.py'),
               ('modules/m1/timetable.py', 'scripts/m1/timetable.py'),
               ('modules/m2/notice.py', 'scripts/m2/notice.py')]
    for local, packaged in mirrors:
        if (ROOT / local).read_bytes() != (SKILL / packaged).read_bytes():
            raise ValueError(f'模块与随包副本不同：{local}')
    files = sorted(p for p in plugin.rglob('*') if p.is_file() and '__pycache__' not in p.parts
                   and p.suffix not in ('.pyc', '.pyo'))
    checksums = {p.relative_to(plugin).as_posix(): sha256(p.read_bytes()).hexdigest() for p in files}
    # Concrete credential values and fixed personal identifiers must not enter the export.
    forbidden = re.compile(r'\b(?:gh[pousr]_[A-Za-z0-9_]{20,}|github_pat_[A-Za-z0-9_]{20,})\b'
                           r'|\b[0-9a-f]{8}-(?:[0-9a-f]{4}-){3}[0-9a-f]{12}\b', re.I)
    for file in files:
        if file.suffix in ('.py', '.md', '.json', '.csv'):
            if forbidden.search(file.read_text(encoding='utf-8-sig')):
                raise ValueError(f'需要人工核对凭据或固定个人标识：{file.relative_to(plugin)}')
    archive = out_dir / 'scut-schedule-0.5.0-source.zip'
    with ZipFile(archive, 'w', ZIP_DEFLATED) as package:
        for file in files:
            package.write(file, 'scut-schedule/' + file.relative_to(plugin).as_posix())
    with ZipFile(archive) as package:
        for name, checksum in checksums.items():
            if sha256(package.read('scut-schedule/' + name)).hexdigest() != checksum:
                raise ValueError('ZIP与源包不一致')

    sys.path.insert(0, str(SKILL / 'scripts'))
    from notice_runtime import prepare_notice, prepare_correction, notice_snapshot
    from schedule import prepare_import, COLUMNS
    import csv
    import io

    def apply_plan(content, plan):
        rows = list(csv.DictReader(io.StringIO(content))) if content else []
        rows.extend({k: v['text'] for k, v in row.items()} for row in plan['records'])
        for update in plan['updates']:
            row = next(row for row in rows if row['id'] == update['event_id'])
            row.update({k: v['text'] for k, v in update['properties'].items()})
        output = io.StringIO(newline='')
        writer = csv.DictWriter(output, fieldnames=COLUMNS, lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)
        return output.getvalue()

    bundle = json.loads((ROOT / 'docs/协作/联调样例.json').read_text(encoding='utf-8'))['D']['input_bundle']
    # New combined status input, preserving the shared fixture in the repository.
    status_bundle = deepcopy(bundle)
    meeting = next(e for e in status_bundle['events'] if e['title'] == '示例学院会议')
    meeting['status'] = 'completed'
    cancelled = dict(meeting, id='d4-synthetic-cancelled', title='示例已取消课程', type='course',
                     status='cancelled', start_time='16:00', end_time='17:00',
                     source_id='d4-source-cancelled',
                     source_excerpt='2026年11月17日16:00至17:00在B305上示例课程，现已取消')
    status_bundle['events'].append(cancelled)
    done = dict(status_bundle['events'][1], id='d4-synthetic-completed', title='示例已完成作业',
                date='2026-11-18', status='completed', source_id='d4-source-completed',
                source_excerpt='2026年11月18日18:00前提交示例作业，已完成')
    status_bundle['events'].append(done)
    for event in (cancelled, done):
        status_bundle['sources'].append(dict(
            id=event['source_id'], type='message', title=event['title'], mode='example',
            text=event['source_excerpt'], sent_on='2026-11-16'))
    content = prepare_import('', status_bundle, '2026-11-10T12:00:00+08:00')['csv']
    restored = notice_snapshot(content, 'example', '2026-11-16')
    week = build_report(restored)
    tonight = build_report(restored, 'tonight')
    weekly_brief = build_report(restored, 'week-brief')
    slots = find_free_slots(restored, '2026-11-17', '2026-11-17', '14:00', '18:00')
    assert meeting['id'] in [e['id'] for e in week['scheduled']]
    assert meeting['id'] not in [e['id'] for e in tonight['scheduled']]
    assert cancelled['id'] not in [e['id'] for e in week['scheduled']]
    assert done['id'] not in [e['id'] for e in weekly_brief['due']]
    assert done['id'] not in [e['id'] for e in tonight['due']]
    assert slots['slots'][0]['start_time'] == '15:40'
    assert len(tonight['pending']) == 1
    assert [e['date'] for e in tonight['due']] == ['2026-11-18']
    for name, report in [('周计划', week), ('今晚简报', tonight), ('本周简报', weekly_brief)]:
        _write(out_dir / (name + '.md'), render_report(report))
    _write(out_dir / '完成后空档.md', render_analysis(slots, 'free'))

    cross = deepcopy(bundle)
    template = cross['events'][0]
    cross['events'] = [dict(template, id='d4-cross-a', title='示例跨日甲', date='2026-11-30',
                            start_time='23:00', end_time='01:00', end_date='2026-12-01'),
                       dict(template, id='d4-cross-b', title='示例跨日乙', date='2026-11-30',
                            start_time='23:30', end_time='00:30', end_date='2026-12-01')]
    cross['sources'] = []
    for event in cross['events']:
        event['source_id'] = event['id'] + '-source'
        event['source_excerpt'] = (f"{event['title']}：2026年11月30日{event['start_time']}"
                                   f"至2026年12月1日{event['end_time']}，A201")
        cross['sources'].append(dict(id=event['source_id'], type='message', title=event['title'],
                                     mode='example', text=event['source_excerpt'],
                                     sent_on='2026-11-30'))
    snapshot = notice_snapshot(prepare_import('', cross, '2026-11-10T12:00:00+08:00')['csv'],
                               'example', '2026-11-30')
    conflict = find_conflicts(snapshot)
    assert [e['end_date'] for e in snapshot['events']] == ['2026-12-01'] * 2
    assert [(c['date'], c['minutes']) for c in conflict['conflicts']] == [
        ('2026-11-30', 30), ('2026-12-01', 30)]
    _write(out_dir / '跨日冲突.md', render_analysis(conflict, 'conflicts'))

    payload = json.loads((SKILL / 'examples/m2-notice-save.json').read_text(encoding='utf-8'))
    correction = json.loads((SKILL / 'examples/m2-notice-correction.json').read_text(encoding='utf-8'))
    content = apply_plan('', prepare_notice('', payload, '2026-11-10T12:00:00+08:00'))
    content = apply_plan(content, prepare_correction(content, correction, '2026-11-17T11:00:00+08:00'))
    restored_notice = notice_snapshot(content, 'example', '2026-11-23')
    notice_report = build_report(restored_notice, 'week-brief')
    notice_text = render_report(notice_report)
    assert notice_report['changes'] == []  # Correction is outside this report's week.
    assert '2026-11-27' in notice_text and correction['correction']['text'] in notice_text
    assert restored_notice['events'][0]['history']
    _write(out_dir / '通知与周外更正依据.md', notice_text)

    assignment = deepcopy(bundle)
    assignment['events'] = [dict(bundle['events'][1], id='d4-shortfall', title='示例三小时作业',
                                  date='2026-11-20', start_time='20:00',
                                  source_id='d4-shortfall-source',
                                  source_excerpt='2026年11月20日20:00前交示例三小时作业')]
    assignment['sources'] = [dict(id='d4-shortfall-source', type='message', mode='example',
                                  title='示例三小时作业', sent_on='2026-11-16',
                                  text=assignment['events'][0]['source_excerpt'])]
    shortfall = suggest_preparation(assignment, 'd4-shortfall', 180,
                                   '2026-11-20', '2026-11-20', '18:00', '20:00')
    assert (shortfall['available_minutes'], shortfall['shortfall_minutes']) == (120, 60)
    _write(out_dir / '准备时长不足.md', render_analysis(shortfall, 'prepare'))
    _write(out_dir / '合成输入.json', json.dumps({
        'description': 'Synthetic local inputs only; not personal-table snapshots or cloud results',
        'status_and_deadline_bundle': status_bundle,
        'cross_month_bundle': cross,
        'notice_save_payload': payload,
        'notice_correction_payload': correction,
        'notice_correction_applied_at_synthetic': '2026-11-17T11:00:00+08:00',
        'notice_report_today': '2026-11-23',
        'preparation_bundle': assignment,
        'preparation_window': {'minutes': 180, 'start': '2026-11-20', 'end': '2026-11-20',
                               'day_start': '18:00', 'day_end': '20:00'},
    }, ensure_ascii=False, indent=2) + '\n')

    result = {'generated_at': datetime.now(timezone(timedelta(hours=8))).isoformat(timespec='seconds'),
              'version': version, 'business_code_changed': False,
              'evidence_kind': 'synthetic_local_table_roundtrip_not_cloud_or_second_account',
              'new_synthetic_scenarios': {'completed_cancelled_and_pending': 'passed',
                                          'three_day_deadline_window': 'passed',
                                          'cross_month_end_date_roundtrip': 'passed',
                                          'correction_cited_outside_report_week': 'passed',
                                          'preparation_shortfall': 'passed'},
              'module_mirror_checks': len(mirrors), 'source_files': len(files),
              'archive_sha256': sha256(archive.read_bytes()).hexdigest(),
              'source_zip_byte_verification': 'passed',
              'known_token_and_uuid_literal_scan': 'passed_limited_pattern_scan',
              'personal_snapshot_read': False, 'cloud_writes': 0,
              'platform_short_flow': 'not_executed_no_desktop_control_tool',
              'second_account': 'not_tested'}
    (out_dir / '检查结果.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    (out_dir / '源包文件校验.json').write_text(json.dumps(
        {'version': version, 'sha256': checksums}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out-dir', type=Path, default=Path('work/d4-d5-evidence'))
    args = parser.parse_args()
    try:
        verify(args.out_dir)
    except (ValueError, KeyError, OSError, AssertionError) as error:
        parser.exit(1, f'D4/D5交付检查失败：{error}\n')


if __name__ == '__main__':
    main()
