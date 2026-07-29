import asyncio
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

import main
from database import Base, get_db
from models.entities import (
    AuditLog,
    Location,
    Notification,
    NotificationType,
    Organization,
    PasswordResetToken,
    User,
    UserRole,
    UserStatus,
    VisitorEntry,
    VisitorStatus,
    PassType,
)
from security import hash_password


DATABASE_URL = "sqlite+aiosqlite:///:memory:"
engine = create_async_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


def run(coro):
    return asyncio.run(coro)


async def _create_tables():
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)


async def _drop_tables():
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)


async def _get_user(user_id: int):
    async with TestingSessionLocal() as db:
        return await db.get(User, user_id)


async def _seed_user(
    email="user@example.com",
    role=UserRole.USER,
    status=UserStatus.ACTIVE,
    organization_id=None,
    password="StrongPass1!",
):
    async with TestingSessionLocal() as db:
        user = User(
            email=email,
            full_name="Test User",
            password_hash=hash_password(password),
            role=role,
            status=status,
            organization_id=organization_id,
            is_soft_deleted=False,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user.id


async def _seed_org_and_location():
    async with TestingSessionLocal() as db:
        organization = Organization(name="Test Organization", code="TEST")
        db.add(organization)
        await db.flush()
        location = Location(
            organization_id=organization.id,
            name="Main Entrance",
            address="1 Main Street",
        )
        db.add(location)
        await db.commit()
        await db.refresh(organization)
        await db.refresh(location)
        return organization.id, location.id


async def _seed_visitor(creator_id, location_id, status=VisitorStatus.WAITING_FOR_APPROVAL):
    async with TestingSessionLocal() as db:
        entry = VisitorEntry(
            creator_id=creator_id,
            location_id=location_id,
            visitor_name="Jane Visitor",
            visitor_email="jane@example.com",
            visitor_phone="5551234567",
            company="Example Corp",
            purpose="Business meeting",
            visit_date=date(2030, 1, 15),
            end_date=date(2030, 1, 15),
            pass_type=PassType.SINGLE_DAY,
            photo_metadata={"filename": "photo.jpg"},
            consent=True,
            status=status,
        )
        db.add(entry)
        await db.commit()
        await db.refresh(entry)
        return entry.id


@pytest.fixture(autouse=True)
def database():
    run(_create_tables())

    async def override_get_db():
        async with TestingSessionLocal() as db:
            yield db

    main.app.dependency_overrides[get_db] = override_get_db
    yield
    main.app.dependency_overrides.clear()
    run(_drop_tables())


@pytest.fixture
def client():
    return TestClient(main.app)


def set_authenticated_user(user_id):
    async def override_current_user():
        return await _get_user(user_id)

    main.app.dependency_overrides[main.current_user] = override_current_user


def test_health_returns_status_and_environment(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert "environment" in response.json()


def test_register_creates_pending_user_and_normalizes_email(client, monkeypatch):
    monkeypatch.setattr(main, "hash_password", lambda value: "hashed-password")

    response = client.post(
        "/auth/register",
        json={
            "email": "NEWUSER@EXAMPLE.COM",
            "full_name": "New User",
            "password": "StrongPass1!",
            "phone": "5550001111",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "newuser@example.com"
    assert body["full_name"] == "New User"
    assert body["status"] == UserStatus.PENDING.value
    assert body["role"] == UserRole.USER.value

    created = run(_get_user(body["id"]))
    assert created.password_hash == "hashed-password"


def test_register_rejects_duplicate_email(client):
    run(_seed_user(email="duplicate@example.com", status=UserStatus.PENDING))

    response = client.post(
        "/auth/register",
        json={
            "email": "DUPLICATE@example.com",
            "full_name": "Duplicate User",
            "password": "StrongPass1!",
        },
    )

    assert response.status_code == 409
    assert response.json() == {"detail": "Email is already registered"}


def test_login_returns_token_for_active_user(client, monkeypatch):
    user_id = run(_seed_user(email="active@example.com"))
    monkeypatch.setattr(main, "create_token", lambda subject, claims=None: "test-token")

    response = client.post(
        "/auth/login",
        json={"email": "ACTIVE@example.com", "password": "StrongPass1!"},
    )

    assert response.status_code == 200
    assert response.json()["access_token"] == "test-token"
    assert response.json()["token_type"] == "bearer"
    assert user_id > 0


def test_login_rejects_invalid_password(client):
    run(_seed_user(email="active@example.com"))

    response = client.post(
        "/auth/login",
        json={"email": "active@example.com", "password": "wrong-password"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"


def test_login_rejects_pending_user(client):
    run(_seed_user(email="pending@example.com", status=UserStatus.PENDING))

    response = client.post(
        "/auth/login",
        json={"email": "pending@example.com", "password": "StrongPass1!"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Account is waiting for administrator approval"


def test_me_returns_authenticated_user(client):
    user_id = run(_seed_user(email="me@example.com"))
    set_authenticated_user(user_id)

    response = client.get("/auth/me")

    assert response.status_code == 200
    assert response.json()["email"] == "me@example.com"


def test_current_user_rejects_invalid_bearer_token(client, monkeypatch):
    monkeypatch.setattr(main, "decode_token", lambda token: {"invalid": "payload"})

    response = client.get("/auth/me", headers={"Authorization": "Bearer bad-token"})

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid authentication credentials"


def test_password_reset_request_does_not_disclose_unknown_email(client):
    response = client.post(
        "/auth/password-reset/request",
        json={"email": "unknown@example.com"},
    )

    assert response.status_code == 202
    assert response.json() == {
        "message": "If the account exists, reset instructions have been sent"
    }


@pytest.mark.parametrize("export_format,media_type,filename", [
    ("csv", "text/csv; charset=utf-8", "visitors.csv"),
    (
        "xlsx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "visitors.xlsx",
    ),
    ("pdf", "application/pdf", "visitors.pdf"),
])
def test_export_report_formats(client, export_format, media_type, filename):
    organization_id, location_id = run(_seed_org_and_location())
    admin_id = run(
        _seed_user(
            email="admin@example.com",
            role=UserRole.ADMIN,
            organization_id=organization_id,
        )
    )
    run(_seed_visitor(admin_id, location_id, VisitorStatus.APPROVED))
    set_authenticated_user(admin_id)

    response = client.get(f"/reports/visitors/export?format={export_format}")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith(media_type)
    assert filename in response.headers["content-disposition"]
    assert len(response.content) > 0
    if export_format == "csv":
        assert b"visitor_name" in response.content
        assert b"Jane Visitor" in response.content


def test_export_report_rejects_unknown_format(client):
    response = client.get("/reports/visitors/export?format=xml")

    assert response.status_code == 422


def test_create_visitor_defaults_end_date_and_creates_audit_log(client):
    organization_id, location_id = run(_seed_org_and_location())
    user_id = run(
        _seed_user(email="creator@example.com", organization_id=organization_id)
    )
    set_authenticated_user(user_id)

    response = client.post(
        "/visitors",
        json={
            "location_id": location_id,
            "visitor_name": "Visitor One",
            "visitor_email": "visitor@example.com",
            "visitor_phone": "5551234567",
            "purpose": "Interview",
            "visit_date": "2030-02-01",
            "pass_type": "Single Day",
            "photo_metadata": {"filename": "visitor.jpg"},
            "consent": True,
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == VisitorStatus.WAITING_FOR_APPROVAL.value
    assert body["end_date"] == "2030-02-01"

    async def audit_rows():
        async with TestingSessionLocal() as db:
            result = await db.execute(
                __import__("sqlalchemy").select(AuditLog).where(
                    AuditLog.action == "VISITOR_CREATED"
                )
            )
            return result.scalars().all()

    assert len(run(audit_rows())) == 1


def test_create_visitor_rejects_self_approval(client):
    organization_id, location_id = run(_seed_org_and_location())
    user_id = run(
        _seed_user(email="creator@example.com", organization_id=organization_id)
    )
    set_authenticated_user(user_id)

    response = client.post(
        "/visitors",
        json={
            "location_id": location_id,
            "approver_id": user_id,
            "visitor_name": "Visitor One",
            "visitor_phone": "5551234567",
            "purpose": "Interview",
            "visit_date": "2030-02-01",
            "pass_type": "Single Day",
            "photo_metadata": {},
            "consent": True,
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Creator cannot approve their own entry"


def test_admin_can_approve_pending_visitor(client):
    organization_id, location_id = run(_seed_org_and_location())
    creator_id = run(
        _seed_user(email="creator@example.com", organization_id=organization_id)
    )
    admin_id = run(
        _seed_user(
            email="admin@example.com",
            role=UserRole.ADMIN,
            organization_id=organization_id,
        )
    )
    entry_id = run(_seed_visitor(creator_id, location_id))
    set_authenticated_user(admin_id)

    response = client.post(
        f"/visitors/{entry_id}/approval",
        json={"approved": True},
    )

    assert response.status_code == 200
    assert response.json()["status"] == VisitorStatus.APPROVED.value
    assert response.json()["approver_id"] == admin_id


def test_admin_cannot_list_users_from_another_organization(client):
    org_one, _ = run(_seed_org_and_location())
    admin_id = run(
        _seed_user(
            email="admin@example.com",
            role=UserRole.ADMIN,
            organization_id=org_one,
        )
    )
    run(_seed_user(email="same@example.com", organization_id=org_one))
    other_org_id = run(
        _seed_user(email="other@example.com", organization_id=999)
    )
    set_authenticated_user(admin_id)

    response = client.get("/users")

    assert response.status_code == 200
    emails = {item["email"] for item in response.json()}
    assert "same@example.com" in emails
    assert "other@example.com" not in emails
    assert other_org_id > 0


def test_notification_read_requires_ownership(client):
    owner_id = run(_seed_user(email="owner@example.com"))
    other_id = run(_seed_user(email="other@example.com"))

    async def create_notification():
        async with TestingSessionLocal() as db:
            item = Notification(
                recipient_id=owner_id,
                type=NotificationType.SYSTEM,
                title="Notice",
                message="Message",
            )
            db.add(item)
            await db.commit()
            await db.refresh(item)
            return item.id

    notification_id = run(create_notification())
    set_authenticated_user(other_id)

    response = client.patch(f"/notifications/{notification_id}/read")

    assert response.status_code == 404
    assert response.json()["detail"] == "Notification not found"


def test_dashboard_returns_role_scoped_counts(client):
    organization_id, location_id = run(_seed_org_and_location())
    user_id = run(
        _seed_user(email="dashboard@example.com", organization_id=organization_id)
    )
    run(_seed_visitor(user_id, location_id, VisitorStatus.APPROVED))
    run(_seed_visitor(user_id, location_id, VisitorStatus.REJECTED))
    set_authenticated_user(user_id)

    response = client.get("/dashboard/summary")

    assert response.status_code == 200
    assert response.json()[VisitorStatus.APPROVED.value] == 1
    assert response.json()[VisitorStatus.REJECTED.value] == 1
