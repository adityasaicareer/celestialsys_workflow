import asyncio
import base64
import hashlib
import hmac
import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
import sys

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

sys.path.insert(0, str(Path(__file__).parent.parent))

import main
from main import (
    ApprovalRequest,
    Base,
    Role,
    User,
    UserCreate,
    VisitorCreate,
    VisitStatus,
    app,
    create_token,
    decode_token,
    get_db,
    hash_password,
    validate_visitor,
    verify_password,
)


TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"
test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = async_sessionmaker(test_engine, expire_on_commit=False)


async def override_get_db():
    async with TestingSessionLocal() as session:
        yield session


app.dependency_overrides[get_db] = override_get_db
# Prevent the application startup handler from creating and seeding the production database.
app.router.on_startup.clear()
client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_database():
    async def setup():
        async with test_engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

    async def teardown():
        async with test_engine.begin() as connection:
            await connection.run_sync(Base.metadata.drop_all)

    asyncio.run(setup())
    yield
    asyncio.run(teardown())


@pytest.fixture
def users():
    async def create_users():
        async with TestingSessionLocal() as db:
            super_admin = User(
                email="super@example.com",
                full_name="Super Administrator",
                password_hash=hash_password("SuperPass123"),
                role=Role.SUPER_ADMIN.value,
                active=True,
                location="WTC",
            )
            admin = User(
                email="admin@example.com",
                full_name="Location Admin",
                password_hash=hash_password("AdminPass123"),
                role=Role.ADMIN.value,
                active=True,
                location="WTC",
            )
            user = User(
                email="user@example.com",
                full_name="Regular User",
                password_hash=hash_password("UserPass123"),
                role=Role.USER.value,
                active=True,
                location="WTC",
            )
            pending = User(
                email="pending@example.com",
                full_name="Pending User",
                password_hash=hash_password("Pending123"),
                role=Role.USER.value,
                active=False,
                location="WTC",
            )
            db.add_all([super_admin, admin, user, pending])
            await db.commit()
            for item in [super_admin, admin, user, pending]:
                await db.refresh(item)
            return {
                "super": super_admin,
                "admin": admin,
                "user": user,
                "pending": pending,
            }

    return asyncio.run(create_users())


def auth_headers(user):
    return {"Authorization": f"Bearer {create_token(user)}"}


def visitor_payload(**overrides):
    payload = {
        "identity": "Jane Visitor",
        "phone": "9876543210",
        "email": "jane.visitor@example.com",
        "pass_type": "Day Pass",
        "start_date": date.today().isoformat(),
        "end_date": (date.today() + timedelta(days=2)).isoformat(),
        "origin": "Acme Corporation",
        "visitee": "John Employee",
        "approver_id": 1,
        "location": "WTC",
        "consent": True,
        "id_proof": "passport.pdf",
        "photo_data": "data:image/png;base64," + ("a" * 30),
        "access_card": {"number": "A-1"},
        "device_certificate": {"serial": "device-1"},
        "internet_access_requested": True,
    }
    payload.update(overrides)
    return payload


def test_password_hash_and_verify():
    password = "CorrectHorseBatteryStaple"
    encoded = hash_password(password)

    assert encoded != password
    assert verify_password(password, encoded) is True
    assert verify_password("wrong-password", encoded) is False
    assert verify_password(password, "not-valid-base64") is False
    assert verify_password(password, "") is False


def test_token_creation_and_decoding(users):
    token = create_token(users["user"], minutes=5)
    payload = decode_token(token)

    assert payload["sub"] == users["user"].id
    assert payload["role"] == Role.USER.value
    assert payload["exp"] > int(datetime.now(timezone.utc).timestamp())


def test_decode_token_rejects_bad_signature_and_malformed_tokens():
    with pytest.raises(HTTPException) as bad_signature:
        decode_token("abc.invalid")
    assert bad_signature.value.status_code == 401

    for token in ["", "one", "a.b.c", "%%% .signature"]:
        with pytest.raises(HTTPException) as error:
            decode_token(token)
        assert error.value.status_code == 401


