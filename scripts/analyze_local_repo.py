#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from apps.api.app.services.repository_intelligence import analyze_local_repository

parser = argparse.ArgumentParser(description='Run ETIS phase-aware repository intelligence against a local checkout.')
parser.add_argument('repository', type=Path)
parser.add_argument('--phase', default='A1', choices=[f'A{i}' for i in range(1,7)])
args = parser.parse_args()
result = analyze_local_repository(args.repository.resolve(), args.phase)
print(json.dumps(result, indent=2))
