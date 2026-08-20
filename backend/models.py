// backend/models.py

"""Pydantic models for users and sessions used by the authentication system."""

from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from pydantic import BaseModel, Field, EmailStr


class User(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    email: EmailStr
    password_hash: str
    name: Optional[str] = None
    role: str = "staff"  # staff, admin, super_admin
    active: bool = True
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    last_login_at: Optional[str] = None


class Session(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    user_id: str
    role: str
    expires_at: str = Field(default_factory=lambda: (datetime.now(timezone.utc) + __import__('datetime').timedelta(hours=8)).isoformat())
    csrf_token: str = Field(default_factory=lambda: str(uuid4()))
