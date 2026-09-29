def test_register(client):
    response = client.post(
        "/auth/register",
        json={
            "email": "test@example.com",
            "username": "testuser",
            "password": "password123"
        }
    )
    print(response.json())
    assert response.status_code == 200

def test_login(client):
    response = client.post(
        "/auth/register",
        json={
            "email": "login@example.com",
            "username": "loginuser",
            "password": "password123"
        }
    )
    response = client.post(
        "/auth/login",
        json={
            "email": "login@example.com",
            "password": "password123"
        }
    )

    assert response.status_code == 200

    data = response.json()

    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"

def test_login_wrong_password(client):
    client.post(
        "/auth/register",
        json={
            "email": "wrong@example.com",
            "username": "wronguser",
            "password": "password123"
        }
    )

    response = client.post(
        "/auth/login",
        json={
            "email": "wrong@example.com",
            "password": "wrongpassword"
        }
    )

    assert response.status_code == 401

def test_duplicate_registration(client):
    payload = {
        "email": "duplicate@example.com",
        "username": "duplicateuser",
        "password": "password123"
    }

    first = client.post("/auth/register", json=payload)
    second = client.post("/auth/register", json=payload)

    assert first.status_code == 200
    assert second.status_code == 400
