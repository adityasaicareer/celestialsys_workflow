import asyncio
from datetime import date, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import main


@pytest.fixture
def client(tmp_path, monkeypatch):
    """Provide an isolated FastAPI client backed by a temporary SQLite database."""
    database_file = Path(tmp_path) / "test.db"
    test_engine = create_async_engine(
        f"sqlite+aiosqlite:///{database_file}",
        echo=False,
    )
    test_session_local = async_sessionmaker(test_engine, expire_on_commit=False)

    original_engine = main.engine
    original_session_local = main.SessionLocal
    main.engine = test_engine
    main.SessionLocal = test_session_local

    try:
        with TestClient(main.app) as test_client:
            yield test_client
    finally:
        async def cleanup():
            async with test_engine.begin() as connection:
                await connection.run_sync(main.Base.metadata.drop_all)
            await test_engine.dispose()

        asyncio.run(cleanup())
        main.engine = original_engine
        main.SessionLocal = original_session_local


@pytest.fixture
def superadmin_token(client):
    response = client.post(
        "/auth/login",
        json={
            "email": "superadmin@example.com",
            "password": "ChangeMe123!",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    return body["access_token"]


def register_user(client, email="user@example.com", full_name="Test User"):
    response = client.post(
        "/auth/register",
        json={
            "email": email,
            "full_name": full_name,
            "password": "Password123!",
            "organization": "Example Org",
            "location": "WTC",
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["email"] == email.lower()
    assert body["active"] is False
    assert body["role"] == "user"
    return body


def activate_user(client, user_id, superadmin_token, role="user"):
    response = client.patch(
        f"/users/{user_id}",
        headers={"Authorization": f"Bearer {superadmin_token}"},
        json={"active": True, "role": role},
    )
    assert response.status_code == 200
    assert response.json()["active"] is True
    assert response.json()["role"] == role
    return response.json()


def login(client, email, password="Password123!"):
    response = client.post(
        "/auth/login",
        json={"email": email, "password": password},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def visitor_payload(approver_id=None):
    payload = {
        "identity": "Jane Visitor",
        "phone": "+919876543210",
        "email": "jane.visitor@example.com",
        "pass_type": "Day Pass",
        "start_date": date.today().isoformat(),
        "end_date": (date.today() + timedelta(days=1)).isoformat(),
        "origin": "External Partner",
        "visitee": "Facilities Team",
        "location": "WTC",
        "consent": True,
        "id_proof": "passport-123",
        "photo_data": "data:image/png;base64,abcdefghijklmnop",
        "access_card": {"number": "CARD-001"},
        "device_certificate": {"serial": "DEVICE-001"},
        "internet_access_requested": True,
    }
    if approver_id is not None:
        payload["approver_id"] = approver_id
    return payload


def test_login_requires_authentication_and_rejects_invalid_credentials(client):
    missing = client.get("/users")
    assert missing.status_code == 401
    assert missing.json()["detail"] == "Authentication required"

    invalid_token = client.get(
        "/dashboard/statistics",
        headers={"Authorization": "Bearer invalid.token"},
    )
    assert invalid_token.status_code == 401
    assert invalid_token.json()["detail"] == "Invalid or expired token"

    invalid_login = client.post(
        "/auth/login",
        json={"email": "nobody@example.com", "password": "WrongPass123!"},
    )
    assert invalid_login.status_code == 401
    assert invalid_login.json()["detail"] == "Invalid credentials"


def test_register_duplicate_and_pending_login(client):
    register_user(client)

    duplicate = client.post(
        "/auth/register",
        json={
            "email": "USER@example.com",
            "full_name": "Another User",
            "password": "Password123!",
        },
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["detail"] == "Email already registered"

    pending_login = client.post(
        "/auth/login",
        json={"email": "user@example.com", "password": "Password123!"},
    )
    assert pending_login.status_code == 403
    assert pending_login.json()["detail"] == "User approval is pending"


def test_superadmin_can_list_update_and_delete_users(client, superadmin_token):
    user = register_user(client)
    headers = {"Authorization": f"Bearer {superadmin_token}"}

    listed = client.get("/users", headers=headers)
    assert listed.status_code == 200
    assert isinstance(listed.json(), list)
    assert any(item["id"] == user["id"] for item in listed.json())

    updated = client.patch(
        f"/users/{user['id']}",
        headers=headers,
        json={"full_name": "Updated User", "active": True, "role": "admin"},
    )
    assert updated.status_code == 200
    assert updated.json()["full_name"] == "Updated User"
    assert updated.json()["role"] == "admin"
    assert updated.json()["active"] is True

    deleted = client.delete(f"/users/{user['id']}", headers=headers)
    assert deleted.status_code == 204
    assert deleted.content == b""

    missing = client.get(f"/visitors/999999", headers=headers)
    assert missing.status_code == 404
    assert missing.json()["detail"] == "Visitor not found"


def test_user_cannot_access_admin_endpoints(client):
    user = register_user(client)
    activate_user(client, user["id"], login(client, "superadmin@example.com", "ChangeMe123!"))
    user_token = login(client, "user@example.com")
    headers = {"Authorization": f"Bearer {user_token}"}

    response = client.get("/users", headers=headers)
    assert response.status_code == 403
    assert response.json()["detail"] == "Insufficient permissions"

    report = client.get("/reports/visitors.pdf", headers=headers)
    assert report.status_code == 403


def test_visitor_validation_and_full_approval_checkin_checkout_flow(client, superadmin_token):
    user = register_user(client)
    activate_user(client, user["id"], superadmin_token)
    user_token = login(client, "user@example.com")
    user_headers = {"Authorization": f"Bearer {user_token}"}
    admin_headers = {"Authorization": f"Bearer {superadmin_token}"}

    no_approver = client.post(
        "/visitors",
        headers=user_headers,
        json=visitor_payload(),
    )
    assert no_approver.status_code == 422
    assert "approver" in no_approver.json()["detail"]

    invalid_visitor = visitor_payload(approver_id=1)
    invalid_visitor["consent"] = False
    invalid = client.post("/visitors", headers=user_headers, json=invalid_visitor)
    assert invalid.status_code == 422
    assert invalid.json()["detail"] == "Visitor consent is mandatory"

    created = client.post(
        "/visitors",
        headers=user_headers,
        json=visitor_payload(approver_id=1),
    )
    assert created.status_code == 201
    visitor = created.json()
    visitor_id = visitor["id"]
    assert visitor["status"] == "waiting_for_approval"
    assert visitor["submitted_by"] == user["id"]
    assert visitor["internet_access_requested"] is True

    filtered = client.get(
        "/visitors",
        headers=user_headers,
        params={"status": "waiting_for_approval", "location": "WTC", "limit": 10},
    )
    assert filtered.status_code == 200
    assert any(item["id"] == visitor_id for item in filtered.json())

    rejected = client.post(
        f"/visitors/{visitor_id}/approval",
        headers=admin_headers,
        json={"approved": False},
    )
    assert rejected.status_code == 422
    assert "rejection reason" in rejected.json()["detail"]

    rejected = client.post(
        f"/visitors/{visitor_id}/approval",
        headers=admin_headers,
        json={"approved": False, "rejection_reason": "Use a valid ID proof"},
    )
    assert rejected.status_code == 200
    assert rejected.json()["status"] == "rejected"
    assert rejected.json()["rejection_reason"] == "Use a valid ID proof"

    revised_payload = visitor_payload(approver_id=1)
    revised_payload["id_proof"] = "passport-456"
    revised = client.put(
        f"/visitors/{visitor_id}",
        headers=user_headers,
        json=revised_payload,
    )
    assert revised.status_code == 200
    assert revised.json()["status"] == "waiting_for_approval"
    assert revised.json()["rejection_reason"] is None
    assert revised.json()["id_proof"] == "passport-456"

    approved = client.post(
        f"/visitors/{visitor_id}/approval",
        headers=admin_headers,
        json={"approved": True},
    )
    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"
    assert approved.json()["approver_id"] == 1

    checked_in = client.post(
        f"/visitors/{visitor_id}/check-in",
        headers=user_headers,
    )
    assert checked_in.status_code == 200
    assert checked_in.json()["checked_in_at"] is not None

    checked_in_again = client.post(
        f"/visitors/{visitor_id}/check-in",
        headers=user_headers,
    )
    assert checked_in_again.status_code == 409

    checked_out = client.post(
        f"/visitors/{visitor_id}/check-out",
        headers=user_headers,
    )
    assert checked_out.status_code == 200
    assert checked_out.json()["checked_out_at"] is not None

    checked_out_again = client.post(
        f"/visitors/{visitor_id}/check-out",
        headers=user_headers,
    )
    assert checked_out_again.status_code == 409


def test_dashboard_preferences_and_reports(client, superadmin_token):
    headers = {"Authorization": f"Bearer {superadmin_token}"}

    statistics = client.get("/dashboard/statistics", headers=headers)
    assert statistics.status_code == 200
    body = statistics.json()
    assert set(body) == {"totals", "recent_activity"}
    assert isinstance(body["totals"], dict)
    assert isinstance(body["recent_activity"], list)

    preferences = client.put(
        "/notifications/preferences",
        headers=headers,
        json={"muted": True, "internet_requests": False},
    )
    assert preferences.status_code == 200
    assert preferences.json() == {"muted": True, "internet_requests": False}

    excel = client.get("/reports/visitors.xlsx", headers=headers)
    assert excel.status_code == 200
    assert excel.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    assert excel.content[:2] == b"PK"
    assert "visitors.xlsx" in excel.headers["content-disposition"]

    pdf = client.get("/reports/visitors.pdf", headers=headers)
    assert pdf.status_code == 200
    assert pdf.headers["content-type"] == "application/pdf"
    assert pdf.content.startswith(b"%PDF")
    assert "visitors.pdf" in pdf.headers["content-disposition"]


def test_request_password_reset_has_non_enumerating_response(client):
    response = client.post(
        "/auth/password-reset/request",
        json={"email": "unknown@example.com"},
    )
    assert response.status_code == 200
    assert response.json() == {
        "message": "If the account exists, reset instructions were sent"
    }


def test_validation_errors_and_not_found_responses(client, superadmin_token):
    headers = {"Authorization": f"Bearer {superadmin_token}"}

    malformed_registration = client.post(
        "/auth/register",
        json={"email": "not-an-email", "full_name": "A", "password": "short"},
    )
    assert malformed_registration.status_code == 422
    assert isinstance(malformed_registration.json()["detail"], list)

    missing_user = client.patch(
        "/users/999999",
        headers=headers,
        json={"full_name": "Nobody"},
    )
    assert missing_user.status_code == 404
    assert missing_user.json()["detail"] == "User not found"

    missing_visitor = client.post(
        "/visitors/999999/approval",
        headers=headers,
        json={"approved": True},
    )
    assert missing_visitor.status_code == 404
    assert missing_visitor.json()["detail"] == "Visitor not found"


def test_options_request_does_not_break_middleware_pipeline(client):
    response = client.options(
        "/auth/login",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert response.status_code in {200, 204, 405}
    assert response.headers.get("content-type") is not None or response.status_code == 204
