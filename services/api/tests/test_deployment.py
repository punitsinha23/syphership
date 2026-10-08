def test_create_deployment(client, auth_headers):
    project_response = client.post(
        "/projects/",
        headers=auth_headers,
        json={
            "name": "Deployment Test Project",
            "description": "Testing deployments"
        }
    )

    project_id = project_response.json()["id"]

    response = client.post(
        "/deployments/",
        headers=auth_headers,
        json={
            "project_id": project_id,
            "commit_sha": "abc123"
        }
    )

    assert response.status_code == 200

    data = response.json()

    assert data["project_id"] == project_id
    assert data["commit_sha"] == "abc123"
    assert data["status"] == "QUEUED"
    assert "id" in data


def test_deployment_status_flow(client, auth_headers):
    project_response = client.post(
        "/projects/",
        headers=auth_headers,
        json={
            "name": "Status Test Project",
            "description": "Testing deployment status"
        }
    )

    project_id = project_response.json()["id"]

    deployment_response = client.post(
        "/deployments/",
        headers=auth_headers,
        json={
            "project_id": project_id,
            "commit_sha": "abc123"
        }
    )

    deployment_id = deployment_response.json()["id"]

    for status in ["BUILDING", "DEPLOYING", "RUNNING"]:
        response = client.patch(
            f"/deployments/{deployment_id}/status",
            headers=auth_headers,
            json={"status": status}
        )

        assert response.status_code == 200
        assert response.json()["status"] == status


def test_invalid_deployment_status_transition(client, auth_headers):
    project_response = client.post(
        "/projects/",
        headers=auth_headers,
        json={
            "name": "Invalid Transition Test",
            "description": "Testing invalid status transition"
        }
    )

    project_id = project_response.json()["id"]

    deployment_response = client.post(
        "/deployments/",
        headers=auth_headers,
        json={
            "project_id": project_id,
            "commit_sha": "abc123"
        }
    )

    deployment_id = deployment_response.json()["id"]

    # Move deployment to RUNNING
    for status in ["BUILDING", "DEPLOYING", "RUNNING"]:
        client.patch(
            f"/deployments/{deployment_id}/status",
            headers=auth_headers,
            json={"status": status}
        )

    # RUNNING → BUILDING should fail
    response = client.patch(
        f"/deployments/{deployment_id}/status",
        headers=auth_headers,
        json={"status": "BUILDING"}
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid deployment status transition"

def test_deployment_can_fail(client, auth_headers):
    project_response = client.post(
        "/projects/",
        headers=auth_headers,
        json={
            "name": "Failed Deployment Test",
            "description": "Testing failed deployments"
        }
    )

    project_id = project_response.json()["id"]

    deployment_response = client.post(
        "/deployments/",
        headers=auth_headers,
        json={
            "project_id": project_id,
            "commit_sha": "abc123"
        }
    )

    deployment_id = deployment_response.json()["id"]

    response = client.patch(
        f"/deployments/{deployment_id}/status",
        headers=auth_headers,
        json={"status": "FAILED", "failure_reason": "Build failed"}
    )

    assert response.status_code == 200
    assert response.json()["status"] == "FAILED"
    assert response.json()["failure_reason"] == "Build failed"

def test_failed_status_requires_failure_reason(client, auth_headers):
    project_response = client.post(
        "/projects/",
        headers=auth_headers,
        json={
            "name": "Missing Failure Reason Test",
            "description": "Testing failure_reason validation"
        }
    )

    project_id = project_response.json()["id"]

    deployment_response = client.post(
        "/deployments/",
        headers=auth_headers,
        json={
            "project_id": project_id,
            "commit_sha": "abc123"
        }
    )

    deployment_id = deployment_response.json()["id"]

    response = client.patch(
        f"/deployments/{deployment_id}/status",
        headers=auth_headers,
        json={"status": "FAILED"}
    )

    assert response.status_code == 422

def test_other_user_cannot_access_deployment(client, auth_headers, user2_headers):
    # User 1 creates a project
    project_response = client.post(
        "/projects/",
        headers=auth_headers,
        json={
            "name": "Private Project",
            "description": "User 1 project"
        }
    )

    project_id = project_response.json()["id"]

    # User 1 creates a deployment
    deployment_response = client.post(
        "/deployments/",
        headers=auth_headers,
        json={
            "project_id": project_id,
            "commit_sha": "abc123"
        }
    )

    deployment_id = deployment_response.json()["id"]

    # Create user 2

    # User 2 tries to access User 1's deployment
    response = client.get(
        f"/deployments/{deployment_id}",
        headers=user2_headers
    )

    assert response.status_code == 404


def test_get_deployments(client, auth_headers):
    project_response = client.post(
        "/projects/",
        headers=auth_headers,
        json={
            "name": "Deployment List Project",
            "description": "Testing deployment history"
        }
    )

    project_id = project_response.json()["id"]

    client.post(
        "/deployments/",
        headers=auth_headers,
        json={
            "project_id": project_id,
            "commit_sha": "abc123"
        }
    )

    response = client.get(
        "/deployments/",
        headers=auth_headers
    )

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["commit_sha"] == "abc123"


def test_other_user_cannot_create_deployment_for_project(
    client,
    auth_headers,
    user2_headers
):
    # User 1 creates a project
    project_response = client.post(
        "/projects/",
        headers=auth_headers,
        json={
            "name": "User 1 Project",
            "description": "Private project"
        }
    )

    project_id = project_response.json()["id"]

    # Create user 2

    response = client.post(
        "/deployments/",
        headers=user2_headers,
        json={
            "project_id": project_id,
            "commit_sha": "abc123"
        }
    )

    assert response.status_code == 404


def test_other_user_cannot_update_deployment(
    client,
    auth_headers,
    user2_headers
):
    # User 1 creates project
    project_response = client.post(
        "/projects/",
        headers=auth_headers,
        json={
            "name": "Private Deployment Project",
            "description": "User 1 project"
        }
    )

    project_id = project_response.json()["id"]

    deployment_response = client.post(
        "/deployments/",
        headers=auth_headers,
        json={
            "project_id": project_id,
            "commit_sha": "abc123"
        }
    )

    deployment_id = deployment_response.json()["id"]

    


    response = client.patch(
        f"/deployments/{deployment_id}/status",
        headers=user2_headers,
        json={"status": "BUILDING"}
    )

    assert response.status_code == 404


def test_deployment_not_found(client, auth_headers):
    response = client.get(
        "/deployments/99999",
        headers=auth_headers
    )

    assert response.status_code == 404