def test_decode_token_rejects_expired_token(monkeypatch, users):
    expired = create_token(users["user"], minutes=-1)
    with pytest.raises(HTTPException) as error:
        decode_token(expired)
    assert error.value.status_code == 401


def test_register_creates_inactive_user():
    response = client.post(
        "/auth/register",
        json={
            "email": "New.User@Example.com",
            "full_name": "New User",
            "password": "NewPassword123",
            "organization": "Example Org",
            "location": "Noida",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "new.user@example.com"
    assert body["active"] is False
    assert body["role"] == "user"
    assert "password_hash" not in body


def test_register_rejects_duplicate_email(users):
    response = client.post(
        "/auth/register",
        json={
            "email": "USER@example.com",
            "full_name": "Another User",
            "password": "AnotherPassword123",
        },
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "Email already registered"


@pytest.mark.parametrize(
    "email,password,expected_status,detail",
    [
        ("user@example.com", "UserPass123", 200, None),
        ("user@example.com", "wrongpass", 401, "Invalid credentials"),
        ("missing@example.com", "UserPass123", 401, "Invalid credentials"),
        ("pending@example.com", "Pending123", 403, "User approval is pending"),
    ],
)
def test_login_cases(users, email, password, expected_status, detail):
    response = client.post("/auth/login", json={"email": email, "password": password})

    assert response.status_code == expected_status
    if expected_status == 200:
        assert response.json()["token_type"] == "bearer"
        assert response.json()["access_token"]
    else:
        assert response.json()["detail"] == detail


def test_password_reset_request_is_non_disclosing_and_notifies_existing_user(monkeypatch, users):
    messages = []

    async def fake_notification(message):
        messages.append(message)

    monkeypatch.setattr(main, "send_notification", fake_notification)

    response = client.post("/auth/password-reset/request", json={"email": "user@example.com"})
    unknown = client.post("/auth/password-reset/request", json={"email": "unknown@example.com"})

    assert response.status_code == 200
    assert response.json()["message"].startswith("If the account exists")
    assert unknown.status_code == 200
    assert len(messages) == 1
    assert "Password reset token:" in messages[0]


def test_password_reset_confirm_updates_password(users):
    token = create_token(users["user"], minutes=30)
    response = client.post(
        "/auth/password-reset/confirm",
        json={"token": token, "password": "UpdatedPassword123"},
    )

    assert response.status_code == 200
    assert response.json() == {"message": "Password updated"}
    login = client.post(
        "/auth/login",
        json={"email": "user@example.com", "password": "UpdatedPassword123"},
    )
    assert login.status_code == 200


def test_authentication_is_required(users):
    response = client.get("/visitors")
    assert response.status_code == 401
    assert response.json()["detail"] == "Authentication required"


def test_users_list_and_update_permissions(users):
    response = client.get("/users", headers=auth_headers(users["admin"]))
    assert response.status_code == 200
    assert len(response.json()) == 4

    forbidden = client.patch(
        f"/users/{users['user'].id}",
        headers=auth_headers(users["admin"]),
        json={"role": "admin"},
    )
    assert forbidden.status_code == 403
    assert "Only super administrators" in forbidden.json()["detail"]

    updated = client.patch(
        f"/users/{users['user'].id}",
        headers=auth_headers(users["super"]),
        json={"full_name": "Updated Name", "role": "admin", "active": False},
    )
    assert updated.status_code == 200
    assert updated.json()["full_name"] == "Updated Name"
    assert updated.json()["role"] == "admin"
    assert updated.json()["active"] is False


def test_users_list_rejects_regular_user(users):
    response = client.get("/users", headers=auth_headers(users["user"]))
    assert response.status_code == 403
    assert response.json()["detail"] == "Insufficient permissions"


def test_delete_user_soft_deletes_and_hides_user(users):
    response = client.delete(
        f"/users/{users['pending'].id}",
        headers=auth_headers(users["admin"]),
    )
    assert response.status_code == 204
    assert response.content == b""

    listed = client.get("/users", headers=auth_headers(users["super"]))
    assert all(item["id"] != users["pending"].id for item in listed.json())

    missing = client.delete(
        f"/users/{users['pending'].id}",
        headers=auth_headers(users["admin"]),
    )
    assert missing.status_code == 404


def test_validate_visitor_rejects_invalid_data():
    cases = [
        (visitor_payload(end_date=(date.today() - timedelta(days=1)).isoformat()), "end_date cannot precede start_date"),
        (visitor_payload(location="Bangalore"), "Location must be WTC, Jayanagar, or Noida"),
        (visitor_payload(consent=False), "Visitor consent is mandatory"),
        (visitor_payload(photo_data="not-a-photo"), "A camera-captured photo is mandatory"),
    ]
    for payload, detail in cases:
        with pytest.raises(HTTPException) as error:
            validate_visitor(VisitorCreate.model_validate(payload))
        assert error.value.status_code == 422
        assert error.value.detail == detail


def test_create_visitor_requires_approver_for_regular_users(users):
    response = client.post(
        "/visitors",
        headers=auth_headers(users["user"]),
        json=visitor_payload(approver_id=None),
    )
    assert response.status_code == 422
    assert response.json()["detail"] == "An approver is required"


def test_visitor_approval_rejection_resubmission_and_checkin_checkout(users):
    created = client.post(
        "/visitors",
        headers=auth_headers(users["user"]),
        json=visitor_payload(approver_id=users["admin"].id),
    )
    assert created.status_code == 201
    visitor_id = created.json()["id"]
    assert created.json()["status"] == VisitStatus.WAITING.value

    rejected_without_reason = client.post(
        f"/visitors/{visitor_id}/approval",
        headers=auth_headers(users["admin"]),
        json={"approved": False},
    )
    assert rejected_without_reason.status_code == 422

    rejected = client.post(
        f"/visitors/{visitor_id}/approval",
        headers=auth_headers(users["admin"]),
        json={"approved": False, "rejection_reason": "Missing authorization"},
    )
    assert rejected.status_code == 200
    assert rejected.json()["status"] == VisitStatus.REJECTED.value

    resubmitted = client.put(
        f"/visitors/{visitor_id}",
        headers=auth_headers(users["user"]),
        json=visitor_payload(approver_id=users["admin"].id, visitee="Updated Employee"),
    )
    assert resubmitted.status_code == 200
    assert resubmitted.json()["status"] == VisitStatus.WAITING.value
    assert resubmitted.json()["rejection_reason"] is None

    approved = client.post(
        f"/visitors/{visitor_id}/approval",
        headers=auth_headers(users["admin"]),
        json={"approved": True},
    )
    assert approved.status_code == 200
    assert approved.json()["status"] == VisitStatus.APPROVED.value

    checked_in = client.post(
        f"/visitors/{visitor_id}/check-in",
        headers=auth_headers(users["user"]),
    )
    assert checked_in.status_code == 200
    assert checked_in.json()["checked_in_at"] is not None

    checked_out = client.post(
        f"/visitors/{visitor_id}/check-out",
        headers=auth_headers(users["user"]),
    )
    assert checked_out.status_code == 200
    assert checked_out.json()["checked_out_at"] is not None

    second_checkout = client.post(
        f"/visitors/{visitor_id}/check-out",
        headers=auth_headers(users["user"]),
    )
    assert second_checkout.status_code == 409


def test_visitor_visibility_and_filters(users):
    own = client.post(
        "/visitors",
        headers=auth_headers(users["user"]),
        json=visitor_payload(approver_id=users["admin"].id),
    )
    assert own.status_code == 201
    visitor_id = own.json()["id"]

    visible = client.get("/visitors", headers=auth_headers(users["user"]))
    assert len(visible.json()) == 1
    assert visible.json()[0]["id"] == visitor_id

    filtered = client.get(
        "/visitors",
        headers=auth_headers(users["admin"]),
        params={"status": "waiting_for_approval", "location": "WTC", "limit": 1},
    )
    assert filtered.status_code == 200
    assert len(filtered.json()) == 1

    hidden = client.get(
        f"/visitors/{visitor_id}",
        headers=auth_headers(users["pending"]),
    )
    assert hidden.status_code == 403


def test_visitor_update_only_allows_rejected_entries(users):
    created = client.post(
        "/visitors",
        headers=auth_headers(users["user"]),
        json=visitor_payload(approver_id=users["admin"].id),
    )
    visitor_id = created.json()["id"]
    response = client.put(
        f"/visitors/{visitor_id}",
        headers=auth_headers(users["user"]),
        json=visitor_payload(approver_id=users["admin"].id),
    )
    assert response.status_code == 409
    assert response.json()["detail"] == "Only rejected entries may be edited"


def test_approval_location_and_non_waiting_errors(users):
    created = client.post(
        "/visitors",
        headers=auth_headers(users["user"]),
        json=visitor_payload(approver_id=users["admin"].id),
    )
    visitor_id = created.json()["id"]

    wrong_location_admin = users["admin"]
    wrong_location_admin.location = "Noida"
    async def change_location():
        async with TestingSessionLocal() as db:
            item = await db.get(User, wrong_location_admin.id)
            item.location = "Noida"
            await db.commit()
    asyncio.run(change_location())

    forbidden = client.post(
        f"/visitors/{visitor_id}/approval",
        headers=auth_headers(wrong_location_admin),
        json={"approved": True},
    )
    assert forbidden.status_code == 404

    approved = client.post(
        f"/visitors/{visitor_id}/approval",
        headers=auth_headers(users["super"]),
        json={"approved": True},
    )
    assert approved.status_code == 200

    again = client.post(
        f"/visitors/{visitor_id}/approval",
        headers=auth_headers(users["super"]),
        json={"approved": True},
    )
    assert again.status_code == 409


def test_checkin_rejects_non_approved_visitor(users):
    created = client.post(
        "/visitors",
        headers=auth_headers(users["user"]),
        json=visitor_payload(approver_id=users["admin"].id),
    )
    response = client.post(
        f"/visitors/{created.json()['id']}/check-in",
        headers=auth_headers(users["user"]),
    )
    assert response.status_code == 409
    assert response.json()["detail"] == "Visitor is not eligible for check-in"


def test_dashboard_statistics_and_report_exports(users):
    created = client.post(
        "/visitors",
        headers=auth_headers(users["user"]),
        json=visitor_payload(approver_id=users["admin"].id),
    )
    assert created.status_code == 201

    stats = client.get("/dashboard/statistics", headers=auth_headers(users["user"]))
    assert stats.status_code == 200
    assert stats.json()["totals"][VisitStatus.WAITING.value] == 1
    assert len(stats.json()["recent_activity"]) == 1

    excel = client.get("/reports/visitors.xlsx", headers=auth_headers(users["admin"]))
    assert excel.status_code == 200
    assert excel.headers["content-type"].startswith("application/vnd.openxmlformats")
    assert "visitors.xlsx" in excel.headers["content-disposition"]
    assert excel.content[:2] == b"PK"

    pdf = client.get("/reports/visitors.pdf", headers=auth_headers(users["admin"]))
    assert pdf.status_code == 200
    assert pdf.headers["content-type"] == "application/pdf"
    assert "visitors.pdf" in pdf.headers["content-disposition"]
    assert pdf.content.startswith(b"%PDF")


def test_reports_require_admin_role(users):
    excel = client.get("/reports/visitors.xlsx", headers=auth_headers(users["user"]))
    pdf = client.get("/reports/visitors.pdf", headers=auth_headers(users["user"]))
    assert excel.status_code == 403
    assert pdf.status_code == 403


def test_notification_preferences_create_and_update(users):
    first = client.put(
        "/notifications/preferences",
        headers=auth_headers(users["admin"]),
        json={"muted": True, "internet_requests": False},
    )
    assert first.status_code == 200
    assert first.json() == {"muted": True, "internet_requests": False}

    second = client.put(
        "/notifications/preferences",
        headers=auth_headers(users["admin"]),
        json={"muted": False, "internet_requests": True},
    )
    assert second.status_code == 200
    assert second.json() == {"muted": False, "internet_requests": True}

    forbidden = client.put(
        "/notifications/preferences",
        headers=auth_headers(users["user"]),
        json={"muted": True},
    )
    assert forbidden.status_code == 403
