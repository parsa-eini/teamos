"""FastAPI dependencies shared across modules."""

from app.modules.auth.dependencies import get_current_user
from app.modules.organizations.dependencies import get_organization_context

__all__ = ["get_current_user", "get_organization_context"]
