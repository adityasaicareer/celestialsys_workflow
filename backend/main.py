"""FastAPI application entry point for the visitor management platform."""
from datetime import datetime, timedelta, timezone
import hashlib
import io
import secrets
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database import get_db, init_db
from email_provider import get_email_provider
from models.entities import (
    AuditLog,
    Notification,
    NotificationType,
    PasswordResetToken,
    User,
    UserRole,
    UserStatus,
    VisitorEntry,
    VisitorStatus,
)
from schemas.core import (
    ApprovalRequest,
    LoginRequest,
    NotificationResponse,
    PasswordResetConfirm,
    PasswordResetRequest,
    RegisterRequest,
    ReportFilters,
    TokenResponse,
    UserResponse,
    UserUpdateRequest,
    VisitorCreateRequest,
    VisitorResponse,
)
from security import create_token, decode_token, hash_password, verify_password

app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description="Unified visitor, access, approval, and reporting API.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
oauth2 = OAuth2PasswordBearer(tokenUrl="/auth/login")


@app.on_event("startup")
async def startup() -> None:
    """Initialize local database tables."""
    await init_db()


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exception: HTTPException) -> Response:
    """Return the standard FastAPI error response."""
    del request
    content = '{"detail":"' + str(exception.detail).replace('"', '\\"') + '"}'
    return Response(
        content=content,
        status_code=exception.status_code,
        media_type="application/json",
    )


@app.get("/health", tags=["system"])
async def health() -> dict[str, str]:
    """Return service health status."""
    return {"status": "ok", "environment": settings.environment}


