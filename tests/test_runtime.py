"""Integration behavior against the packaged M1 and real M0 functions."""
import csv
import importlib
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / 'platform/scut-schedule/skills/scut-schedule/scripts'
NOW = '2026-11-08T20:00:00+08:00'
MESSAGE = {'text': '明天19:00在A201开班会，本周五18:00前交信息表',
           'sent_on': '2026-11-16', 'mode': 'example', 'today': '2026-11-16'}


def apply_plan(content, plan):
    """Apply the native text payload to a table-shaped fixture; no cloud claim."""
    rows = list(csv.DictReader(io.StringIO(content))) if content else []
    for record in plan['records']:
        rows.append({k: v['text'] for k, v in record.items()})
    for update in plan['updates']:
        row = next(r for r in rows if r['id'] == update['event_id'])
        row.update({k: v['text'] for k, v in update['properties'].items()})
    if not rows:
        return content
    output = io.StringIO(newline='')
    writer = csv.DictWriter(output, fieldnames=list(rows[0]), lineterminator='\n')
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue((SCRIPTS / 'runtime.py').is_file(), 'M1 runtime is not implemented')
        sys.path.insert(0, str(SCRIPTS))
        self.addCleanup(sys.path.remove, str(SCRIPTS))
        self.runtime = importlib.import_module('runtime')

    def save(self, message=MESSAGE, content=''):
        plan = self.runtime.prepare_message(content, message, NOW)
        return apply_plan(content, plan), plan

    def test_double_message_update_and_replay_preserve_original_and_correction(self):
        content, first = self.save()
        self.assertEqual(len(first['records']), 2)
        before = self.runtime.current_bundle(content, 'example', '2026-11-16')
        activity, submission = before['events']
        update = self.runtime.prepare_location_update(content, {
            'text': '班会地点改到A202', 'sent_on': '2026-11-16', 'mode': 'example',
            'target_event_id': activity['id']}, NOW)
        self.assertEqual(len(update['updates']), 1)
        changed = apply_plan(content, update)
        replay = self.runtime.prepare_message(changed, MESSAGE, NOW)
        self.assertEqual(replay['records'], [])
        self.assertEqual(replay['updates'], [])
        restored = self.runtime.current_bundle(changed, 'example', '2026-11-16')
        changed_activity, unchanged_submission = restored['events']
        self.assertEqual(changed_activity['location'], 'A202')
        self.assertEqual(unchanged_submission, submission)
        self.assertEqual(changed_activity['source_id'], activity['source_id'])
        self.assertEqual(restored['sources'][0]['text'], MESSAGE['text'])
        history = changed_activity['history']
        self.assertEqual(history[0]['changes']['location'], {'before': 'A201', 'after': 'A202'})
        self.assertEqual(history[0]['source']['text'], '班会地点改到A202')
        self.assertEqual(history[0]['source']['sent_on'], '2026-11-16')
        self.assertEqual(history[0]['source']['ingested_at'], NOW)

    def test_sender_date_completion_updates_existing_ids_without_resetting_location(self):
        missing = dict(MESSAGE, sent_on=None)
        content, first = self.save(missing)
        before = self.runtime.current_bundle(content, 'example', '2026-11-16')
        original_ids = [e['id'] for e in before['events']]
        update = self.runtime.prepare_location_update(content, {
            'text': '班会地点改到A202', 'mode': 'example'}, NOW)
        content = apply_plan(content, update)
        completion = self.runtime.prepare_message(content, MESSAGE, '2026-11-09T10:00:00+08:00')
        self.assertEqual(completion['records'], [])
        self.assertEqual(len(completion['updates']), 2)
        content = apply_plan(content, completion)
        restored = self.runtime.current_bundle(content, 'example', '2026-11-16')
        self.assertEqual([e['id'] for e in restored['events']], original_ids)
        self.assertEqual([e['date'] for e in restored['events']], ['2026-11-17', '2026-11-20'])
        self.assertEqual(restored['events'][0]['location'], 'A202')
        self.assertEqual(restored['events'][0]['pending_fields'], [])
        self.assertEqual(restored['sources'][0]['sent_on'], '2026-11-16')
        self.assertEqual(restored['sources'][0]['ingested_at'], NOW)
        self.assertEqual(restored['questions'], [])
        replay = self.runtime.prepare_message(content, MESSAGE, NOW)
        self.assertEqual(replay['records'] + replay['updates'], [])

    def test_replay_without_sender_date_reuses_known_source_and_corrected_event(self):
        content, _ = self.save()
        update = self.runtime.prepare_location_update(content, {
            'text': '班会地点改到A202', 'mode': 'example'}, NOW)
        content = apply_plan(content, update)
        before = self.runtime.current_bundle(content, 'example', '2026-11-16')
        replay = self.runtime.prepare_message(content, dict(MESSAGE, sent_on=None), NOW)
        self.assertEqual(replay['records'] + replay['updates'], [])
        self.assertEqual(replay['questions'], [])
        content = apply_plan(content, replay)
        completion = self.runtime.prepare_message(content, MESSAGE, NOW)
        self.assertEqual(completion['records'] + completion['updates'], [])
        self.assertEqual(self.runtime.current_bundle(content, 'example', '2026-11-16'), before)

    def test_replay_without_sender_date_requires_disambiguation_for_same_text(self):
        content, _ = self.save()
        for other_date in ('2026-11-30', None):
            with self.subTest(other_date=other_date):
                other = dict(MESSAGE, sent_on=other_date, source_id='other-source')
                both, _ = self.save(other, content)
                with self.assertRaisesRegex(ValueError, '多条同原文来源'):
                    self.runtime.prepare_message(both, dict(MESSAGE, sent_on=None), NOW)

    def test_mixed_message_keeps_event_and_questions_after_snapshot_restore(self):
        message = dict(MESSAGE, text='明天19:00在A201开班会，请大家准时参加，下周一交实验报告')
        content, plan = self.save(message)
        self.assertEqual(len(plan['records']), 1)
        self.assertIn('下周一交实验报告', plan['questions'][0]['question'])
        restored = self.runtime.current_bundle(content, 'example', '2026-11-16')
        self.assertEqual(len(restored['events']), 1)
        self.assertEqual(restored['questions'], plan['questions'])
        self.assertEqual(restored['sources'][0]['text'], message['text'])

    def test_mixed_message_sender_date_question_tracks_only_undated_events(self):
        message = {'mode': 'example', 'text': '2026年11月20日20:00前交作业PDF，本周五18:00前交报告，记得带学生证'}
        content, _ = self.save(message)
        snapshot = self.runtime.current_bundle(content, 'example', '2026-11-16')
        self.assertCountEqual([q['field'] for q in snapshot['questions']], ['sent_on', 'source_excerpt'])
        update = self.runtime.prepare_event_update(content, {
            'mode': 'example', 'kind': 'postpone', 'text': '报告延期至11月22日',
            'target_event_id': snapshot['events'][1]['id'], 'changes': {'date': '2026-11-22'}}, NOW)
        content = apply_plan(content, update)
        restored = self.runtime.current_bundle(content, 'example', '2026-11-16')
        self.assertEqual([q['field'] for q in restored['questions']], ['source_excerpt'])
        self.assertEqual([e['date'] for e in restored['events']], ['2026-11-20', '2026-11-22'])

    def test_modes_and_ambiguous_targets_do_not_change_wrong_event(self):
        content, _ = self.save()
        content, _ = self.save(dict(MESSAGE, sent_on='2026-11-30'), content)
        plan = self.runtime.prepare_location_update(content, {'text':'班会地点改到A202','mode':'example'}, NOW)
        self.assertEqual(plan['updates'], [])
        self.assertEqual(len(plan['candidates']), 2)
        self.assertEqual(self.runtime.current_bundle(content, 'real', '2026-11-16')['events'], [])

    def test_packaged_cli_runs_without_repository_and_propagates_parse_failure(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            shutil.copytree(SCRIPTS, base / 'scripts', ignore=shutil.ignore_patterns('__pycache__'))
            message = base / 'message.json'
            message.write_text(json.dumps(MESSAGE), encoding='utf-8')
            result = subprocess.run([sys.executable, '-X', 'utf8', str(base/'scripts/runtime.py'), 'message',
                                     '--input', str(message), '--out', str(base/'plan.json')],
                                    cwd=base, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(len(json.loads((base/'plan.json').read_text(encoding='utf-8'))['records']), 2)
            message.write_text(json.dumps(dict(MESSAGE,text='无法解析的新句式')),encoding='utf-8')
            failed = subprocess.run([sys.executable, '-X', 'utf8', str(base/'scripts/runtime.py'), 'message',
                                     '--input', str(message), '--out', str(base/'failed.json')],
                                    cwd=base,capture_output=True,text=True)
            self.assertNotEqual(failed.returncode,0)
            self.assertFalse((base/'failed.json').exists())


if __name__ == '__main__':
    unittest.main()
