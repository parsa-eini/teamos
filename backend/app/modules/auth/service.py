"""Registration and login use cases."""

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.common.exceptions import InvalidCredentialsError, ResourceAlreadyExistsError
from app.core.config import Settings
from app.core.security import create_access_token, hash_password, verify_password
from app.modules.organizations.service import create_organization_with_owner
from app.modules.users import repository as users_repository
from app.modules.users.models import User
from app.modules.users.schemas import RegisterRequest


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def register_user(session: Session, payload: RegisterRequest) -> User:
    email = _normalize_email(str(payload.email))
    if users_repository.get_by_email(session, email) is not None:
        raise ResourceAlreadyExistsError("A user with this email already exists")

    user = User(
        email=email,
        password_hash=hash_password(payload.password),
        first_name=payload.first_name.strip(),
        last_name=payload.last_name.strip(),
        is_active=True,
    )
    users_repository.add(session, user)
    session.flush()

    create_organization_with_owner(
        session,
        name=payload.organization_name,
        owner_user_id=user.id,
    )

    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise ResourceAlreadyExistsError("A user with this email already exists") from exc

    session.refresh(user)
    return user


def login_user(session: Session, email: str, password: str, settings: Settings) -> str:
    user = users_repository.get_by_email(session, _normalize_email(email))
    if user is None or not user.is_active or not verify_password(password, user.password_hash):
        raise InvalidCredentialsError()

    return create_access_token(user.id, settings)
