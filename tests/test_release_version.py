"""Release consistency and paired-edition integrity, without document dependencies."""
import hashlib
import json
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZipFile

from fastapi.testclient import TestClient
from apps.api.app.main import app
from apps.api.app.version import STUDIO_VERSION

ROOT = Path(__file__).resolve().parents[1]


def test_runtime_version_authority():
    client = TestClient(app)
    assert STUDIO_VERSION == '0.18.0'
    assert app.version == STUDIO_VERSION
    assert client.get('/health').json()['version'] == STUDIO_VERSION
    assert client.get('/openapi.json').json()['info']['version'] == STUDIO_VERSION


def test_current_release_metadata_and_manual_pairs():
    edition = json.loads((ROOT / 'docs/manuals/edition.json').read_text())
    assert edition['version'] == STUDIO_VERSION
    assert edition['status'] == 'release'
    assert len(edition['manuals']) == 12
    actual = {p.name for p in (ROOT / 'docs/manuals').glob('*.docx')}
    assert {m['docx'] for m in edition['manuals']} == actual
    assert len({m['id'] for m in edition['manuals']}) == 12
    for manual in edition['manuals']:
        for fmt in ('docx', 'pdf'):
            path = ROOT / 'docs/manuals' / manual[fmt]
            data = path.read_bytes()
            assert hashlib.sha256(data).hexdigest() == manual[f'{fmt}_sha256'], path
        with ZipFile(ROOT / 'docs/manuals' / manual['docx']) as archive:
            body = ET.fromstring(archive.read('word/document.xml'))
            text = ' '.join(body.itertext())
            assert f'v{STUDIO_VERSION}' in text
            assert 'release manual edition' in text.lower()
            core = ET.fromstring(archive.read('docProps/core.xml'))
            assert f'v{STUDIO_VERSION}' in ' '.join(core.itertext())
        assert manual['pages'] > 0
        assert manual['pdf'].replace('.pdf', '.docx') == manual['docx']
        assert (ROOT / 'docs/manuals' / manual['pdf']).read_bytes().startswith(b'%PDF-')
    assert f'version: "{STUDIO_VERSION}"' in (ROOT / 'CITATION.cff').read_text()
    for rel in ['README.md', 'CHANGELOG.md', 'docs/README.md', 'docs/manuals/README.md',
                f'docs/releases/v{STUDIO_VERSION}.md']:
        assert f'v{STUDIO_VERSION}' in (ROOT / rel).read_text()
