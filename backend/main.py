from __future__ import annotations

import base64
import csv
import hashlib
import hmac
import io
import json
import os
import secrets
from datetime import date, datetime, timedelta, timezone
from enum import Enum
from typing import Annotated, Any, AsyncGenerator

from fastapi import Depends, FastAPI, HTTPException, Query, Response, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from openpyxl import Workbook
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, JSON, String, Text, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./visitor_access.db")
JWT_SECRET = os.getenv("JWT_SECRET", "change-this-secret-in-production")
TOKEN_MINUTES = int(os.getenv("TOKEN_MINUTES", "60"))

engine = create_async_engine(DATABASE_URL, echo=False)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)
security = HTTPBearer(auto_error=False)


class Role(str, Enum):
    """Application roles."""

    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    USER = "user"


class VisitStatus(str, Enum):
    """Visitor approval states."""

    WAITING = "waiting_for_approval"
    APPROVED = "approved"
    REJECTED = "rejected"


class Base(DeclarativeBase):
    """Base SQLAlchemy model."""


class User(Base):
    """Application user."""

    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(160))
    password_hash: Mapped[str] = mapped_column(String(256))
    role: Mapped[str] = mapped_column(String(30), default=Role.USER.value)
    organization: Mapped[str | None] = mapped_column(String(160), nullable=True)
    location: Mapped[str | None] = mapped_column(String(80), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class Visitor(Base):
    """Visitor registration and approval record."""

    __tablename__ = "visitors"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    identity: Mapped[str] = mapped_column(String(160))
    phone: Mapped[str] = mapped_column(String(30))
    email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    pass_type: Mapped[str] = mapped_column(String(50))
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    origin: Mapped[str] = mapped_column(String(160))
    visitee: Mapped[str] = mapped_column(String(160))
    approver_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    location: Mapped[str] = mapped_column(String(80))
    consent: Mapped[bool] = mapped_column(Boolean)
    id_proof: Mapped[str] = mapped_column(String(160))
    photo_data: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(40), default=VisitStatus.WAITING.value)
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    submitted_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    checked_in_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    checked_out_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    access_card: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    device_certificate: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    internet_access_requested: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class AuditLog(Base):
    """Immutable audit attribution record."""

    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    actor_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(80))
    entity: Mapped[str] = mapped_column(String(80))
    entity_id: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class NotificationPreference(Base):
    """Per-administrator notification settings."""

    __tablename__ = "notification_preferences"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True)
    muted: Mapped[bool] = mapped_column(Boolean, default=False)
    internet_requests: Mapped[bool] = mapped_column(Boolean, default=True)


class UserCreate(BaseModel):
    """User registration payload."""

    email: EmailStr
    full_name: str = Field(min_length=2, max_length=160)
    password: str = Field(min_length=8)
    organization: str | None = None
    location: str | None = None


class UserUpdate(BaseModel):
    """Editable user fields."""

    full_name: str | None = None
    organization: str | None = None
    location: str | None = None
    role: Role | None = None
    active: bool | None = None


class LoginRequest(BaseModel):
    """Login payload."""

    email: EmailStr
    password: str


class UserRead(BaseModel):
    """Public user representation."""

    model_config = ConfigDict(from_attributes=True)
    id: int
    email: EmailStr
    full_name: str
    role: Role
    organization: str | None
    location: str | None
    active: bool


class VisitorCreate(BaseModel):
    """Visitor entry payload."""

    identity: str = Field(min_length=2, max_length=160)
    phone: str = Field(min_length=7, max_length=30)
    email: EmailStr | None = None
    pass_type: str = Field(min_length=2, max_length=50)
    start_date: date
    end_date: date
    origin: str
    visitee: str
    approver_id: int | None = None
    location: str
    consent: bool
    id_proof: str
    photo_data: str = Field(min_length=20, description="Base64 camera-captured image")
    access_card: dict[str, Any] | None = None
    device_certificate: dict[str, Any] | None = None
    internet_access_requested: bool = False


class VisitorUpdate(VisitorCreate):
    """Payload used only to edit and resubmit rejected entries."""


class VisitorRead(BaseModel):
    """Visitor response model."""

    model_config = ConfigDict(from_attributes=True)
    id: int
    identity: str
    phone: str
    email: EmailStr | None
    pass_type: str
    start_date: date
    end_date: date
    origin: str
    visitee: str
    approver_id: int | None
    location: str
    consent: bool
    id_proof: str
    status: VisitStatus
    rejection_reason: str | None
    submitted_by: int
    checked_in_at: datetime | None
    checked_out_at: datetime | None
    internet_access_requested: bool


