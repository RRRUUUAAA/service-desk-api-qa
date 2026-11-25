from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator


class ApiModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class UserRole(str, Enum):
    employee = "employee"
    technician = "technician"
    admin = "admin"


class TicketPriority(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"


class TicketStatus(str, Enum):
    open = "open"
    assigned = "assigned"
    in_progress = "in_progress"
    resolved = "resolved"
    closed = "closed"


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=32)
    password: str = Field(min_length=1, max_length=128)


class UserCreate(BaseModel):
    username: str = Field(
        min_length=3,
        max_length=32,
        pattern=r"^[A-Za-z0-9_.-]+$",
    )
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    role: UserRole = UserRole.employee


class UserOut(ApiModel):
    id: int
    username: str
    email: EmailStr
    role: UserRole
    is_active: bool
    created_at: datetime


class UserRoleUpdate(BaseModel):
    role: UserRole


class UserActiveUpdate(BaseModel):
    is_active: bool


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserOut


class PaginatedUsers(BaseModel):
    items: list[UserOut]
    total: int
    page: int
    page_size: int


class TicketCreate(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=2000)
    priority: TicketPriority = TicketPriority.medium

    @field_validator("title")
    @classmethod
    def title_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("title must not be blank")
        return value


class TicketUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    priority: TicketPriority | None = None

    @model_validator(mode="before")
    @classmethod
    def reject_explicit_nulls(cls, data):
        if isinstance(data, dict):
            for field in ("title", "description", "priority"):
                if field in data and data[field] is None:
                    raise ValueError(f"{field} must not be null")
        return data

    @field_validator("title")
    @classmethod
    def updated_title_must_not_be_blank(cls, value: str | None) -> str | None:
        if value is None:
            return value
        value = value.strip()
        if not value:
            raise ValueError("title must not be blank")
        return value

    @model_validator(mode="after")
    def at_least_one_field(self) -> "TicketUpdate":
        if not self.model_fields_set:
            raise ValueError("at least one field must be provided")
        return self


class TicketAssign(BaseModel):
    assignee_id: int = Field(gt=0)


class TicketStatusUpdate(BaseModel):
    status: TicketStatus


class TicketOut(ApiModel):
    id: int
    title: str
    description: str
    priority: TicketPriority
    status: TicketStatus
    created_by: int
    assignee_id: int | None
    created_at: datetime
    updated_at: datetime


class TicketEventOut(ApiModel):
    id: int
    ticket_id: int
    actor_id: int
    event_type: str
    from_status: str | None
    to_status: str
    created_at: datetime


class PaginatedTickets(BaseModel):
    items: list[TicketOut]
    total: int
    page: int
    page_size: int


class TicketDetail(TicketOut):
    events: list[TicketEventOut]
