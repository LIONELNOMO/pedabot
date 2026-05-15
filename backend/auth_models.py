from typing import Optional
from datetime import datetime
from sqlmodel import SQLModel, Field, Column
import sqlalchemy as sa


class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str        = Field(unique=True, index=True)
    nom: str
    password_hash: str
    role: str         = Field(default='prof', sa_column=Column(sa.String, server_default='prof'))
    created_at: datetime = Field(default_factory=datetime.utcnow)


class RegisterRequest(SQLModel):
    email: str
    nom: str
    password: str
    role: str = 'prof'


class LoginRequest(SQLModel):
    email: str
    password: str


class UserOut(SQLModel):
    id: int
    email: str
    nom: str
    role: str = 'prof'


class AuthResponse(SQLModel):
    token: str
    user: UserOut


# ══════════════════════════════════════
#  PARTAGE EXERCICES ÉLÈVES
# ══════════════════════════════════════

class Assignment(SQLModel, table=True):
    __tablename__ = "assignment"
    id: Optional[int]          = Field(default=None, primary_key=True)
    teacher_id: int
    teacher_nom: str
    eleve_email: str           = Field(index=True)
    titre: str
    contenu: str               = Field(sa_column=Column(sa.Text))
    lang: str                  = ""
    difficulty: str            = ""
    reponses: Optional[str]    = Field(default=None, sa_column=Column(sa.Text))
    submitted_at: Optional[datetime] = None
    corrige_visible: bool      = False
    created_at: datetime       = Field(default_factory=datetime.utcnow)


class ExerciseDB(SQLModel, table=True):
    __tablename__ = "exercisedb"
    id: Optional[int]   = Field(default=None, primary_key=True)
    teacher_id: int
    teacher_nom: str
    titre: str
    contenu: str        = Field(sa_column=Column(sa.Text))
    lang: str           = ""
    difficulty: str     = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)


class SharedLink(SQLModel, table=True):
    __tablename__ = "sharedlink"
    token: str          = Field(primary_key=True)
    exercise_id: int
    teacher_id: int
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Submission(SQLModel, table=True):
    __tablename__ = "submission"
    id: Optional[int]   = Field(default=None, primary_key=True)
    token: str          = Field(index=True)
    eleve_prenom: str
    reponses: str       = Field(sa_column=Column(sa.Text))
    submitted_at: datetime = Field(default_factory=datetime.utcnow)