class ApprovalRequest(BaseModel):
    """Approval decision payload."""

    approved: bool
    rejection_reason: str | None = Field(default=None, max_length=1000)


class ResetRequest(BaseModel):
    """Password-reset request payload."""

    email: EmailStr


class ResetConfirm(BaseModel):
    """Password-reset confirmation payload."""

    token: str
    password: str = Field(min_length=8)


class PreferenceUpdate(BaseModel):
    """Notification preference payload."""

    muted: bool
    internet_requests: bool = True


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield an SQLAlchemy asynchronous session."""
    async with SessionLocal() as session:
        yield session


def hash_password(password: str) -> str:
    """Hash a password using PBKDF2 with a random salt."""
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 180_000)
    return base64.b64encode(salt + digest).decode()


def verify_password(password: str, encoded: str) -> bool:
    """Verify a password against a PBKDF2 hash."""
    try:
        raw = base64.b64decode(encoded.encode())
        return hmac.compare_digest(hashlib.pbkdf2_hmac("sha256", password.encode(), raw[:16], 180_000), raw[16:])
    except (ValueError, TypeError):
        return False


def create_token(user: User, minutes: int = TOKEN_MINUTES) -> str:
    """Create a signed, expiring bearer token."""
    payload = {"sub": user.id, "role": user.role, "exp": int((datetime.now(timezone.utc) + timedelta(minutes=minutes)).timestamp())}
    body = base64.urlsafe_b64encode(json.dumps(payload, separators=(",", ":")).encode()).decode().rstrip("=")
    signature = hmac.new(JWT_SECRET.encode(), body.encode(), hashlib.sha256).hexdigest()
    return f"{body}.{signature}"


def decode_token(token: str) -> dict[str, Any]:
    """Validate and decode a signed bearer token."""
    try:
        body, signature = token.split(".", 1)
        expected = hmac.new(JWT_SECRET.encode(), body.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected):
            raise ValueError("invalid signature")
        padded = body + "=" * (-len(body) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded).decode())
        if int(payload["exp"]) < int(datetime.now(timezone.utc).timestamp()):
            raise ValueError("expired token")
        return payload
    except (ValueError, KeyError, TypeError, json.JSONDecodeError) as error:
        raise HTTPException(status_code=401, detail="Invalid or expired token") from error


async def current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """Resolve and validate the authenticated active user."""
    if credentials is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    payload = decode_token(credentials.credentials)
    user = await db.get(User, int(payload["sub"]))
    if user is None or not user.active or user.deleted_at is not None:
        raise HTTPException(status_code=403, detail="Inactive or deleted user")
    return user


def require_roles(*roles: Role) -> Any:
    """Build a dependency that enforces one of the supplied roles."""
    async def guard(user: Annotated[User, Depends(current_user)]) -> User:
        if user.role not in {role.value for role in roles}:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user
    return guard


async def audit(db: AsyncSession, actor: User, action: str, entity: str, entity_id: int) -> None:
    """Record an auditable action."""
    db.add(AuditLog(actor_id=actor.id, action=action, entity=entity, entity_id=entity_id))


def validate_visitor(data: VisitorCreate) -> None:
    """Validate visitor dates, consent, photo, and supported location."""
    allowed = {"WTC", "Jayanagar", "Noida"}
    if data.end_date < data.start_date:
        raise HTTPException(status_code=422, detail="end_date cannot precede start_date")
    if data.location not in allowed:
        raise HTTPException(status_code=422, detail="Location must be WTC, Jayanagar, or Noida")
    if not data.consent:
        raise HTTPException(status_code=422, detail="Visitor consent is mandatory")
    if not data.photo_data.startswith(("data:image/", "iVBOR", "/9j/")):
        raise HTTPException(status_code=422, detail="A camera-captured photo is mandatory")


async def send_notification(message: str) -> None:
    """Email-provider abstraction; replace this implementation with a real provider."""
    _ = message


app = FastAPI(title="Visitor Access and Authorization API", version="1.0.0")


@app.on_event("startup")
async def startup() -> None:
    """Create database tables and provision the initial super administrator."""
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    async with SessionLocal() as db:
        email = os.getenv("SUPER_ADMIN_EMAIL", "superadmin@example.com").lower()
        existing = await db.scalar(select(User).where(User.email == email))
        if existing is None:
            db.add(User(email=email, full_name="Super Administrator", password_hash=hash_password(os.getenv("SUPER_ADMIN_PASSWORD", "ChangeMe123!")), role=Role.SUPER_ADMIN.value, active=True))
            await db.commit()


@app.post("/auth/register", response_model=UserRead, status_code=201)
async def register(data: UserCreate, db: Annotated[AsyncSession, Depends(get_db)]) -> User:
    """Register an inactive user awaiting super-admin approval."""
    email = str(data.email).lower()
    if await db.scalar(select(User).where(User.email == email)):
        raise HTTPException(status_code=409, detail="Email already registered")
    user = User(email=email, full_name=data.full_name, password_hash=hash_password(data.password), organization=data.organization, location=data.location, active=False, role=Role.USER.value)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@app.post("/auth/login")
async def login(data: LoginRequest, db: Annotated[AsyncSession, Depends(get_db)]) -> dict[str, str]:
    """Authenticate an active user and issue a bearer token."""
    user = await db.scalar(select(User).where(User.email == str(data.email).lower(), User.deleted_at.is_(None)))
    if user is None or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not user.active:
        raise HTTPException(status_code=403, detail="User approval is pending")
    return {"access_token": create_token(user), "token_type": "bearer"}


@app.post("/auth/password-reset/request")
async def request_reset(data: ResetRequest, db: Annotated[AsyncSession, Depends(get_db)]) -> dict[str, str]:
    """Create a short-lived reset token and pass it to the email abstraction."""
    user = await db.scalar(select(User).where(User.email == str(data.email).lower(), User.deleted_at.is_(None)))
    if user is not None:
        token = create_token(user, 30)
        await send_notification(f"Password reset token: {token}")
    return {"message": "If the account exists, reset instructions were sent"}


@app.post("/auth/password-reset/confirm")
async def confirm_reset(data: ResetConfirm, db: Annotated[AsyncSession, Depends(get_db)]) -> dict[str, str]:
    """Validate a reset token and replace the user's password."""
    payload = decode_token(data.token)
    user = await db.get(User, int(payload["sub"]))
    if user is None or user.deleted_at is not None:
        raise HTTPException(status_code=404, detail="User not found")
    user.password_hash = hash_password(data.password)
    await db.commit()
    return {"message": "Password updated"}


