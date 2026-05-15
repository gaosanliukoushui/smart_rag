"""Common schemas."""

from typing import Generic, TypeVar, Optional, Any
from pydantic import BaseModel, Field


T = TypeVar("T")


class ResponseBase(BaseModel):
    """Base response schema."""

    success: bool = True
    message: Optional[str] = None


class DataResponse(ResponseBase, Generic[T]):
    """Generic data response."""

    data: Optional[T] = None


class PaginatedResponse(ResponseBase):
    """Paginated response schema."""

    total: int = 0
    page: int = 1
    page_size: int = 20
    items: list = Field(default_factory=list)


class ErrorResponse(BaseModel):
    """Error response schema."""

    success: bool = False
    error_code: str
    error_message: str
    details: Optional[Any] = None
