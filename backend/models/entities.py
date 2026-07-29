"""Unified SQLAlchemy data model for visitor management."""
from datetime import date, datetime, time
from enum import Enum
from typing import Optional
from sqlalchemy import Boolean, Date, DateTime, Enum as SAEnum, ForeignKey, Integer, JSON, String, Text, Time, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database import Base


class UserRole(str, Enum):
    """Supported application roles."""
    SUPER_ADMIN = "Super Admin"
    ADMIN = "Admin"
    USER = "User"


class UserStatus(str, Enum):
    """User lifecycle states."""
    PENDING = "Pending"
    ACTIVE = "Active"
    INACTIVE = "Inactive"
    DELETED = "Deleted"


class VisitorStatus(str, Enum):
    """Visitor entry workflow states."""
    WAITING_FOR_APPROVAL = "Waiting for Approval"
    APPROVED = "Approved"
    REJECTED = "Rejected"
    CANCELLED = "Cancelled"
    COMPLETED = "Completed"


class PassType(str, Enum):
    """Supported visitor pass types."""
    SINGLE_DAY = "Single Day"
    MULTI_DAY = "Multi-Day"
    RECURRING = "Recurring"


class NotificationType(str, Enum):
    """Notification categories."""
    VISITOR_APPROVAL = "Visitor Approval"
    INTERNET_ACCESS = "Internet Access"
    PASSWORD_RESET = "Password Reset"
    SYSTEM = "System"


class TimestampMixin:
    """Provide creation and update timestamps."""
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Organization(TimestampMixin, Base):
    """Represent an organization or tenant."""
    __tablename__ = "organizations"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(150), unique=True, index=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    locations: Mapped[list["Location"]] = relationship(back_populates="organization", cascade="all, delete-orphan")


class Location(TimestampMixin, Base):
    """Represent a supported visitor location."""
    __tablename__ = "locations"
    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    name: Mapped[str] = mapped_column(String(150))
    address: Mapped[Optional[str]] = mapped_column(String(300))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    organization: Mapped[Organization] = relationship(back_populates="locations")


class User(TimestampMixin, Base):
    """Represent an authenticated application user."""
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[Optional[int]] = mapped_column(ForeignKey("organizations.id"), index=True)
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(150))
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(SAEnum(UserRole), default=UserRole.USER)
    status: Mapped[UserStatus] = mapped_column(SAEnum(UserStatus), default=UserStatus.PENDING)
    phone: Mapped[Optional[str]] = mapped_column(String(30))
    is_soft_deleted: Mapped[bool] = mapped_column(Boolean, default=False)


class VisitorEntry(TimestampMixin, Base):
    """Represent a visitor request and its approval workflow."""
    __tablename__ = "visitor_entries"
    id: Mapped[int] = mapped_column(primary_key=True)
    creator_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    approver_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), index=True)
    location_id: Mapped[int] = mapped_column(ForeignKey("locations.id"), index=True)
    visitor_name: Mapped[str] = mapped_column(String(150))
    visitor_email: Mapped[Optional[str]] = mapped_column(String(254))
    visitor_phone: Mapped[str] = mapped_column(String(30))
    company: Mapped[Optional[str]] = mapped_column(String(150))
    purpose: Mapped[str] = mapped_column(String(500))
    visit_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    start_time: Mapped[Optional[time]] = mapped_column(Time)
    end_time: Mapped[Optional[time]] = mapped_column(Time)
    pass_type: Mapped[PassType] = mapped_column(SAEnum(PassType))
    photo_metadata: Mapped[dict] = mapped_column(JSON)
    consent: Mapped[bool] = mapped_column(Boolean, default=False)
    id_proof_type: Mapped[Optional[str]] = mapped_column(String(50))
    id_proof_reference: Mapped[Optional[str]] = mapped_column(String(255))
    access_card_number: Mapped[Optional[str]] = mapped_column(String(100))
    device_certificate_id: Mapped[Optional[str]] = mapped_column(String(255))
    internet_access_requested: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[VisitorStatus] = mapped_column(SAEnum(VisitorStatus), default=VisitorStatus.WAITING_FOR_APPROVAL, index=True)
    rejection_reason: Mapped[Optional[str]] = mapped_column(Text)
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    creator: Mapped[User] = relationship(foreign_keys=[creator_id])
    approver: Mapped[Optional[User]] = relationship(foreign_keys=[approver_id])


class AccessCard(TimestampMixin, Base):
    """Represent an issued access card."""
    __tablename__ = "access_cards"
    id: Mapped[int] = mapped_column(primary_key=True)
    visitor_entry_id: Mapped[int] = mapped_column(ForeignKey("visitor_entries.id"), index=True)
    card_number: Mapped[str] = mapped_column(String(100), unique=True)
    issued_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    returned_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class DeviceCertificate(TimestampMixin, Base):
    """Represent a device certificate associated with a visitor."""
    __tablename__ = "device_certificates"
    id: Mapped[int] = mapped_column(primary_key=True)
    visitor_entry_id: Mapped[int] = mapped_column(ForeignKey("visitor_entries.id"), index=True)
    fingerprint: Mapped[str] = mapped_column(String(255), unique=True)
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)


class Notification(TimestampMixin, Base):
    """Represent an in-app notification."""
    __tablename__ = "notifications"
    id: Mapped[int] = mapped_column(primary_key=True)
    recipient_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    type: Mapped[NotificationType] = mapped_column(SAEnum(NotificationType))
    title: Mapped[str] = mapped_column(String(200))
    message: Mapped[str] = mapped_column(Text)
    visitor_entry_id: Mapped[Optional[int]] = mapped_column(ForeignKey("visitor_entries.id"))
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    is_muted: Mapped[bool] = mapped_column(Boolean, default=False)


class PasswordResetToken(Base):
    """Represent a single-use password reset token."""
    __tablename__ = "password_reset_tokens"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    token_hash: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


class AuditLog(Base):
    """Represent an immutable security and business event."""
    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(primary_key=True)
    actor_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), index=True)
    action: Mapped[str] = mapped_column(String(100), index=True)
    entity_type: Mapped[str] = mapped_column(String(100))
    entity_id: Mapped[Optional[int]] = mapped_column(Integer)
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ReportFilter(Base):
    """Represent saved report filter preferences."""
    __tablename__ = "report_filters"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(150))
    filters: Mapped[dict] = mapped_column(JSON, default=dict)