@app.get("/users", response_model=list[UserRead])
async def list_users(
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(Role.SUPER_ADMIN, Role.ADMIN))],
) -> list[User]:
    """List non-deleted users for administrators."""
    return list((await db.scalars(select(User).where(User.deleted_at.is_(None)).order_by(User.id))).all())


@app.patch("/users/{user_id}", response_model=UserRead)
async def update_user(user_id: int, data: UserUpdate, db: Annotated[AsyncSession, Depends(get_db)], actor: Annotated[User, Depends(require_roles(Role.SUPER_ADMIN, Role.ADMIN))]) -> User:
    """Edit a user, with role assignment restricted to super administrators."""
    user = await db.get(User, user_id)
    if user is None or user.deleted_at is not None:
        raise HTTPException(status_code=404, detail="User not found")
    if data.role is not None and actor.role != Role.SUPER_ADMIN.value:
        raise HTTPException(status_code=403, detail="Only super administrators may assign roles")
    for field in ("full_name", "organization", "location", "active"):
        value = getattr(data, field)
        if value is not None:
            setattr(user, field, value)
    if data.role is not None:
        user.role = data.role.value
    await audit(db, actor, "update", "user", user.id)
    await db.commit()
    await db.refresh(user)
    return user


@app.delete("/users/{user_id}", status_code=204)
async def delete_user(user_id: int, db: Annotated[AsyncSession, Depends(get_db)], actor: Annotated[User, Depends(require_roles(Role.SUPER_ADMIN, Role.ADMIN))]) -> Response:
    """Soft-delete a user and preserve the deleting actor."""
    user = await db.get(User, user_id)
    if user is None or user.deleted_at is not None:
        raise HTTPException(status_code=404, detail="User not found")
    user.deleted_at = datetime.now(timezone.utc)
    user.deleted_by = actor.id
    user.active = False
    await audit(db, actor, "soft_delete", "user", user.id)
    await db.commit()
    return Response(status_code=204)


