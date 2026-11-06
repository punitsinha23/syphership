import pytest

from models.project import Project
from services.env_vars import MAX_ENV_VALUE_CHARS, MAX_ENV_VARS
from tests.conftest import TestingSessionLocal


@pytest.fixture
def project_id(client, auth_headers):
    return client.post("/projects/", headers=auth_headers, json={"name": "App"}).json()["id"]


def put_env(client, headers, project_id, variables):
    return client.put(f"/projects/{project_id}/env", headers=headers, json={"variables": variables})


def test_saved_values_are_never_returned(client, auth_headers, project_id):
    response = put_env(client, auth_headers, project_id, {"API_KEY": "very-secret"})

    assert response.json() == {"names": ["API_KEY"]}
    read = client.get(f"/projects/{project_id}/env", headers=auth_headers)
    assert read.json() == {"names": ["API_KEY"]}
    assert "very-secret" not in read.text


def test_values_are_encrypted_in_the_database(client, auth_headers, project_id):
    put_env(client, auth_headers, project_id, {"API_KEY": "very-secret"})

    db = TestingSessionLocal()
    try:
        stored = db.query(Project).filter(Project.id == project_id).one().env_vars
    finally:
        db.close()

    assert "very-secret" not in stored
    assert "API_KEY" not in stored


def test_update_merges_and_null_deletes(client, auth_headers, project_id):
    put_env(client, auth_headers, project_id, {"A": "1", "B": "2"})

    response = put_env(client, auth_headers, project_id, {"B": None, "C": "3"})

    assert response.json() == {"names": ["A", "C"]}


@pytest.mark.parametrize("name", ["1BAD", "HAS SPACE", "A=B", "", "A-B", "A\nB"])
def test_invalid_names_are_rejected(client, auth_headers, project_id, name):
    assert put_env(client, auth_headers, project_id, {name: "x"}).status_code == 422


def test_too_long_value_is_rejected(client, auth_headers, project_id):
    assert put_env(client, auth_headers, project_id, {"A": "x" * (MAX_ENV_VALUE_CHARS + 1)}).status_code == 422


def test_too_many_variables_are_rejected(client, auth_headers, project_id):
    variables = {f"V{i}": "x" for i in range(MAX_ENV_VARS + 1)}

    assert put_env(client, auth_headers, project_id, variables).status_code == 422


def test_other_users_cannot_read_or_change_env_vars(client, auth_headers, user2_headers, project_id):
    assert client.get(f"/projects/{project_id}/env", headers=user2_headers).status_code == 404
    assert put_env(client, user2_headers, project_id, {"A": "1"}).status_code == 404
