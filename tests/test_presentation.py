"""M3 business checks against shared expectations and the real M0/M1 snapshot."""

from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from modules.m3 import presentation as m3


ROOT = Path(__file__).resolve().parents[1]
PACKAGED = ROOT / 'platform/scut-schedule/skills/scut-schedule/scripts/presentation.py'
FIXTURE = json.loads((ROOT / 'docs/协作/联调样例.json').read_text(encoding='utf-8'))['D']


class PresentationTests(unittest.TestCase):
    def setUp(self):
        self.bundle = deepcopy(FIXTURE['input_bundle'])

    def event(self, **changes):
        return dict(self.bundle['events'][0], **changes)

    def test_shared_week_and_tonight_expectations_and_input_unchanged(self):
        original = deepcopy(self.bundle)
        expected = FIXTURE['expected']
        week = m3.build_report(self.bundle)
        self.assertEqual((week['start'], week['end']), ('2026-11-16', '2026-11-22'))
        self.assertEqual(len(week['scheduled']), expected['week']['scheduled_count'])
        self.assertEqual([e['id'] for e in week['pending']], expected['week']['pending_ids'])
        tonight = m3.build_report(self.bundle, 'tonight')
        tomorrow = expected['tonight_brief']
        self.assertEqual([e['id'] for e in tonight['scheduled'] if e['type'] == 'course'],
                         tomorrow['tomorrow_course_ids'])
        self.assertEqual([e['id'] for e in tonight['scheduled'] if e['type'] == 'activity'],
                         tomorrow['tomorrow_activity_ids'])
        self.assertEqual([e['id'] for e in tonight['due']], tomorrow['due_ids'])
        self.assertNotIn('提交信息表', m3.render_report(tonight))
        self.assertEqual(tonight['changes'], [])
        self.assertEqual(self.bundle, original)
        weekly_brief = m3.build_report(self.bundle, 'week-brief')
        self.assertIn('# 本周简报', m3.render_report(weekly_brief))
        self.assertEqual([e['id'] for e in weekly_brief['due']], [e['id'] for e in week['due']])

    def test_pending_fields_with_dates_and_unparsed_source_questions_survive(self):
        self.bundle['events'][0]['pending_fields'] = ['location']
        question = {'field': 'source_excerpt', 'question': '请核对「下周一交实验报告」'}
        self.bundle['sources'][0]['questions'] = [question]
        self.bundle['questions'] = [question]
        report = m3.build_report(self.bundle)
        self.assertEqual(len(report['pending']), 2)
        self.assertEqual(len(report['questions']), 1)
        self.assertIn('下周一交实验报告', m3.render_report(report))
        self.assertIn('待确认：地点', m3.render_report(report))

    def test_real_and_example_never_mix_and_invalid_decoding_is_explicit(self):
        self.bundle['sources'].append(dict(self.bundle['sources'][0], id='real-source', mode='real'))
        self.bundle['events'].append(self.event(id='real-event', source_id='real-source', title='私有真实事项'))
        report = m3.build_report(self.bundle)
        self.assertNotIn('私有真实事项', m3.render_report(report))
        self.assertNotIn('real-source', [s['id'] for s in report['sources']])
        self.bundle['events'][0]['pending_fields'] = '[]'
        with self.assertRaisesRegex(ValueError, 'snapshot'):
            m3.build_report(self.bundle)

    def test_completed_cancelled_and_date_only_deadlines(self):
        self.bundle['sources'][0]['url'] = None
        self.bundle['events'] = [
            self.event(id='done', type='submission', date='2026-11-15', status='completed'),
            self.event(id='cancelled', date='2026-11-17', status='cancelled'),
            self.event(id='overdue', type='submission', date='2026-11-15'),
            self.event(id='date-only', type='submission', date='2026-11-18', start_time=None)]
        report = m3.build_report(self.bundle)
        self.assertEqual([e['id'] for e in report['scheduled']], ['date-only'])
        self.assertEqual([e['id'] for e in report['due']], ['date-only'])
        self.assertEqual([e['id'] for e in report['overdue']], ['overdue'])
        self.assertIn('截止时刻未提供', m3.render_report(report))
        self.assertNotIn('23:59', m3.render_report(report))
        self.bundle['events'].append(self.event(id='notice', type='notice_task', date='2026-11-17',
                                                start_time=None, title='确认讲座日期'))
        self.assertEqual([e['id'] for e in m3.build_report(self.bundle)['due']], ['date-only'])

    def test_changes_use_actual_applied_time_in_shanghai_not_source_sent_on(self):
        event = self.bundle['events'][0]
        entry = {'kind': 'location', 'event_id': event['id'], 'applied_at': '2026-11-15T17:00:00Z',
                 'changes': {'location': {'before': 'A201', 'after': 'A202'}},
                 'source': {'sent_on': '2026-11-10'}}
        event['history'] = [entry, dict(entry, applied_at='2026-11-17T01:00:00+08:00')]
        self.bundle['changes'] = [entry]
        report = m3.build_report(self.bundle, 'tonight')
        self.assertEqual(len(report['changes']), 1)
        self.assertIn('A201 → A202', m3.render_report(report))
        self.assertEqual(len(m3.build_report(self.bundle)['changes']), 2)

    def test_shared_conflict_and_touching_boundaries_and_unknown_end(self):
        result = m3.find_conflicts(self.bundle)
        conflict = result['conflicts'][0]
        for field in ('event_ids', 'date', 'start_time', 'end_time'):
            self.assertEqual(conflict[field], FIXTURE['expected']['conflicts'][0][field])
        self.assertEqual([w['event_id'] for w in result['warnings']], ['handoff-b-event-001'])
        self.bundle['events'] = [self.event(id='a', start_time='14:00', end_time='15:00'),
                                 self.event(id='b', start_time='15:00', end_time='16:00')]
        self.assertEqual(m3.find_conflicts(self.bundle)['conflicts'], [])

    def test_deadlines_and_finished_events_do_not_occupy_slots(self):
        self.bundle['events'] = [self.event(id='a', start_time='14:00', end_time='16:00'),
                                 self.event(id='ddl', type='submission', start_time='15:00', end_time='17:00'),
                                 self.event(id='done', status='completed', start_time='15:00', end_time='17:00'),
                                 self.event(id='gone', status='cancelled', start_time='15:00', end_time='17:00')]
        self.assertEqual(m3.find_conflicts(self.bundle)['conflicts'], [])
        slots = m3.find_free_slots(self.bundle, '2026-11-17', '2026-11-17', '14:00', '18:00')
        self.assertEqual([(s['start_time'], s['end_time']) for s in slots['slots']], [('16:00', '18:00')])

    def test_cross_midnight_overlap_split_and_no_implicit_next_day(self):
        self.bundle['events'] = [self.event(id='a', start_time='23:00', end_time='01:00', end_date='2026-11-18'),
                                 self.event(id='b', start_time='23:30', end_time='00:30', end_date='2026-11-18')]
        overlaps = m3.find_conflicts(self.bundle)['conflicts']
        self.assertEqual([(c['date'], c['start_time'], c['end_time']) for c in overlaps],
                         [('2026-11-17', '23:30', '00:00'), ('2026-11-18', '00:00', '00:30')])
        next_day = m3.find_free_slots(self.bundle, '2026-11-18', '2026-11-18', '00:00', '02:00')
        self.assertEqual(next_day['slots'][0]['start_time'], '01:00')
        del self.bundle['events'][0]['end_date']
        self.assertEqual(m3.find_conflicts(self.bundle)['conflicts'], [])
        self.assertEqual(len(m3.find_conflicts(self.bundle)['warnings']), 1)

    def test_overlapping_busy_periods_merge_and_unknown_events_are_provisional(self):
        slots = m3.find_free_slots(self.bundle, '2026-11-17', '2026-11-17', '14:00', '18:00')
        self.assertEqual([(s['start_time'], s['end_time']) for s in slots['slots']], [('16:00', '18:00')])
        self.assertTrue(slots['provisional'])
        self.assertEqual(slots['warnings'][0]['title'], '班会')

    def test_preparation_two_continuous_alternatives_preserve_ddl_and_input(self):
        original = deepcopy(self.bundle)
        result = m3.suggest_preparation(self.bundle, 'handoff-b-event-002', 180,
                                       '2026-11-17', '2026-11-20', '16:00', '20:00')
        self.assertEqual([(s['date'], s['start_time'], s['end_time']) for s in result['candidates']],
                         [('2026-11-17', '16:00', '19:00'), ('2026-11-18', '16:00', '19:00')])
        self.assertEqual(result['deadline'], {'date': '2026-11-20', 'time': '18:00'})
        self.assertTrue(all(s['label'] == '建议' for s in result['candidates']))
        self.assertTrue(result['provisional'])
        self.assertEqual(self.bundle, original)

    def test_preparation_clips_at_deadline_and_never_offers_insufficient_or_past_slots(self):
        self.bundle['events'] = [self.event(id='ddl', type='submission', date='2026-11-16', start_time='18:00')]
        with self.assertRaisesRegex(ValueError, 'not_before'):
            m3.suggest_preparation(self.bundle, 'ddl', 180, '2026-11-16', '2026-11-16', '14:00', '20:00')
        result = m3.suggest_preparation(self.bundle, 'ddl', 180, '2026-11-16', '2026-11-16', '14:00', '20:00',
                                       not_before='2026-11-16T16:00:00+08:00')
        self.assertEqual(result['candidates'], [])
        enough = m3.suggest_preparation(self.bundle, 'ddl', 120, '2026-11-16', '2026-11-16', '14:00', '20:00',
                                       not_before='2026-11-16T16:00:00+08:00')
        self.assertEqual(enough['candidates'][0]['end_time'], '18:00')
        seconds = m3.suggest_preparation(self.bundle, 'ddl', 120, '2026-11-16', '2026-11-16', '14:00', '20:00',
                                        not_before='2026-11-16T15:59:30+08:00')
        self.assertEqual(seconds['candidates'][0]['start_time'], '16:00')

    def test_m2_notice_materials_relevance_and_correction_history_are_presented(self):
        scripts = ROOT / 'platform/scut-schedule/skills/scut-schedule/scripts'
        sys.path.insert(0, str(scripts))
        self.addCleanup(sys.path.remove, str(scripts))
        import notice_runtime
        from test_notice_runtime import apply_plan
        payload = json.loads((scripts.parent / 'examples/m2-notice-save.json').read_text(encoding='utf-8'))
        plan = notice_runtime.prepare_notice('', payload, '2026-11-16T10:00:00+08:00')
        content = apply_plan('', plan)
        snapshot = notice_runtime.notice_snapshot(content, 'example', '2026-11-23')
        text = m3.render_report(m3.build_report(snapshot))
        for expected in ('材料：报名表PDF', '相关性：明确相关', '判断依据：', '收录：2026-11-16'):
            self.assertIn(expected, text)
        correction = json.loads((scripts.parent / 'examples/m2-notice-correction.json').read_text(encoding='utf-8'))
        update = notice_runtime.prepare_correction(content, correction, '2026-11-23T11:00:00+08:00')
        self.assertEqual(len(update['updates']), 1)
        content = apply_plan(content, update)
        changed = m3.build_report(notice_runtime.notice_snapshot(content, 'example', '2026-11-23'), 'week-brief')
        self.assertEqual(changed['scheduled'][0]['date'], '2026-11-27')
        self.assertEqual(len(changed['changes']), 1)
        self.assertIn('2026-11-25 → 2026-11-27', m3.render_report(changed))

    def test_snapshot_adapter_preserves_mixed_message_and_location_history(self):
        scripts = ROOT / 'platform/scut-schedule/skills/scut-schedule/scripts'
        sys.path.insert(0, str(scripts))
        self.addCleanup(sys.path.remove, str(scripts))
        import runtime
        from test_runtime import apply_plan
        message = {'text': '明天20:00在B101开M1混合讨论会，请大家准时参加，下周一交实验报告',
                   'sent_on': '2026-11-16', 'mode': 'example', 'today': '2026-11-16'}
        plan = runtime.prepare_message('', message, '2026-11-16T10:00:00+08:00')
        content = apply_plan('', plan)
        update = runtime.prepare_location_update(content, {'text': 'M1混合讨论会地点改到B102',
                                                  'sent_on': '2026-11-16', 'mode': 'example'},
                                                 '2026-11-16T11:00:00+08:00')
        content = apply_plan(content, update)
        snapshot = runtime.current_bundle(content, 'example', '2026-11-16')
        report = m3.build_report(snapshot, 'tonight')
        text = m3.render_report(report)
        self.assertIn('下周一交实验报告', text)
        self.assertIn('B102', text)
        self.assertEqual(len(report['questions']), 1)
        self.assertEqual(len(report['changes']), 1)

    def test_full_shared_fixture_roundtrips_through_m0_table_and_snapshot(self):
        scripts = ROOT / 'platform/scut-schedule/skills/scut-schedule/scripts'
        sys.path.insert(0, str(scripts))
        self.addCleanup(sys.path.remove, str(scripts))
        import runtime
        from schedule import prepare_import
        plan = prepare_import('', self.bundle, '2026-11-09T16:00:00+08:00')
        self.assertEqual(len(plan['records']), 6)
        snapshot = runtime.current_bundle(plan['csv'], 'example', '2026-11-16')
        self.assertEqual(len(m3.build_report(snapshot)['scheduled']), 5)
        self.assertEqual(len(m3.build_report(snapshot)['pending']), 1)
        self.assertEqual(m3.find_conflicts(snapshot)['conflicts'][0]['minutes'], 40)
        self.assertEqual(prepare_import(plan['csv'], self.bundle, '2026-11-09T17:00:00+08:00')['records'], [])

    def test_packaged_script_is_standalone_and_bad_input_fails_without_output(self):
        self.assertEqual(PACKAGED.read_bytes(), Path(m3.__file__).read_bytes())
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            shutil.copy2(PACKAGED, base / 'presentation.py')
            (base / 'input.json').write_text(json.dumps(self.bundle), encoding='utf-8')
            result = subprocess.run([sys.executable, '-X', 'utf8', str(base/'presentation.py'), 'tonight',
                                     '--input', str(base/'input.json'), '--out', str(base/'brief.md')],
                                    cwd=base, capture_output=True, text=True, encoding='utf-8')
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('提交示例活动确认表', (base/'brief.md').read_text(encoding='utf-8'))
            self.bundle['events'][0]['start_time'] = '25:00'
            (base/'input.json').write_text(json.dumps(self.bundle), encoding='utf-8')
            failed = subprocess.run([sys.executable, str(base/'presentation.py'), 'week',
                                     '--input', str(base/'input.json'), '--out', str(base/'bad.md')],
                                    cwd=base, capture_output=True)
            self.assertNotEqual(failed.returncode, 0)
            self.assertFalse((base/'bad.md').exists())


if __name__ == '__main__':
    unittest.main()
