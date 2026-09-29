def test_projects_requires_auth(client):
    response = client.get("/projects/")

    assert response.status_code == 401

def test_projects_authenticated(client, auth_headers):
    response = client.get(
        "/projects/",
        headers=auth_headers
    )

    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_create_project(client, auth_headers):
    response = client.post(
        "/projects/",
        headers=auth_headers,
        json={
            "name": "Test Project",
            "description": "Project for testing"
        }
    )

    assert response.status_code == 200

    data = response.json()
    assert data["name"] == "Test Project"
    assert data["description"] == "Project for testing"
    assert "id" in data

def test_get_projects(client, auth_headers):
    client.post(
        "/projects/",
        headers=auth_headers,
        json={
            "name": "Project One",
            "description": "First project"
        }
    )

    response = client.get(
        "/projects/",
        headers=auth_headers
    )

    assert response.status_code == 200

    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "Project One"

def test_get_project(client, auth_headers):
    create_response = client.post(
        "/projects/",
        headers=auth_headers,
        json={
            "name": "Specific Project",
            "description": "Testing get by ID"
        }
    )

    project_id = create_response.json()["id"]

    response = client.get(
        f"/projects/{project_id}",
        headers=auth_headers
    )

    assert response.status_code == 200
    assert response.json()["id"] == project_id

def test_update_project(client, auth_headers):
    create_response = client.post(
        "/projects/",
        headers=auth_headers,
        json={
            "name": "Old Name",
            "description": "Old description"
        }
    )

    project_id = create_response.json()["id"]

    response = client.put(
        f"/projects/{project_id}",
        headers=auth_headers,
        json={
            "name": "New Name",
            "description": "New description"
        }
    )

    assert response.status_code == 200
    assert response.json()["name"] == "New Name"
    assert response.json()["description"] == "New description"

def test_delete_project(client, auth_headers):
    create_response = client.post(
        "/projects/",
        headers=auth_headers,
        json={
            "name": "Delete Me",
            "description": "Testing deletion"
        }
    )

    project_id = create_response.json()["id"]

    response = client.delete(
        f"/projects/{project_id}",
        headers=auth_headers
    )

    assert response.status_code == 200

    get_response = client.get(
        f"/projects/{project_id}",
        headers=auth_headers
    )

    assert get_response.status_code == 404

def test_user_cannot_access_other_users_project(client, auth_headers):
    response = client.post(
        "/projects/",
        headers=auth_headers,
        json={
            "name": "Private Project",
            "description": "User 1 project"
        }
    )

    project_id = response.json()["id"]

    client.post(
        "/auth/register",
        json={
            "email": "user2@example.com",
            "username": "user2",
            "password": "password123"
        }
    )

    login = client.post(
        "/auth/login",
        json={
            "email": "user2@example.com",
            "password": "password123"
        }
    )

    user2_headers = {
        "Authorization": f"Bearer {login.json()['access_token']}"
    }

    response = client.get(
        f"/projects/{project_id}",
        headers=user2_headers
    )

    assert response.status_code == 404


def test_user_cannot_update_other_users_project(client, auth_headers):
    response = client.post(
        "/projects/",
        headers=auth_headers,
        json={
            "name": "Private Project",
            "description": "User 1 project"
        }
    )

    project_id = response.json()["id"]

    client.post(
        "/auth/register",
        json={
            "email": "user2@example.com",
            "username": "user2",
            "password": "password123"
        }
    )

    login = client.post(
        "/auth/login",
        json={
            "email": "user2@example.com",
            "password": "password123"
        }
    )

    user2_headers = {
        "Authorization": f"Bearer {login.json()['access_token']}"
    }

    response = client.put(
        f"/projects/{project_id}",
        headers=user2_headers,
        json={
            "name": "Hacked Project",
            "description": "Changes"
        }
    )

    assert response.status_code == 404



def other_user_cannot_delete_other_user_project(client, auth_headers ):
    response = client.post(
        "/projects/",
        headers=auth_headers,
        json={
            "name": "Private project",
            "description": "User 1 project"
        }
    )

    project_id = response.json()["id"]

    response = client.post(
        "/auth/register",
        json={
            "email": "user2@example.com",
            "username": "User2",
            "password": "password123",
        }
    )

    response = client.post(
        "/auth/login",
        json={
            "email": "user2@example.com",
            "password": "password123",
        }
    )

    user2_headers = {
        "Authorization" : f"Bearer {response.json()['access_token']}"
    }


    response = client.delete(
        f"/projects/{project_id}",
        headers=user2_headers,
    )

    assert response.status_code == 404

