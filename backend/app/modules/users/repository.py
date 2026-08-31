"""Persistence helpers for User."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.users.models import User


def get_by_id(session: Session, user_id: UUID) -> User | None:
    return session.get(User, user_id)


def get_by_email(session: Session, email: str) -> User | None:
    return session.scalar(select(User).where(User.email == email))


def add(session: Session, user: User) -> User:
    session.add(user)
    return user
