"""Run the shipped CLI outside the repository and restore native table payloads."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from test_runtime import ROOT, SCRIPTS, apply_plan


class PackagedWorkflowTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.base = Path(temp.name)
        shutil.copytree(SCRIPTS, self.base / 'scripts', ignore=shutil.ignore_patterns('__pycache__'))
        self.content = ''

    def run_cli(self, command, payload=None, extra=()):
        existing = self.base / 'latest.csv'
        existing.write_text(self.content, encoding='utf-8')
        output = self.base / 'output.json'
        args = [sys.executable, '-B', '-X', 'utf8', str(self.base / 'scripts/runtime.py'),
                command, '--existing', str(existing), '--out', str(output), *extra]
        if payload is not None:
            path = self.base / 'input.json'
            path.write_text(json.dumps(payload, ensure_ascii=False), encoding='utf-8')
            args.extend(['--input', str(path)])
        result = subprocess.run(args, cwd=self.base, capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(output.read_text(encoding='utf-8'))

    def apply(self, command, payload=None, extra=()):
        plan = self.run_cli(command, payload, extra)
        self.assertFalse(plan['saved_to_cloud'])
        self.content = apply_plan(self.content, plan)
        return plan

    def snapshot(self):
        return self.run_cli('snapshot', extra=['--mode', 'example', '--today', '2026-11-16'])

    def test_timetable_single_reschedule_cancel_and_replay_from_installed_scripts(self):
        for name in ('timetable.csv', 'term-config.json'):
            shutil.copyfile(ROOT / 'modules/m1/examples' / name, self.base / name)
        args = ['--csv', str(self.base / 'timetable.csv'), '--config', str(self.base / 'term-config.json')]
        first_plan = self.apply('timetable', extra=args)
        self.assertEqual(len(first_plan['records']), 2)
        first, second = self.snapshot()['events']
        self.assertEqual([(e['date'], e['start_time'], e['end_time']) for e in (first, second)],
                         [('2026-11-17', '14:00', '15:35'), ('2026-11-24', '14:00', '15:35')])
        move = {'mode': 'example', 'kind': 'reschedule', 'text': '11月17日这次课改到18日B202',
                'sent_on': '2026-11-16', 'target_title': first['title'],
                'changes': {'date': '2026-11-18', 'location': 'B202'}}
        ambiguous = self.run_cli('update', move)
        self.assertEqual(ambiguous['records'] + ambiguous['updates'], [])
        self.assertEqual(len(ambiguous['candidates']), 2)
        move['target_event_id'] = first['id']
        self.assertEqual(self.run_cli('update', dict(move, mode='real'))['updates'], [])
        self.apply('update', move)
        cancel = {'mode': 'example', 'kind': 'cancel', 'text': '取消这次课',
                  'target_event_id': first['id'], 'sent_on': '2026-11-16'}
        self.apply('update', cancel)
        replay = self.apply('timetable', extra=args)
        self.assertEqual(replay['records'] + replay['updates'], [])
        self.assertEqual(set(replay['skipped_event_ids']), {first['id'], second['id']})
        self.assertEqual(self.apply('update', move)['updates'], [])
        self.assertEqual(self.apply('update', cancel)['updates'], [])
        restored, untouched = self.snapshot()['events']
        self.assertEqual((restored['id'], restored['date'], restored['location'], restored['status']),
                         (first['id'], '2026-11-18', 'B202', 'cancelled'))
        self.assertEqual(untouched, second)
        self.assertEqual([h['kind'] for h in restored['history']], ['reschedule', 'cancel'])
        self.assertEqual(restored['source_id'], first['source_id'])

    def test_assignment_requirements_complete_and_missing_date_resolution(self):
        for format_name in ('PDF', 'Word文档'):
            with self.subTest(format_name=format_name):
                self.content = ''
                message = {'mode': 'example', 'text': f'本周五20:00前交数据分析作业{format_name}'}
                self.apply('message', message)
                event = self.snapshot()['events'][0]
                self.assertEqual(event['pending_fields'], ['date'])
                source = self.snapshot()['sources'][0]
                self.assertEqual(source.get('submission_requirements'), {event['id']: [format_name]})
                postpone = {'mode': 'example', 'kind': 'postpone', 'text': '作业延期至11月22日21:00',
                            'target_event_id': event['id'], 'sent_on': '2026-11-16',
                            'changes': {'date': '2026-11-22', 'start_time': '21:00'}}
                self.apply('update', postpone)
                self.apply('update', {'mode': 'example', 'kind': 'complete', 'text': '作业已完成',
                                      'target_event_id': event['id'], 'sent_on': '2026-11-16'})
                replay = self.apply('message', message)
                self.assertEqual(replay['questions'], [])
                restored = self.snapshot()
                item = restored['events'][0]
                self.assertEqual((item['id'], item['date'], item['start_time'], item['status']),
                                 (event['id'], '2026-11-22', '21:00', 'completed'))
                self.assertEqual(item['pending_fields'], [])
                self.assertEqual(restored['questions'], [])
                self.assertEqual(restored['sources'][0]['submission_requirements'], source['submission_requirements'])
                self.assertEqual(restored['sources'][0]['ingested_at'], source['ingested_at'])
                self.assertEqual([h['kind'] for h in item['history']], ['postpone', 'complete'])


if __name__ == '__main__':
    unittest.main()