async def current_user(
    token: Annotated[str, Depends(oauth2)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """Resolve the authenticated active user from a bearer token."""
    try:
        payload = decode_token(token)
        user_id = int(payload["sub"])
    except (ValueError, KeyError, TypeError) as error:
        raise HTTPException(
            status_code=401,
            detail="Invalid authentication credentials",
        ) from error
    user = await db.get(User, user_id)
    if not user or user.is_soft_deleted or user.status != UserStatus.ACTIVE:
        raise HTTPException(status_code=403, detail="Account is inactive or unavailable")
    return user


def require_roles(*roles: UserRole):
    """Create a dependency restricting access to the supplied roles."""
    async def dependency(
        user: Annotated[User, Depends(current_user)],
    ) -> User:
        """Check the current user's role."""
        if user.role not in roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user

    return dependency


async def audit(
    db: AsyncSession,
    actor_id: int | None,
    action: str,
    entity_type: str,
    entity_id: int | None,
    details: dict | None = None,
) -> None:
    """Append an audit event to the current transaction."""
    db.add(
        AuditLog(
            actor_id=actor_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            details=details or {},
        )
    )


@app.post("/auth/register", response_model=UserResponse, status_code=201, tags=["auth"])
async def register(
    payload: RegisterRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """Register a pending user who requires administrator approval."""
    user = User(
        email=payload.email.lower(),
        full_name=payload.full_name,
        phone=payload.phone,
        organization_id=payload.organization_id,
        password_hash=hash_password(payload.password),
        status=UserStatus.PENDING,
        role=UserRole.USER,
    )
    db.add(user)
    try:
        await db.commit()
        await db.refresh(user)
        return user
    except IntegrityError as error:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Email is already registered") from error


@app.post("/auth/login", response_model=TokenResponse, tags=["auth"])
async def login(
    payload: LoginRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TokenResponse:
    """Authenticate an active user and issue a JWT."""
    user = (
        await db.execute(
            select(User).where(
                User.email == payload.email.lower(),
                User.is_soft_deleted.is_(False),
            )
        )
    ).scalar_one_or_none()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if user.status != UserStatus.ACTIVE:
        raise HTTPException(
            status_code=403,
            detail="Account is waiting for administrator approval",
        )
    return TokenResponse(
        access_token=create_token(str(user.id), claims={"role": user.role.value})
    )


@app.get("/auth/me", response_model=UserResponse, tags=["auth"])
async def me(user: Annotated[User, Depends(current_user)]) -> User:
    """Return the authenticated user's profile."""
    return user


@app.post("/auth/password-reset/request", status_code=202, tags=["auth"])
async def request_password_reset(
    payload: PasswordResetRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, str]:
    """Create a password reset token without disclosing account existence."""
    user = (
        await db.execute(
            select(User).where(
                User.email == payload.email.lower(),
                User.is_soft_deleted.is_(False),
            )
        )
    ).scalar_one_or_none()
    if user:
        raw = secrets.token_urlsafe(32)
        token = PasswordResetToken(
            user_id=user.id,
            token_hash=hashlib.sha256(raw.encode()).hexdigest(),
            expires_at=datetime.now(timezone.utc)
            + timedelta(minutes=settings.password_reset_minutes),
        )
        db.add(token)
        await db.commit()
        await get_email_provider().send(
            user.email,
            "Password reset",
            settings.frontend_url + "/reset-password?token=" + raw,
        )
    return {"message": "If the account exists, reset instructions have been sent"}


@app.post("/auth/password-reset/confirm", status_code=204, tags=["auth"])
async def confirm_password_reset(
    payload: PasswordResetConfirm,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Consume a valid reset token and replace the password."""
    token_hash = hashlib.sha256(payload.token.encode()).hexdigest()
    item = (
        await db.execute(
            select(PasswordResetToken).where(
                PasswordResetToken.token_hash == token_hash,
                PasswordResetToken.used_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if not item or item.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")
    user = await db.get(User, item.user_id)
    if not user:
        raise HTTPException(status_code=400, detail="Invalid reset token")
    user.password_hash = hash_password(payload.new_password)
    item.used_at = datetime.now(timezone.utc)
    await db.commit()


@app.get("/users", response_model=list[UserResponse], tags=["users"])
async def list_users(
    user: Annotated[User, Depends(require_roles(UserRole.ADMIN, UserRole.SUPER_ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[User]:
    """List users visible to administrators."""
    query = select(User).where(User.is_soft_deleted.is_(False))
    if user.role == UserRole.ADMIN:
        query = query.where(User.organization_id == user.organization_id)
    return list((await db.execute(query.order_by(User.created_at.desc()))).scalars().all())


@app.patch("/users/{user_id}", response_model=UserResponse, tags=["users"])
async def update_user(
    user_id: int,
    payload: UserUpdateRequest,
    actor: Annotated[User, Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """Update, approve, assign, or soft-delete a user."""
    target = await db.get(User, user_id)
    if not target or target.is_soft_deleted or (
        actor.role == UserRole.ADMIN
        and target.organization_id != actor.organization_id
    ):
        raise HTTPException(status_code=404, detail="User not found")
    if payload.role == UserRole.SUPER_ADMIN and actor.role != UserRole.SUPER_ADMIN:
        raise HTTPException(
            status_code=403,
            detail="Only Super Admin can assign Super Admin",
        )
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(target, field, value)
    await audit(
        db,
        actor.id,
        "USER_UPDATED",
        "User",
        target.id,
        payload.model_dump(exclude_unset=True),
    )
    await db.commit()
    await db.refresh(target)
    return target


@app.delete("/users/{user_id}", status_code=204, tags=["users"])
async def delete_user(
    user_id: int,
    actor: Annotated[User, Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Soft-delete a user without removing audit history."""
    target = await db.get(User, user_id)
    if not target or (
        actor.role == UserRole.ADMIN
        and target.organization_id != actor.organization_id
    ):
        raise HTTPException(status_code=404, detail="User not found")
    target.is_soft_deleted = True
    target.status = UserStatus.DELETED
    await audit(db, actor.id, "USER_DELETED", "User", user_id)
    await db.commit()


@app.post("/visitors", response_model=VisitorResponse, status_code=201, tags=["visitors"])
async def create_visitor(
    payload: VisitorCreateRequest,
    user: Annotated[User, Depends(current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> VisitorEntry:
    """Create a visitor entry in Waiting for Approval state."""
    if payload.approver_id == user.id:
        raise HTTPException(status_code=400, detail="Creator cannot approve their own entry")
    values = payload.model_dump()
    values["photo_metadata"] = payload.photo_metadata.model_dump()
    values["end_date"] = values["end_date"] or values["visit_date"]
    entry = VisitorEntry(
        **values,
        creator_id=user.id,
        status=VisitorStatus.WAITING_FOR_APPROVAL,
    )
    db.add(entry)
    try:
        await db.flush()
        if payload.approver_id:
            db.add(
                Notification(
                    recipient_id=payload.approver_id,
                    type=NotificationType.VISITOR_APPROVAL,
                    title="Visitor approval required",
                    message="A visitor entry requires your approval",
                    visitor_entry_id=entry.id,
                )
            )
        await audit(db, user.id, "VISITOR_CREATED", "VisitorEntry", entry.id)
        await db.commit()
        await db.refresh(entry)
        return entry
    except IntegrityError as error:
        await db.rollback()
        raise HTTPException(status_code=400, detail="Invalid location or approver") from error


@app.get("/visitors", response_model=list[VisitorResponse], tags=["visitors"])
async def list_visitors(
    user: Annotated[User, Depends(current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    filters: Annotated[ReportFilters, Depends()],
) -> list[VisitorEntry]:
    """List visitor entries according to role and report filters."""
    query = select(VisitorEntry)
    if user.role in (UserRole.USER, UserRole.ADMIN):
        query = query.where(VisitorEntry.creator_id == user.id)
    if filters.from_date:
        query = query.where(VisitorEntry.visit_date >= filters.from_date)
    if filters.to_date:
        query = query.where(VisitorEntry.visit_date <= filters.to_date)
    for column, value in (
        (VisitorEntry.creator_id, filters.creator_id),
        (VisitorEntry.approver_id, filters.approver_id),
        (VisitorEntry.status, filters.status),
        (VisitorEntry.location_id, filters.location_id),
    ):
        if value is not None:
            query = query.where(column == value)
    query = (
        query.offset((filters.page - 1) * filters.page_size)
        .limit(filters.page_size)
        .order_by(VisitorEntry.created_at.desc())
    )
    return list((await db.execute(query)).scalars().all())


@app.post("/visitors/{entry_id}/approval", response_model=VisitorResponse, tags=["approvals"])
async def approve_visitor(
    entry_id: int,
    payload: ApprovalRequest,
    approver: Annotated[
        User,
        Depends(require_roles(UserRole.ADMIN, UserRole.SUPER_ADMIN)),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> VisitorEntry:
    """Approve or reject a pending visitor entry."""
    entry = await db.get(VisitorEntry, entry_id)
    if not entry or entry.status != VisitorStatus.WAITING_FOR_APPROVAL:
        raise HTTPException(status_code=404, detail="Pending visitor entry not found")
    if approver.role == UserRole.ADMIN and entry.approver_id not in (None, approver.id):
        raise HTTPException(status_code=403, detail="Entry is assigned to another approver")
    entry.approver_id = approver.id
    entry.status = VisitorStatus.APPROVED if payload.approved else VisitorStatus.REJECTED
    entry.rejection_reason = None if payload.approved else payload.reason
    entry.approved_at = datetime.now(timezone.utc) if payload.approved else None
    db.add(
        Notification(
            recipient_id=entry.creator_id,
            type=NotificationType.VISITOR_APPROVAL,
            title="Visitor entry updated",
            message="Your visitor entry was " + entry.status.value.lower(),
            visitor_entry_id=entry.id,
        )
    )
    await audit(
        db,
        approver.id,
        "VISITOR_" + ("APPROVED" if payload.approved else "REJECTED"),
        "VisitorEntry",
        entry.id,
        {"reason": payload.reason},
    )
    await db.commit()
    await db.refresh(entry)
    return entry


@app.post("/visitors/{entry_id}/resubmit", response_model=VisitorResponse, tags=["visitors"])
async def resubmit_visitor(
    entry_id: int,
    payload: VisitorCreateRequest,
    user: Annotated[User, Depends(current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> VisitorEntry:
    """Edit a rejected entry and return it to approval."""
    entry = await db.get(VisitorEntry, entry_id)
    if not entry or entry.creator_id != user.id or entry.status != VisitorStatus.REJECTED:
        raise HTTPException(
            status_code=400,
            detail="Only your rejected entries can be resubmitted",
        )
    values = payload.model_dump()
    values["photo_metadata"] = payload.photo_metadata.model_dump()
    values["end_date"] = values["end_date"] or values["visit_date"]
    for key, value in values.items():
        setattr(entry, key, value)
    entry.status = VisitorStatus.WAITING_FOR_APPROVAL
    entry.rejection_reason = None
    await audit(db, user.id, "VISITOR_RESUBMITTED", "VisitorEntry", entry.id)
    await db.commit()
    await db.refresh(entry)
    return entry


@app.get("/notifications", response_model=list[NotificationResponse], tags=["notifications"])
async def notifications(
    user: Annotated[User, Depends(current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[Notification]:
    """Return the current user's unmuted and muted notifications."""
    return list(
        (
            await db.execute(
                select(Notification)
                .where(Notification.recipient_id == user.id)
                .order_by(Notification.created_at.desc())
            )
        )
        .scalars()
        .all()
    )


@app.patch("/notifications/{notification_id}/read", response_model=NotificationResponse, tags=["notifications"])
async def mark_notification_read(
    notification_id: int,
    user: Annotated[User, Depends(current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Notification:
    """Mark an owned notification as read."""
    item = await db.get(Notification, notification_id)
    if not item or item.recipient_id != user.id:
        raise HTTPException(status_code=404, detail="Notification not found")
    item.is_read = True
    await db.commit()
    await db.refresh(item)
    return item


@app.get("/dashboard/summary", tags=["dashboard"])
async def dashboard(
    user: Annotated[User, Depends(current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, int]:
    """Return role-scoped visitor workflow counts."""
    query = select(VisitorEntry.status, func.count(VisitorEntry.id)).group_by(
        VisitorEntry.status
    )
    if user.role == UserRole.USER:
        query = query.where(VisitorEntry.creator_id == user.id)
    rows = (await db.execute(query)).all()
    return {status.value: count for status, count in rows}


@app.get("/reports/visitors", response_model=list[VisitorResponse], tags=["reports"])
async def report(
    filters: Annotated[ReportFilters, Depends()],
    user: Annotated[
        User,
        Depends(require_roles(UserRole.ADMIN, UserRole.SUPER_ADMIN)),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[VisitorEntry]:
    """Return a consolidated, role-authorized visitor activity report."""
    return await list_visitors(user, db, filters)


@app.get("/reports/visitors/export", tags=["reports"])
async def export_report(
    filters: Annotated[ReportFilters, Depends()],
    format: str = Query(default="csv", pattern="^(csv|xlsx|pdf)$"),
    user: User = Depends(require_roles(UserRole.ADMIN, UserRole.SUPER_ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """Export the same filtered report data as CSV, XLSX, or PDF."""
    rows = await list_visitors(user, db, filters)
    if format == "csv":
        content = (
            "id,visitor_name,status,visit_date,location_id,creator_id\n"
            + "\n".join(
                ",".join(
                    map(
                        str,
                        [
                            row.id,
                            row.visitor_name,
                            row.status.value,
                            row.visit_date,
                            row.location_id,
                            row.creator_id,
                        ],
                    )
                )
                for row in rows
            )
        )
        return StreamingResponse(
            io.BytesIO(content.encode()),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=visitors.csv"},
        )
    if format == "xlsx":
        from openpyxl import Workbook

        workbook = Workbook()
        sheet = workbook.active
        sheet.append(["id", "visitor_name", "status", "visit_date", "location_id", "creator_id"])
        for row in rows:
            sheet.append(
                [
                    row.id,
                    row.visitor_name,
                    row.status.value,
                    row.visit_date.isoformat(),
                    row.location_id,
                    row.creator_id,
                ]
            )
        output = io.BytesIO()
        workbook.save(output)
        output.seek(0)
        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=visitors.xlsx"},
        )
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen.canvas import Canvas

    output = io.BytesIO()
    canvas = Canvas(output, pagesize=letter)
    canvas.drawString(40, 760, "Visitor Activity Report")
    for index, row in enumerate(rows[:45]):
        canvas.drawString(
            40,
            740 - index * 15,
            str(row.id)
            + " | "
            + row.visitor_name
            + " | "
            + row.status.value
            + " | "
            + str(row.visit_date),
        )
    canvas.save()
    output.seek(0)
    return StreamingResponse(
        output,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=visitors.pdf"},
    )
