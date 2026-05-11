from typing import Optional
from datetime import datetime
from sqlmodel import SQLModel, Field


class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True)
    nom: str
    password_hash: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


class RegisterRequest(SQLModel):
    email: str
    nom: str
    password: str


class LoginRequest(SQLModel):
    email: str
    password: str


class UserOut(SQLModel):
    id: int
    email: str
    nom: str


class AuthResponse(SQLModel):
    token: str
    user: UserOut
