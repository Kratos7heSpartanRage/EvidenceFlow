from typing import Any

from fastapi import status


class AppError(Exception):
    """Base application exception mapping to standard error envelope."""

    def __init__(
        self,
        message: str,
        code: str = "INTERNAL_ERROR",
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: dict[str, Any] | None = None,
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}

    def to_envelope(self) -> dict[str, Any]:
        return {
            "error": {
                "code": self.code,
                "message": self.message,
                "details": self.details,
            }
        }


class NotFoundError(AppError):
    def __init__(
        self, message: str, code: str = "NOT_FOUND", details: dict[str, Any] | None = None
    ):
        super().__init__(
            message=message,
            code=code,
            status_code=status.HTTP_404_NOT_FOUND,
            details=details,
        )


class ConflictError(AppError):
    def __init__(self, message: str, code: str = "CONFLICT", details: dict[str, Any] | None = None):
        super().__init__(
            message=message,
            code=code,
            status_code=status.HTTP_409_CONFLICT,
            details=details,
        )


class ValidationError(AppError):
    def __init__(
        self, message: str, code: str = "VALIDATION_ERROR", details: dict[str, Any] | None = None
    ):
        super().__init__(
            message=message,
            code=code,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details=details,
        )


class ImmutableError(ConflictError):
    def __init__(self, message: str = "Resource is frozen/immutable and cannot be modified"):
        super().__init__(message=message, code="IMMUTABLE_RESOURCE")