@app.post("/visitors", response_model=VisitorRead, status_code=201)
async def create_visitor(data: VisitorCreate, db: Annotated[AsyncSession, Depends(get_db)], actor: Annotated[User, Depends(current_user)]) -> Visitor:
    """Create a visitor entry in Waiting for Approval state."""
    validate_visitor(data)
    if actor.role == Role.USER and data.approver_id is None:
        raise HTTPException(status_code=422, detail="An approver is required")
    visitor = Visitor(**data.model_dump(), submitted_by=actor.id, status=VisitStatus.WAITING.value)
    db.add(visitor)
    await db.commit()
    await db.refresh(visitor)
    return visitor


@app.get("/visitors", response_model=list[VisitorRead])
async def list_visitors(db: Annotated[AsyncSession, Depends(get_db)], actor: Annotated[User, Depends(current_user)], visitor_status: VisitStatus | None = Query(default=None, alias="status"), location: str | None = None, submitted_by: int | None = None, from_date: date | None = None, to_date: date | None = None, skip: int = Query(default=0, ge=0), limit: int = Query(default=50, ge=1, le=200)) -> list[Visitor]:
    """List visitors with role, location, date, status, and pagination filters."""
    statement = select(Visitor).order_by(Visitor.created_at.desc())
    if actor.role == Role.USER:
        statement = statement.where(Visitor.submitted_by == actor.id)
    elif actor.role == Role.ADMIN and actor.location:
        statement = statement.where(Visitor.location == actor.location)
    if visitor_status:
        statement = statement.where(Visitor.status == visitor_status.value)
    if location:
        statement = statement.where(Visitor.location == location)
    if submitted_by:
        statement = statement.where(Visitor.submitted_by == submitted_by)
    if from_date:
        statement = statement.where(Visitor.start_date >= from_date)
    if to_date:
        statement = statement.where(Visitor.end_date <= to_date)
    return list((await db.scalars(statement.offset(skip).limit(limit))).all())


@app.get("/visitors/{visitor_id}", response_model=VisitorRead)
async def get_visitor(visitor_id: int, db: Annotated[AsyncSession, Depends(get_db)], actor: Annotated[User, Depends(current_user)]) -> Visitor:
    """Return a visitor subject to the caller's visibility rules."""
    visitor = await db.get(Visitor, visitor_id)
    if visitor is None or (actor.role == Role.USER and visitor.submitted_by != actor.id) or (actor.role == Role.ADMIN and actor.location != visitor.location):
        raise HTTPException(status_code=404, detail="Visitor not found")
    return visitor


@app.put("/visitors/{visitor_id}", response_model=VisitorRead)
async def update_visitor(visitor_id: int, data: VisitorUpdate, db: Annotated[AsyncSession, Depends(get_db)], actor: Annotated[User, Depends(current_user)]) -> Visitor:
    """Edit and resubmit a rejected entry; approved entries are immutable for users."""
    visitor = await get_visitor(visitor_id, db, actor)
    if visitor.submitted_by != actor.id and actor.role == Role.USER:
        raise HTTPException(status_code=403, detail="Only the submitter may edit this entry")
    if visitor.status != VisitStatus.REJECTED.value:
        raise HTTPException(status_code=409, detail="Only rejected entries may be edited")
    validate_visitor(data)
    for key, value in data.model_dump().items():
        setattr(visitor, key, value)
    visitor.status = VisitStatus.WAITING.value
    visitor.rejection_reason = None
    visitor.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(visitor)
    return visitor


@app.post("/visitors/{visitor_id}/approval", response_model=VisitorRead)
async def approve_visitor(visitor_id: int, decision: ApprovalRequest, db: Annotated[AsyncSession, Depends(get_db)], actor: Annotated[User, Depends(require_roles(Role.SUPER_ADMIN, Role.ADMIN))]) -> Visitor:
    """Approve or reject a visitor, requiring a reason for rejection."""
    visitor = await db.get(Visitor, visitor_id)
    if visitor is None or (actor.role == Role.ADMIN and actor.location != visitor.location):
        raise HTTPException(status_code=404, detail="Visitor not found")
    if visitor.status != VisitStatus.WAITING.value:
        raise HTTPException(status_code=409, detail="Entry is no longer awaiting approval")
    if not decision.approved and not decision.rejection_reason:
        raise HTTPException(status_code=422, detail="A rejection reason is required")
    visitor.status = VisitStatus.APPROVED.value if decision.approved else VisitStatus.REJECTED.value
    visitor.rejection_reason = None if decision.approved else decision.rejection_reason
    visitor.approver_id = actor.id
    await audit(db, actor, "approve" if decision.approved else "reject", "visitor", visitor.id)
    await db.commit()
    await db.refresh(visitor)
    return visitor


