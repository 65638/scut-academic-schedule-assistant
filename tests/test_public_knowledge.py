import importlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / 'platform/scut-schedule/skills/scut-schedule'


class PublicKnowledgeTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue((SKILL / 'scripts/knowledge_runtime.py').is_file(),
                        'Packaged public knowledge entry is missing')
        sys.path.insert(0, str(SKILL / 'scripts'))
        self.addCleanup(sys.path.remove, str(SKILL / 'scripts'))
        self.knowledge = importlib.import_module('knowledge_runtime')

    def test_notice_search_and_read_preserve_exact_excerpt_and_collection_time(self):
        results = self.knowledge.search_public('求职 补贴')
        self.assertEqual(len(results), 1)
        fixture = json.loads((ROOT / 'modules/m2/fixtures/real_job_subsidy.json').read_text(encoding='utf-8'))
        found = self.knowledge.read_public(results[0]['id'])
        self.assertEqual(found['source'], fixture['source'])
        self.assertEqual(found['ingested_at'], fixture['source']['ingested_at'])
        self.assertEqual(found['url'], fixture['source']['url'])
        self.assertIn('整理摘要', found['document'])
        self.assertIn('正文节选', found['source']['text_scope'])

    def test_timetable_search_reads_content_without_inventing_original_notice(self):
        results = self.knowledge.search_public('第5节')
        self.assertEqual([r['id'] for r in results], ['scut-jw-schedule-university-town'])
        found = self.knowledge.read_public(results[0]['id'])
        self.assertIn('| 第5节 | 14:00 | 14:45 |', found['document'])
        self.assertIsNone(found['published_on'])
        self.assertIsNone(found['source'])
        self.assertEqual(found['content_kind'], '整理资料')

    def test_missing_source_and_no_match_are_explicit(self):
        self.assertEqual(self.knowledge.search_public('不存在的助教通知'), [])
        with self.assertRaisesRegex(ValueError, '没有该公开来源'):
            self.knowledge.read_public('handoff-c-notice-001')
        with self.assertRaisesRegex(ValueError, '关键词'):
            self.knowledge.search_public('  ')

    def test_cli_runs_from_copied_skill_without_repository(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / 'skill'
            shutil.copytree(SKILL, target, ignore=shutil.ignore_patterns('__pycache__'))
            output = Path(folder) / 'search.json'
            result = subprocess.run([sys.executable, '-B', '-X', 'utf8',
                str(target / 'scripts/knowledge_runtime.py'), 'search',
                '--query', '校历', '--out', str(output)],
                cwd=folder, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            data = json.loads(output.read_text(encoding='utf-8'))
            self.assertEqual(data['results'][0]['id'], 'scut-jw-calendar-2026-2027-1')


if __name__ == '__main__':
    unittest.main()
