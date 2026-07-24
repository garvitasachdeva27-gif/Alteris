"""
Alteris backend test suite.

Run with: pytest test_alteris.py -v

These tests use a SEPARATE test database (test_alteris.db) so running
tests never touches your real development data.
"""
import os
os.environ["GROQ_API_KEY"] = "test-key-not-real"
os.environ["JWT_SECRET_KEY"] = "test-secret-key-for-pytest-only"

import pytest
from fastapi.testclient import TestClient

import database
database.DATABASE_NAME = "test_alteris.db"  # isolate test data from real data

from main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_database():
    """Runs before EVERY test: wipe and recreate tables for a clean slate."""
    if os.path.exists("test_alteris.db"):
        os.remove("test_alteris.db")
    database.init_db()
    yield
    if os.path.exists("test_alteris.db"):
        os.remove("test_alteris.db")


def get_auth_headers(email="test@alteris.com", password="testpass123"):
    """Helper: signs up a fresh user and returns ready-to-use auth headers."""
    res = client.post("/auth/signup", json={"email": email, "password": password})
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# ---------- Health check ----------

def test_health_check():
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}


# ---------- Authentication ----------

def test_signup_creates_user_and_returns_token():
    res = client.post("/auth/signup", json={"email": "new@alteris.com", "password": "securepass"})
    assert res.status_code == 200
    assert "access_token" in res.json()


def test_signup_rejects_duplicate_email():
    client.post("/auth/signup", json={"email": "dupe@alteris.com", "password": "pass12345"})
    res = client.post("/auth/signup", json={"email": "dupe@alteris.com", "password": "otherpass"})
    assert res.status_code == 400


def test_login_succeeds_with_correct_credentials():
    client.post("/auth/signup", json={"email": "login@alteris.com", "password": "mypassword"})
    res = client.post("/auth/login", json={"email": "login@alteris.com", "password": "mypassword"})
    assert res.status_code == 200
    assert "access_token" in res.json()


def test_login_rejects_wrong_password():
    client.post("/auth/signup", json={"email": "wrong@alteris.com", "password": "correctpass"})
    res = client.post("/auth/login", json={"email": "wrong@alteris.com", "password": "wrongpass"})
    assert res.status_code == 401


def test_protected_route_rejects_missing_token():
    res = client.get("/prompts")
    assert res.status_code == 401


def test_protected_route_rejects_garbage_token():
    res = client.get("/prompts", headers={"Authorization": "Bearer not-a-real-token"})
    assert res.status_code == 401


# ---------- Prompt CRUD ----------

def test_create_and_list_prompt():
    headers = get_auth_headers()
    create_res = client.post(
        "/prompts",
        json={"title": "Test Prompt", "content": "You are a helpful assistant.", "category": "General"},
        headers=headers,
    )
    assert create_res.status_code == 200
    assert create_res.json()["title"] == "Test Prompt"

    list_res = client.get("/prompts", headers=headers)
    assert list_res.status_code == 200
    assert len(list_res.json()) == 1


def test_update_prompt():
    headers = get_auth_headers()
    created = client.post(
        "/prompts", json={"title": "Original", "content": "Original content"}, headers=headers
    ).json()

    update_res = client.put(
        f"/prompts/{created['id']}", json={"title": "Updated Title"}, headers=headers
    )
    assert update_res.status_code == 200
    assert update_res.json()["title"] == "Updated Title"
    assert update_res.json()["content"] == "Original content"  # unchanged field preserved


def test_delete_prompt():
    headers = get_auth_headers()
    created = client.post("/prompts", json={"title": "To Delete", "content": "..."}, headers=headers).json()

    delete_res = client.delete(f"/prompts/{created['id']}", headers=headers)
    assert delete_res.status_code == 200

    get_res = client.get(f"/prompts/{created['id']}", headers=headers)
    assert get_res.status_code == 404


# ---------- Ownership isolation (the most important security test) ----------

def test_user_cannot_access_another_users_prompt():
    """
    This is the critical test: User A's prompts must be completely
    invisible to User B, even if User B knows the exact prompt ID.
    """
    headers_a = get_auth_headers(email="usera@alteris.com", password="passwordA")
    headers_b = get_auth_headers(email="userb@alteris.com", password="passwordB")

    prompt = client.post(
        "/prompts", json={"title": "User A's Secret Prompt", "content": "Private content"}, headers=headers_a
    ).json()

    # User B tries to read User A's prompt directly by ID
    res = client.get(f"/prompts/{prompt['id']}", headers=headers_b)
    assert res.status_code == 404  # not 403 -- see note in prompts.py on why

    # User B tries to delete it too
    delete_res = client.delete(f"/prompts/{prompt['id']}", headers=headers_b)
    assert delete_res.status_code == 404

    # Confirm it's untouched from User A's perspective
    still_there = client.get(f"/prompts/{prompt['id']}", headers=headers_a)
    assert still_there.status_code == 200


def test_prompt_list_only_shows_own_prompts():
    headers_a = get_auth_headers(email="listera@alteris.com", password="passwordA")
    headers_b = get_auth_headers(email="listerb@alteris.com", password="passwordB")

    client.post("/prompts", json={"title": "A's prompt", "content": "..."}, headers=headers_a)
    client.post("/prompts", json={"title": "B's prompt 1", "content": "..."}, headers=headers_b)
    client.post("/prompts", json={"title": "B's prompt 2", "content": "..."}, headers=headers_b)

    list_a = client.get("/prompts", headers=headers_a).json()
    list_b = client.get("/prompts", headers=headers_b).json()

    assert len(list_a) == 1
    assert len(list_b) == 2


# ---------- Versions ----------

def test_create_and_revert_version():
    headers = get_auth_headers()
    prompt = client.post(
        "/prompts", json={"title": "V1 Title", "content": "Version 1 content"}, headers=headers
    ).json()

    # Snapshot v1
    v1 = client.post(f"/prompts/{prompt['id']}/versions", json={"note": "first save"}, headers=headers).json()
    assert v1["version_number"] == 1

    # Change the live prompt
    client.put(f"/prompts/{prompt['id']}", json={"content": "Version 2 content"}, headers=headers)

    # Revert back to v1
    revert_res = client.post(f"/prompts/{prompt['id']}/versions/{v1['id']}/revert", headers=headers)
    assert revert_res.status_code == 200

    live = client.get(f"/prompts/{prompt['id']}", headers=headers).json()
    assert live["content"] == "Version 1 content"


def test_versions_increment_correctly():
    headers = get_auth_headers()
    prompt = client.post("/prompts", json={"title": "P", "content": "C1"}, headers=headers).json()

    v1 = client.post(f"/prompts/{prompt['id']}/versions", json={}, headers=headers).json()
    v2 = client.post(f"/prompts/{prompt['id']}/versions", json={}, headers=headers).json()

    assert v1["version_number"] == 1
    assert v2["version_number"] == 2


# ---------- Input validation ----------

def test_signup_rejects_invalid_email():
    res = client.post("/auth/signup", json={"email": "not-an-email", "password": "password123"})
    assert res.status_code == 422  # Pydantic validation error


def test_create_prompt_requires_title_and_content():
    headers = get_auth_headers()
    res = client.post("/prompts", json={"title": "Only title"}, headers=headers)
    assert res.status_code == 422