@app.post("/visitors/{visitor_id}/check-in", response_model=VisitorRead)
async def check_in(visitor_id: int, db: Annotated[AsyncSession, Depends(get_db)], actor: Annotated[User, Depends(current_user)]) -> Visitor:
    """Check in an approved visitor during the permitted multi-day period."""
    visitor = await get_visitor(visitor_id, db, actor)
    today = date.today()
    if visitor.status != VisitStatus.APPROVED.value or not visitor.start_date <= today <= visitor.end_date:
        raise HTTPException(status_code=409, detail="Visitor is not eligible for check-in")
    visitor.checked_in_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(visitor)
    return visitor


@app.post("/visitors/{visitor_id}/check-out", response_model=VisitorRead)
async def check_out(visitor_id: int, db: Annotated[AsyncSession, Depends(get_db)], actor: Annotated[User, Depends(current_user)]) -> Visitor:
    """Check out a visitor who has checked in."""
    visitor = await get_visitor(visitor_id, db, actor)
    if visitor.checked_in_at is None or visitor.checked_out_at is not None:
        raise HTTPException(status_code=409, detail="Visitor is not currently checked in")
    visitor.checked_out_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(visitor)
    return visitor


@app.get("/dashboard/statistics")
async def statistics(db: Annotated[AsyncSession, Depends(get_db)], _: Annotated[User, Depends(current_user)]) -> dict[str, Any]:
    """Return visitor totals and month-wise activity aggregation."""
    totals = dict((row[0], row[1]) for row in (await db.execute(select(Visitor.status, func.count(Visitor.id)).group_by(Visitor.status))).all())
    recent = list((await db.scalars(select(Visitor).order_by(Visitor.created_at.desc()).limit(10))).all())
    return {"totals": totals, "recent_activity": [VisitorRead.model_validate(item).model_dump(mode="json") for item in recent]}


@app.get("/reports/visitors.xlsx")
async def export_excel(db: Annotated[AsyncSession, Depends(get_db)], _: Annotated[User, Depends(require_roles(Role.SUPER_ADMIN, Role.ADMIN))]) -> Response:
    """Export visitor activity as an Excel workbook."""
    visitors = list((await db.scalars(select(Visitor).order_by(Visitor.created_at))).all())
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["ID", "Identity", "Location", "Status", "Start", "End", "Visitee"])
    for item in visitors:
        sheet.append([item.id, item.identity, item.location, item.status, item.start_date.isoformat(), item.end_date.isoformat(), item.visitee])
    output = io.BytesIO()
    workbook.save(output)
    return Response(output.getvalue(), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": "attachment; filename=visitors.xlsx"})


@app.get("/reports/visitors.pdf")
async def export_pdf(db: Annotated[AsyncSession, Depends(get_db)], _: Annotated[User, Depends(require_roles(Role.SUPER_ADMIN, Role.ADMIN))]) -> Response:
    """Export a concise visitor activity report as PDF."""
    visitors = list((await db.scalars(select(Visitor).order_by(Visitor.created_at))).all())
    output = io.BytesIO()
    document = canvas.Canvas(output, pagesize=A4)
    document.drawString(40, 800, "Visitor Activity Report")
    y_position = 775
    for item in visitors:
        document.drawString(40, y_position, f"{item.id}: {item.identity} | {item.location} | {item.status}")
        y_position -= 16
        if y_position < 40:
            document.showPage()
            y_position = 800
    document.save()
    return Response(output.getvalue(), media_type="application/pdf", headers={"Content-Disposition": "attachment; filename=visitors.pdf"})


@app.put("/notifications/preferences")
async def notification_preferences(data: PreferenceUpdate, db: Annotated[AsyncSession, Depends(get_db)], actor: Annotated[User, Depends(require_roles(Role.SUPER_ADMIN, Role.ADMIN))]) -> PreferenceUpdate:
    """Configure or mute administrator notifications."""
    preference = await db.scalar(select(NotificationPreference).where(NotificationPreference.user_id == actor.id))
    if preference is None:
        preference = NotificationPreference(user_id=actor.id)
        db.add(preference)
    preference.muted = data.muted
    preference.internet_requests = data.internet_requests
    await db.commit()
    return data
