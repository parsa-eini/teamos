"""Stable API error codes and exception types.

Codes match `AI_BUILD_SPEC.md` section 37. Handlers in `error_handlers.py` map these to the
error envelope in section 24.
"""


class AppError(Exception):
    """Base error for domain and application failures that the API should report."""

    def __init__(self, message: str, *, code: str, status_code: int) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code


class InvalidCredentialsError(AppError):
    def __init__(self, message: str = "Invalid credentials") -> None:
        super().__init__(message, code="INVALID_CREDENTIALS", status_code=401)


class UnauthorizedError(AppError):
    def __init__(self, message: str = "Authentication required") -> None:
        super().__init__(message, code="UNAUTHORIZED", status_code=401)


class ForbiddenError(AppError):
    def __init__(self, message: str = "You do not have permission to perform this action") -> None:
        super().__init__(message, code="FORBIDDEN", status_code=403)


class ResourceNotFoundError(AppError):
    def __init__(self, message: str = "Resource not found") -> None:
        super().__init__(message, code="RESOURCE_NOT_FOUND", status_code=404)


class ValidationError(AppError):
    def __init__(self, message: str = "Request validation failed") -> None:
        super().__init__(message, code="VALIDATION_ERROR", status_code=422)


class ResourceAlreadyExistsError(AppError):
    def __init__(self, message: str = "Resource already exists") -> None:
        super().__init__(message, code="RESOURCE_ALREADY_EXISTS", status_code=409)


class OrganizationAccessDeniedError(AppError):
    def __init__(self, message: str = "Access to this organization is denied") -> None:
        super().__init__(message, code="ORGANIZATION_ACCESS_DENIED", status_code=403)
