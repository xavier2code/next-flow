from fastapi import HTTPException


class AppException(HTTPException):
    """Base application exception with structured error code and message."""

    def __init__(
        self,
        status_code: int,
        error_code: str,
        message: str,
    ) -> None:
        self.error_code = error_code
        self.message = message
        super().__init__(status_code=status_code, detail=message)


class NotFoundException(AppException):
    """Resource not found (404)."""

    def __init__(self, message: str = "Resource not found") -> None:
        super().__init__(status_code=404, error_code="NOT_FOUND", message=message)


class UnauthorizedException(AppException):
    """Authentication required (401)."""

    def __init__(self, message: str = "Not authenticated") -> None:
        super().__init__(
            status_code=401,
            error_code="UNAUTHORIZED",
            message=message,
        )


class ForbiddenException(AppException):
    """Insufficient permissions (403)."""

    def __init__(self, message: str = "Forbidden") -> None:
        super().__init__(
            status_code=403,
            error_code="FORBIDDEN",
            message=message,
        )


class BadRequestException(AppException):
    """Invalid request data (400)."""

    def __init__(self, message: str = "Bad request") -> None:
        super().__init__(
            status_code=400,
            error_code="BAD_REQUEST",
            message=message,
        )


class ConflictException(AppException):
    """Resource conflict (409)."""

    def __init__(self, message: str = "Conflict") -> None:
        super().__init__(
            status_code=409,
            error_code="CONFLICT",
            message=message,
        )
