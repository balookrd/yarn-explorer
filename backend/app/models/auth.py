from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class Role(str, Enum):
    READER = "reader"
    WRITER = "writer"
    ADMIN = "admin"


class LoginRequest(BaseModel):
    username: str
    password: str


class UserSession(BaseModel):
    username: str
    display_name: str
    email: Optional[str] = None
    groups: List[str] = Field(default_factory=list)
    auth_method: str = "mock"  # ldap, kerberos, mock
    is_admin: bool = False
    system_role: Role = Role.READER


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserSession
