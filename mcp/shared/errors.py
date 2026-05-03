"""Unified error types for SimFlow MCP servers."""


class SimFlowError(Exception):
    """Base exception for SimFlow errors."""

    def __init__(self, message: str, code: str = "UNKNOWN"):
        super().__init__(message)
        self.code = code


class ValidationError(SimFlowError):
    """Input validation failed."""

    def __init__(self, message: str):
        super().__init__(message, code="VALIDATION_ERROR")


class AuthError(SimFlowError):
    """Authentication or authorization failed."""

    def __init__(self, message: str):
        super().__init__(message, code="AUTH_ERROR")


class NotFoundError(SimFlowError):
    """Requested resource not found."""

    def __init__(self, message: str):
        super().__init__(message, code="NOT_FOUND")


class ExternalServiceError(SimFlowError):
    """External service (API, HPC, database) error."""

    def __init__(self, message: str):
        super().__init__(message, code="EXTERNAL_SERVICE_ERROR")


class RetryableError(SimFlowError):
    """Error that may succeed on retry."""

    def __init__(self, message: str):
        super().__init__(message, code="RETRYABLE_ERROR")
