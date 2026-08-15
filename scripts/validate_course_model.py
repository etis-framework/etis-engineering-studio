import json
from pathlib import Path
root=Path(__file__).resolve().parents[1]
course=json.loads((root/'course-model/course.json').read_text())
phases=json.loads((root/'course-model/phases.json').read_text())
assert len(phases)==6
assert [p['id'] for p in phases]==['A1','A2','A3','A4','A5','A6']
for p in phases:
    assert p['gate_question'] and p['expected_evidence'] and p['active_agents']
for p in phases[:2]:
    assert len(p['scenario_library'])>=4
    assert len(p['decisions_to_defend'])>=6
print('course model valid')
