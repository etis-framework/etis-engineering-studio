from fastapi.testclient import TestClient
from apps.api.app.main import app

client=TestClient(app)

def test_health():
    with client:
        r=client.get('/health')
        assert r.status_code==200
        assert r.json()['status']=='ok'

def test_course_endpoint():
    with client:
        r=client.get('/api/v1/course')
        assert r.status_code==200
        assert len(r.json()['phases'])==6
