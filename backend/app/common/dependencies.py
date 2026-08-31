"""FastAPI dependencies shared across modules.

Organization context arrives with Stage 4.
"""

from app.modules.auth.dependencies import get_current_user

__all__ = ["get_current_user"]
