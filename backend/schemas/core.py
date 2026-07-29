"""Shared request and response contracts for the API."""
from datetime import date, datetime, time
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator

from models.entities import PassType, UserRole, UserStatus, VisitorStatus


class StrictSchema(BaseModel):
    """Base schema configured for ORM serialization."""

    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)


class RegisterRequest(StrictSchema):
    """Public registration request."""

    email: EmailStr
    full_name: str = Field(min_length=2, max_length=150)
    password: str = Field(min_length=12, max_length=128)
    phone: Optional[str] = Field(default=None, max_length=30)
    organization_id: Optional[int] = Field(default=None, gt=0)


class LoginRequest(StrictSchema):
    """Login credentials."""

    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class TokenResponse(StrictSchema):
    """JWT response."""

    access_token: str
    token_type: str = "bearer"


class UserResponse(StrictSchema):
    """Public user representation."""

    id: int
    email: EmailStr
    full_name: str
    phone: Optional[str]
    role: UserRole
    status: UserStatus
    organization_id: Optional[int]


class UserUpdateRequest(StrictSchema):
    """Administrator user update request."""

    full_name: Optional[str] = Field(default=None, min_length=2, max_length=150)
    phone: Optional[str] = Field(default=None, max_length=30)
    role: Optional[UserRole] = None
    status: Optional[UserStatus] = None
    organization_id: Optional[int] = Field(default=None, gt=0)


class PhotoMetadata(StrictSchema):
    """Mandatory camera-captured photo metadata."""

    capture_id: str = Field(min_length=1, max_length=255)
    captured_at: datetime
    mime_type: str = Field(pattern=r"^image/(jpeg|png|webp)$")
    sha256: str = Field(min_length=64, max_length=64)
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    camera_id: Optional[str] = Field(default=None, max_length=255)


class VisitorCreateRequest(StrictSchema):
    """Visitor entry creation and resubmission request."""

    approver_id: Optional[int] = Field(default=None, gt=0)
    location_id: int = Field(gt=0)
    visitor_name: str = Field(min_length=2, max_length=150)
    visitor_email: Optional[EmailStr] = None
    visitor_phone: str = Field(min_length=3, max_length=30)
    company: Optional[str] = Field(default=None, max_length=150)
    purpose: str = Field(min_length=3, max_length=500)
    visit_date: date
    end_date: Optional[date] = None
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    pass_type: PassType
    photo_metadata: PhotoMetadata
    consent: bool
    id_proof_type: Optional[str] = Field(default=None, max_length=50)
    id_proof_reference: Optional[str] = Field(default=None, max_length=255)
    access_card_number: Optional[str] = Field(default=None, max_length=100)
    device_certificate_id: Optional[str] = Field(default=None, max_length=255)
    internet_access_requested: bool = False

    @model_validator(mode="after")
    def validate_dates_and_consent(self) -> "VisitorCreateRequest":
        """Validate visit dates, duration, and consent."""
        end = self.end_date or self.visit_date
        if end < self.visit_date:
            raise ValueError("end_date cannot precede visit_date")
        if self.pass_type == PassType.MULTI_DAY and end == self.visit_date:
            raise ValueError("multi-day passes require more than one day")
        if not self.consent:
            raise ValueError("visitor consent is mandatory")
        if self.start_time and self.end_time and self.end_time <= self.start_time:
            raise ValueError("end_time must be after start_time")
        return self


class VisitorResponse(StrictSchema):
    """Visitor entry response."""

    id: int
    creator_id: int
    approver_id: Optional[int]
    location_id: int
    visitor_name: str
    visitor_email: Optional[EmailStr]
    visitor_phone: str
    company: Optional[str]
    purpose: str
    visit_date: date
    end_date: date
    start_time: Optional[time]
    end_time: Optional[time]
    pass_type: PassType
    photo_metadata: dict[str, Any]
    consent: bool
    id_proof_type: Optional[str]
    id_proof_reference: Optional[str]
    access_card_number: Optional[str]
    device_certificate_id: Optional[str]
    internet_access_requested: bool
    status: VisitorStatus
    rejection_reason: Optional[str]
    created_at: datetime
    updated_at: datetime


class ApprovalRequest(StrictSchema):
    """Approval or rejection request."""

    approved: bool
    reason: Optional[str] = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def validate_rejection_reason(self) -> "ApprovalRequest":
        """Require a reason when rejecting a visitor."""
        if not self.approved and not self.reason:
            raise ValueError("reason is required when rejecting an entry")
        return self


class PasswordResetRequest(StrictSchema):
    """Request a password-reset email."""

    email: EmailStr


class PasswordResetConfirm(StrictSchema):
    """Confirm a password reset."""

    token: str = Field(min_length=20)
    new_password: str = Field(min_length=12, max_length=128)


class ReportFilters(StrictSchema):
    """Validated report query filters."""

    from_date: Optional[date] = None
    to_date: Optional[date] = None
    creator_id: Optional[int] = Field(default=None, gt=0)
    approver_id: Optional[int] = Field(default=None, gt=0)
    status: Optional[VisitorStatus] = None
    location_id: Optional[int] = Field(default=None, gt=0)
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=200)

    @model_validator(mode="after")
    def validate_range(self) -> "ReportFilters":
        """Ensure the report date range is ordered."""
        if self.from_date and self.to_date and self.to_date < self.from_date:
            raise ValueError("to_date cannot precede from_date")
        return self


class NotificationResponse(StrictSchema):
    """Notification response."""

    id: int
    type: str
    title: str
    message: str
    visitor_entry_id: Optional[int]
    is_read: bool
    is_muted: bool
    created_at: datetime
