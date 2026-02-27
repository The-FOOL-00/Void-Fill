"""Custom exception hierarchy for the VoidFill application."""

from typing import Any, Optional
from uuid import UUID


class VoidFillError(Exception):
    """Base exception for all VoidFill application errors."""

    def __init__(self, message: str = "An unexpected error occurred", code: str = "INTERNAL_ERROR") -> None:
        self.message = message
        self.code = code
        super().__init__(self.message)


class NotFoundError(VoidFillError):
    """Raised when a requested resource does not exist."""

    def __init__(self, resource: str, resource_id: Optional[UUID] = None) -> None:
        identifier = f" with id '{resource_id}'" if resource_id else ""
        super().__init__(
            message=f"{resource}{identifier} not found",
            code="NOT_FOUND",
        )


class ConflictError(VoidFillError):
    """Raised when an operation conflicts with existing state."""

    def __init__(self, message: str = "Resource conflict") -> None:
        super().__init__(message=message, code="CONFLICT")


class ValidationError(VoidFillError):
    """Raised when input data fails business-rule validation."""

    def __init__(self, message: str = "Validation failed", details: Optional[dict[str, Any]] = None) -> None:
        self.details = details or {}
        super().__init__(message=message, code="VALIDATION_ERROR")


class AuthenticationError(VoidFillError):
    """Raised when authentication credentials are missing or invalid."""

    def __init__(self, message: str = "Authentication required") -> None:
        super().__init__(message=message, code="AUTHENTICATION_ERROR")


class AuthorizationError(VoidFillError):
    """Raised when the authenticated user lacks permission."""

    def __init__(self, message: str = "Permission denied") -> None:
        super().__init__(message=message, code="AUTHORIZATION_ERROR")


class VoiceProcessingError(VoidFillError):
    """Raised when voice transcription or processing fails."""

    def __init__(self, message: str = "Voice processing failed") -> None:
        super().__init__(message=message, code="VOICE_PROCESSING_ERROR")


class ExternalServiceError(VoidFillError):
    """Raised when an external service call fails."""

    def __init__(self, service: str, message: str = "External service unavailable") -> None:
        self.service = service
        super().__init__(message=f"{service}: {message}", code="EXTERNAL_SERVICE_ERROR")
