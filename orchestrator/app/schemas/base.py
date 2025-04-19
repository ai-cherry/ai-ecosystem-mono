"""
Base schema models used across the application.

These models provide common response structures for API endpoints.
"""

from typing import Generic, TypeVar, List, Optional, Any, Dict
from pydantic import BaseModel, Field

# Generic type for paginated responses
T = TypeVar('T')

class StatusResponse(BaseModel):
    """
    General response model with status and optional message.
    """
    status: str = Field(..., description="Status of the operation (success, error)")
    message: Optional[str] = Field(None, description="Optional message with details")


class ErrorResponse(BaseModel):
    """
    Error response model with status, error message and optional details.
    """
    status: str = Field("error", description="Error status indicator")
    error: str = Field(..., description="Error message")
    detail: Optional[Dict[str, Any]] = Field(None, description="Optional error details")
    
    class Config:
        schema_extra = {
            "example": {
                "status": "error",
                "error": "Resource not found",
                "detail": {"resource_id": "123", "resource_type": "workflow"}
            }
        }


class PaginatedResponse(Generic[T], BaseModel):
    """
    Generic response model for paginated results.
    """
    items: List[T] = Field(..., description="List of items")
    total: int = Field(..., description="Total number of items")
    page: int = Field(1, description="Current page number")
    page_size: int = Field(..., description="Number of items per page")
    pages: int = Field(..., description="Total number of pages")
    
    @classmethod
    def create(cls, items: List[T], total: int, page: int, page_size: int) -> "PaginatedResponse[T]":
        """
        Create a paginated response from a list of items and pagination info.
        
        Args:
            items: The items for the current page
            total: Total number of items across all pages
            page: Current page number (1-based)
            page_size: Number of items per page
            
        Returns:
            A populated PaginatedResponse
        """
        pages = (total + page_size - 1) // page_size if page_size > 0 else 0
        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            pages=pages
        )
