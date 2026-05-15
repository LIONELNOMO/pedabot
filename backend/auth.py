import os
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlmodel import Session, select
from auth_models import User

SECRET_KEY = os.getenv("SECRET_KEY", "pedabot-dev-secret-key-changer-en-prod")
ALGORITHM = "HS256"
TOKEN_EXPIRE_DAYS = 7

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_token(user_id: int, email: str, nom: str, role: str = 'prof') -> str:
    expire = datetime.utcnow() + timedelta(days=TOKEN_EXPIRE_DAYS)
    payload = {"sub": str(user_id), "email": email, "nom": nom, "role": role, "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None


def get_user_by_email(session: Session, email: str) -> Optional[User]:
    return session.exec(select(User).where(User.email == email)).first()


def seed_demo_accounts(session: Session):
    demos = [
        {"email": "demo@pedabot.com",   "nom": "Prof. Demo",   "password": "demo123", "role": "prof"},
        {"email": "kamga@pedabot.com",  "nom": "M. Kamga",     "password": "demo123", "role": "prof"},
        {"email": "ngono@pedabot.com",  "nom": "Mme Ngono",    "password": "demo123", "role": "prof"},
        {"email": "eleve@pedabot.com",  "nom": "Jean-Paul",    "password": "demo123", "role": "eleve"},
        {"email": "amina@pedabot.com",  "nom": "Amina Bello",  "password": "demo123", "role": "eleve"},
    ]
    for d in demos:
        if not get_user_by_email(session, d["email"]):
            user = User(
                email=d["email"],
                nom=d["nom"],
                password_hash=hash_password(d["password"]),
                role=d["role"],
            )
            session.add(user)
    session.commit()
