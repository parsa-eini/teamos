"""Organization API schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.modules.organizations.models import OrganizationRole

_SLUG_PATTERN = r"^[a-z0-9]+(?:-[a-z0-9]+)*$"


class OrganizationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    slug: str
    created_at: datetime
    updated_at: datetime


class OrganizationUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    slug: str | None = Field(default=None, min_length=1, max_length=100, pattern=_SLUG_PATTERN)

    @field_validator("name")
    @classmethod
    def name_must_not_be_blank(cls, value: str | None) -> str | None:
        if value is None:
            return value
        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be blank")
        return stripped


class OrganizationMemberRead(BaseModel):
    user_id: UUID
    email: EmailStr
    first_name: str
    last_name: str
    role: OrganizationRole
    created_at: datetime


class OrganizationMemberCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    role: OrganizationRole = OrganizationRole.MEMBER

    @field_validator("first_name", "last_name")
    @classmethod
    def names_must_not_be_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be blank")
        return stripped

    @field_validator("role")
    @classmethod
    def role_must_not_be_owner(cls, value: OrganizationRole) -> OrganizationRole:
        if value == OrganizationRole.OWNER:
            raise ValueError("cannot assign OWNER; the registering user is the owner")
        return value
