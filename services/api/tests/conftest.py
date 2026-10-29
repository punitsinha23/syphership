import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base, DATABASE_URL, get_db
from models.user import User
from models.project import Project
from models.deployment import Deployment
from auth.security import create_session_tokens
from main import app


# Same server/credentials as the dev DB, separate "<db>_test" database
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    DATABASE_URL.rsplit("/", 1)[0] + f"/{os.getenv('POSTGRES_DB')}_test",
)

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
def client(monkeypatch):
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()

@pytest.fixture
def make_user():
    def _make_user(email="auth@example.com", username="authuser"):
        db = TestingSessionLocal()
        try:
            user = User(email=email, username=username)
            db.add(user)
            db.commit()
            return user.id
        finally:
            db.close()

    return _make_user


@pytest.fixture
def auth_headers(make_user):
    token = create_session_tokens(make_user())["access_token"]

    return {
        "Authorization": f"Bearer {token}"
    }


@pytest.fixture
def user2_headers(make_user):
    token = create_session_tokens(make_user(email="user2@example.com", username="user2"))["access_token"]

    return {
        "Authorization": f"Bearer {token}"
    }
