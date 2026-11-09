"""Run the shared synthetic D fixture and save actual M3 outputs."""

import argparse
from copy import deepcopy
import json
from pathlib import Path

from .presentation import (build_report, find_conflicts, find_free_slots, opening,
                           render_report, suggest_preparation)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out-dir', type=Path, default=Path('work/m3-demo'))
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    fixture = json.loads((root / 'docs/协作/联调样例.json').read_text(encoding='utf-8'))['D']
    bundle = fixture['input_bundle']
    assignment = deepcopy(bundle)
    assignment['sources'].append({'id': 'm3-assignment-source', 'type': 'assignment',
                                  'title': '合成示例作业', 'mode': 'example',
                                  'text': '2026年11月20日20:00前交数据分析作业PDF，预计用时3小时。',
                                  'sent_on': '2026-11-16'})
    assignment['events'].append({'id': 'm3-assignment', 'type': 'submission', 'title': '示例数据分析作业PDF',
                                 'date': '2026-11-20', 'start_time': '20:00', 'end_time': None,
                                 'location': None, 'status': 'not_started', 'pending_fields': [],
                                 'source_id': 'm3-assignment-source',
                                 'source_excerpt': assignment['sources'][-1]['text']})
    results = {'input.json': bundle, 'welcome.md': opening(),
               'week.json': build_report(bundle), 'tonight.json': build_report(bundle, 'tonight'),
               'week-brief.md': render_report(build_report(bundle, 'week-brief')),
               'assignment-input.json': assignment,
               'assignment-preparation.json': suggest_preparation(assignment, 'm3-assignment', 180,
                                                                  '2026-11-17', '2026-11-20', '16:00', '20:00'),
               'conflicts.json': find_conflicts(bundle),
               'free.json': find_free_slots(bundle, '2026-11-17', '2026-11-17', '14:00', '18:00'),
               'preparation.json': suggest_preparation(bundle, 'handoff-b-event-002', 180,
                                                       '2026-11-17', '2026-11-20', '16:00', '20:00')}
    results['week.md'] = render_report(results['week.json'])
    results['tonight.md'] = render_report(results['tonight.json'])
    args.out_dir.mkdir(parents=True, exist_ok=True)
    for name, result in results.items():
        output = result if isinstance(result, str) else json.dumps(result, ensure_ascii=False, indent=2) + '\n'
        (args.out_dir / name).write_text(output, encoding='utf-8')
    print(json.dumps({'synthetic_example': True, 'output': str(args.out_dir),
                      'scheduled': len(results['week.json']['scheduled']),
                      'pending': len(results['week.json']['pending']),
                      'conflicts': len(results['conflicts.json']['conflicts']),
                      'saved_to_cloud': False}, ensure_ascii=False))


if __name__ == '__main__':
    main()
