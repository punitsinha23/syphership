import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base, get_db
from models.user import User
from models.project import Project
from models.deployment import Deployment
from main import app


TEST_DATABASE_URL = "postgresql+psycopg://syphership:1234@localhost:5435/syphership_test"

test_engine = create_engine(TEST_DATABASE_URL)

TestingSessionLocal = sessionmaker(bind=test_engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def client():
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()

@pytest.fixture
def auth_headers(client):
    client.post(
        "/auth/register",
        json={
            "email": "auth@example.com",
            "username": "authuser",
            "password": "password123"
        }
    )

    response = client.post(
        "/auth/login",
        json={
            "email": "auth@example.com",
            "password": "password123"
        }
    )

    token = response.json()["access_token"]

    return {
        "Authorization": f"Bearer {token}"
    }