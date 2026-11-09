"""Regression cases from D review, through the actual personal-table adapter."""

from copy import deepcopy
import importlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from modules.m3 import presentation as m3
from test_notice_runtime import apply_plan

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / 'platform/scut-schedule/skills/scut-schedule'
FIXTURE = json.loads((ROOT / 'docs/协作/联调样例.json').read_text(encoding='utf-8'))['D']['input_bundle']
NOW = '2026-11-16T10:00:00+08:00'


class M3IntegrationTests(unittest.TestCase):
    def setUp(self):
        sys.path.insert(0, str(SKILL / 'scripts'))
        self.addCleanup(sys.path.remove, str(SKILL / 'scripts'))
        self.schedule = importlib.import_module('schedule')
        self.runtime = importlib.import_module('runtime')
        self.notices = importlib.import_module('notice_runtime')
        self.bundle = deepcopy(FIXTURE)

    def test_completed_meeting_leaves_tomorrow_alert_but_remains_in_week_history(self):
        meeting = next(e for e in self.bundle['events'] if e['id'] == 'handoff-d-event-002')
        meeting['status'] = 'completed'
        report = m3.build_report(self.bundle, 'tonight')
        self.assertNotIn(meeting['id'], [e['id'] for e in report['scheduled']])
        self.assertNotIn(meeting['title'], m3.render_report(report))
        self.assertIn(meeting['id'], [e['id'] for e in m3.build_report(self.bundle)['scheduled']])

    def test_current_deadline_cites_old_correction_even_outside_report_week(self):
        payload = json.loads((SKILL / 'examples/m2-notice-save.json').read_text(encoding='utf-8'))
        correction = json.loads((SKILL / 'examples/m2-notice-correction.json').read_text(encoding='utf-8'))
        correction['correction'].update(title='示例更正：截止延至27日', url='https://example.com/notice-correction')
        content = apply_plan('', self.notices.prepare_notice('', payload, NOW))
        content = apply_plan(content, self.notices.prepare_correction(content, correction, '2026-11-17T11:00:00+08:00'))
        report = m3.build_report(self.notices.notice_snapshot(content, 'example', '2026-11-23'), 'week-brief')
        self.assertEqual(report['changes'], [])
        rendered = m3.render_report(report)
        for text in ('2026-11-27', payload['source']['title'], correction['correction']['title'],
                     correction['correction']['url'], correction['correction']['text']):
            self.assertIn(text, rendered)

    def cross_day_bundle(self):
        event = self.bundle['events'][0]
        self.bundle['events'] = [
            dict(event, id='overnight-a', title='跨月甲', type='course', date='2026-11-30', start_time='23:00', end_time='01:00', end_date='2026-12-01'),
            dict(event, id='overnight-b', title='跨月乙', date='2026-11-30', start_time='23:30', end_time='00:30', end_date='2026-12-01')]
        return self.bundle

    def test_cross_day_overlap_survives_table_storage_and_single_event_move(self):
        bundle = self.cross_day_bundle()
        content = self.schedule.prepare_import('', bundle, NOW)['csv']
        restored = self.runtime.current_bundle(content, 'example', '2026-11-30')
        self.assertEqual([e.get('end_date') for e in restored['events']], ['2026-12-01'] * 2)
        conflicts = m3.find_conflicts(restored)['conflicts']
        self.assertEqual([(c['date'], c['minutes']) for c in conflicts], [('2026-11-30', 30), ('2026-12-01', 30)])
        update = {'kind':'reschedule', 'text':'跨月甲改到2026年12月2日，其他时刻不变',
                  'sent_on':'2026-11-16', 'mode':'example', 'target_event_id':'overnight-a',
                  'changes':{'date':'2026-12-02'}}
        plan = self.runtime.prepare_event_update(content, update, NOW)
        self.assertEqual(len(plan['updates']), 1)
        content = apply_plan(content, plan)
        restored = self.runtime.current_bundle(content, 'example', '2026-11-30')
        events = {e['id']:e for e in restored['events']}
        self.assertEqual(events['overnight-a']['end_date'], '2026-12-03')
        self.assertEqual(events['overnight-b']['end_date'], '2026-12-01')
        self.assertEqual(events['overnight-a']['history'][0]['changes']['end_date'],
                         {'before':'2026-12-01', 'after':'2026-12-03'})
        self.assertEqual(m3.find_conflicts(restored)['conflicts'], [])
        replay = self.schedule.prepare_import(content, bundle, NOW)
        self.assertEqual(replay['records'], [])
        self.assertEqual(replay['csv'], content)

    def test_insufficient_preparation_reports_total_and_largest_continuous_gap(self):
        self.bundle['events'] = [dict(self.bundle['events'][1], id='ddl', date='2026-11-20', start_time='20:00')]
        result = m3.suggest_preparation(self.bundle, 'ddl', 180, '2026-11-20', '2026-11-20', '18:00', '20:00')
        self.assertEqual(result['candidates'], [])
        self.assertEqual((result['available_minutes'], result['largest_continuous_minutes'], result['shortfall_minutes']), (120, 120, 60))

    def test_authoritative_snapshot_questions_do_not_resurrect_resolved_sender_date(self):
        self.bundle['sources'][0]['questions'] = [{'field':'sent_on', 'question':'请提供原消息发送日'}]
        self.bundle['questions'] = []
        self.assertEqual(m3.build_report(self.bundle)['questions'], [])

    def test_assignment_requirements_are_visible_after_snapshot(self):
        message = {'text':'2026年11月20日20:00前交数据分析作业PDF', 'mode':'example', 'sent_on':'2026-11-16',
                   'submission_requirements':{'2026年11月20日20:00前交数据分析作业PDF':['包含数据分析过程']}}
        plan = self.runtime.prepare_message('', message, NOW)
        content = apply_plan('', plan)
        rendered = m3.render_report(m3.build_report(self.notices.notice_snapshot(content, 'example', '2026-11-16')))
        self.assertIn('提交要求：PDF、包含数据分析过程', rendered)

    def test_packaged_presentation_reads_csv_in_a_fresh_process(self):
        entry = SKILL / 'scripts/presentation_runtime.py'
        self.assertTrue(entry.exists(), 'Packaged CSV presentation entry is missing')
        content = self.schedule.prepare_import('', self.bundle, NOW)['csv']
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            shutil.copytree(SKILL, folder / 'skill', ignore=shutil.ignore_patterns('__pycache__'))
            (folder / 'latest.csv').write_text(content, encoding='utf-8')
            command = [sys.executable, '-B', '-X', 'utf8', str(folder/'skill/scripts/presentation_runtime.py'),
                       'tonight', '--existing', str(folder/'latest.csv'), '--mode','example', '--today','2026-11-16',
                       '--out', str(folder/'tonight.md')]
            result = subprocess.run(command, cwd=folder, capture_output=True, text=True, encoding='utf-8')
            self.assertEqual(result.returncode, 0, result.stderr)
            rendered = (folder/'tonight.md').read_text(encoding='utf-8')
            self.assertIn('提交示例活动确认表', rendered)
            self.assertNotIn('提交信息表', rendered)
            self.assertIn('15:00–15:40', rendered)

    def test_b_updates_change_occupancy_and_stop_finished_assignment_alerts(self):
        config = json.loads((SKILL / 'examples/term-config.json').read_text(encoding='utf-8'))
        timetable = (SKILL / 'examples/timetable.csv').read_text(encoding='utf-8')
        flow = json.loads((SKILL / 'examples/d2-d3-workflow.json').read_text(encoding='utf-8'))
        content = apply_plan('', self.runtime.prepare_timetable('', timetable, config, NOW))
        content = apply_plan(content, self.runtime.prepare_message(content, flow['assignment'], NOW))
        meeting = deepcopy(self.bundle)
        meeting['events'] = [e for e in meeting['events'] if e['id'] == 'handoff-d-event-002']
        content = self.schedule.prepare_import(content, meeting, NOW)['csv']
        snapshot = self.notices.notice_snapshot(content, 'example', '2026-11-16')
        self.assertEqual(m3.find_conflicts(snapshot)['conflicts'][0]['minutes'], 35)
        content = apply_plan(content, self.runtime.prepare_event_update(content, flow['reschedule'], NOW))
        snapshot = self.notices.notice_snapshot(content, 'example', '2026-11-16')
        self.assertEqual(m3.find_conflicts(snapshot)['conflicts'], [])
        content = apply_plan(content, self.runtime.prepare_event_update(content, flow['cancel'], NOW))
        content = apply_plan(content, self.runtime.prepare_event_update(content, flow['postpone'], NOW))
        report = m3.build_report(self.notices.notice_snapshot(content, 'example', '2026-11-20'), 'tonight')
        self.assertEqual([(e['date'],e['start_time']) for e in report['due']], [('2026-11-22','21:00')])
        content = apply_plan(content, self.runtime.prepare_event_update(content, flow['complete'], NOW))
        snapshot = self.notices.notice_snapshot(content, 'example', '2026-11-20')
        self.assertEqual(m3.build_report(snapshot, 'tonight')['due'], [])
        self.assertEqual(m3.find_free_slots(snapshot, '2026-11-18','2026-11-18','14:00','16:00')['slots'][0]['minutes'],120)
        self.assertEqual(self.runtime.prepare_timetable(content, timetable, config, NOW)['records'], [])
        self.assertEqual(self.runtime.prepare_message(content, flow['assignment'], NOW)['records'], [])
        self.assertEqual(sorted(e['status'] for e in snapshot['events']), ['cancelled','completed','not_started','not_started'])

    def test_free_and_preparation_have_readable_output_with_actual_shortfall(self):
        slots = m3.find_free_slots(self.bundle, '2026-11-17','2026-11-17','14:00','18:00')
        self.assertIn('16:00–18:00', m3.render_analysis(slots, 'free'))
        self.bundle['events'] = [dict(self.bundle['events'][1], id='ddl', date='2026-11-20', start_time='20:00')]
        result = m3.suggest_preparation(self.bundle, 'ddl', 180, '2026-11-20','2026-11-20','18:00','20:00')
        output = m3.render_analysis(result, 'prepare')
        self.assertIn('120', output)
        self.assertIn('60', output)
        self.assertIn('20:00', output)


if __name__ == '__main__':
    unittest.main()
