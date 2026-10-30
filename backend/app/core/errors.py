# OWNER: P1
from typing import Any, Optional

from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from app.schemas.common import ErrorDetail, ErrorEnvelope


class FestOSError(Exception):
    def __init__(
        self,
        message: str,
        code: str = "INTERNAL",
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: Any = None
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details

class ValidationError(FestOSError):
    def __init__(self, message: str = "Validation failed", details: Any = None):
        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details=details
        )

class NotFoundError(FestOSError):
    def __init__(self, message: str = "Resource not found", details: Any = None):
        super().__init__(
            message=message,
            code="NOT_FOUND",
            status_code=status.HTTP_404_NOT_FOUND,
            details=details
        )

class ForbiddenError(FestOSError):
    def __init__(self, message: str = "Access forbidden", details: Any = None):
        super().__init__(
            message=message,
            code="FORBIDDEN",
            status_code=status.HTTP_403_FORBIDDEN,
            details=details
        )

class UnauthenticatedError(FestOSError):
    def __init__(self, message: str = "Authentication required", details: Any = None):
        super().__init__(
            message=message,
            code="UNAUTHENTICATED",
            status_code=status.HTTP_401_UNAUTHORIZED,
            details=details
        )

class VersionConflictError(FestOSError):
    def __init__(self, message: str = "Version conflict detected", details: Any = None):
        super().__init__(
            message=message,
            code="VERSION_CONFLICT",
            status_code=status.HTTP_409_CONFLICT,
            details=details
        )

class AlreadyIssuedError(FestOSError):
    def __init__(self, message: str = "Resource already issued", details: Any = None):
        super().__init__(
            message=message,
            code="ALREADY_ISSUED",
            status_code=status.HTTP_409_CONFLICT,
            details=details
        )

class ConstraintViolationError(FestOSError):
    def __init__(self, message: str = "Constraint violation", details: Any = None):
        super().__init__(
            message=message,
            code="CONSTRAINT_VIOLATION",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details=details
        )

class ApprovalRequiredError(FestOSError):
    def __init__(self, message: str = "Action requires higher approval", details: Any = None):
        super().__init__(
            message=message,
            code="APPROVAL_REQUIRED",
            status_code=status.HTTP_202_ACCEPTED,
            details=details
        )

class RateLimitedError(FestOSError):
    def __init__(self, message: str = "Rate limit exceeded", details: Any = None):
        super().__init__(
            message=message,
            code="RATE_LIMITED",
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            details=details
        )

def make_error_response(
    code: str,
    message: str,
    status_code: int,
    details: Any = None,
    request_id: Optional[str] = None
) -> JSONResponse:
    envelope = ErrorEnvelope(
        error=ErrorDetail(
            code=code,
            message=message,
            details=details,
            request_id=request_id
        )
    )
    return JSONResponse(status_code=status_code, content=envelope.model_dump())

async def festos_exception_handler(request: Request, exc: FestOSError) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None)
    return make_error_response(
        code=exc.code,
        message=exc.message,
        status_code=exc.status_code,
        details=exc.details,
        request_id=request_id
    )

async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None)
    return make_error_response(
        code="VALIDATION_ERROR",
        message="Request validation error",
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        details=exc.errors(),
        request_id=request_id
    )

async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None)
    return make_error_response(
        code="INTERNAL",
        message=f"Database error: {str(exc)}",
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        details=None,
        request_id=request_id
    )

async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None)
    return make_error_response(
        code="INTERNAL",
        message=str(exc) or "Internal server error",
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        details=None,
        request_id=request_id
    )
