from fastapi.testclient import TestClient

from apps.api.app.main import app


client = TestClient(app)


def _create_setup_term(namespace: str) -> int:
    response = client.post(
        "/api/v1/admin/terms",
        json={
            "namespace": namespace,
            "term_label": "Gate 12 Lifecycle Test",
            "starts_on": "2027-01-10",
            "ends_on": "2027-05-10",
            "course_code": "COMP 330",
        },
    )
    assert response.status_code == 200
    return response.json()["id"]


def _set_status(term_id: int, status: str):
    return client.put(
        f"/api/v1/admin/terms/{term_id}/status?status={status}"
    )


def test_setup_term_can_transition_to_active():
    term_id = _create_setup_term("COMP330-G12-SETUP-ACTIVE")

    response = _set_status(term_id, "active")

    assert response.status_code == 200
    assert response.json()["status"] == "active"


def test_active_term_cannot_transition_backward_to_setup():
    term_id = _create_setup_term("COMP330-G12-NO-BACKWARD")
    assert _set_status(term_id, "active").status_code == 200

    response = _set_status(term_id, "setup")

    assert response.status_code == 409


def test_active_term_can_transition_to_archived():
    term_id = _create_setup_term("COMP330-G12-ACTIVE-ARCHIVE")
    assert _set_status(term_id, "active").status_code == 200

    response = _set_status(term_id, "archived")

    assert response.status_code == 200
    assert response.json()["status"] == "archived"


def test_archived_term_cannot_be_reactivated():
    term_id = _create_setup_term("COMP330-G12-NO-RESURRECT")
    assert _set_status(term_id, "active").status_code == 200
    assert _set_status(term_id, "archived").status_code == 200

    response = _set_status(term_id, "active")

    assert response.status_code == 409
