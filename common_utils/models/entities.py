from datetime import datetime
from typing import (
    Any,
    Dict,
    List,
    Optional,
)

from pydantic import BaseModel, ConfigDict, Field, field_validator

from common_utils.timezone_utils import get_utc_now

# BASE MODELS AND UTILITIES
# =============================================================================


class FilterAttribute(BaseModel):
    """Filter attribute for model filtering across the system."""

    key: str = Field(..., description="Attribute key")
    value: Any = Field(..., description="Attribute value")
    operator: str = Field(default="eq", description="Comparison operator")
    is_required: bool = Field(
        default=False, description="Whether this attribute is required"
    )


# =============================================================================
# PRISM AND INSTRUMENTATION MODELS
# =============================================================================


class BasePrismModel(BaseModel):
    """Base model with timestamp fields."""

    created_at: str = Field(
        default_factory=lambda: get_utc_now().strftime("%Y-%m-%dT%H:%M:%S%z"),
        description="Creation timestamp",
    )
    updated_at: str = Field(
        default_factory=lambda: get_utc_now().strftime("%Y-%m-%dT%H:%M:%S%z"),
        description="Last update timestamp",
    )

    model_config = ConfigDict(validate_assignment=True, extra="forbid")

    @field_validator("created_at", "updated_at", mode="before")
    @classmethod
    def validate_datetime(cls, v: Any) -> str:
        """Validate and convert datetime fields to strings."""
        if v is None:
            return get_utc_now().strftime("%Y-%m-%dT%H:%M:%S%z")
        if isinstance(v, str):
            try:
                # Validate the string format
                datetime.fromisoformat(v.replace("Z", "+00:00"))
                return v
            except ValueError:
                return get_utc_now().strftime("%Y-%m-%dT%H:%M:%S%z")
        elif isinstance(v, datetime):
            return v.strftime("%Y-%m-%dT%H:%M:%S%z")
        return get_utc_now().strftime("%Y-%m-%dT%H:%M:%S%z")

    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary."""
        data = self.model_dump(exclude_none=True, exclude={"id"})
        if hasattr(self, "id") and self.id is not None:
            data["_id"] = str(self.id)
        return data


# =============================================================================
# FILE OPERATIONS MODELS
# =============================================================================


class FileListResponse(BaseModel):
    """Response model for listing files in directories"""

    input_files: List[str] = Field(description="List of files in input directory")
    output_files: List[str] = Field(description="List of files in output directory")
    config_files: List[str] = Field(description="List of files in config directory")


class UploadResponse(BaseModel):
    """Response model for file upload operations"""

    success: bool = Field(description="Whether the upload was successful")
    message: str = Field(description="Upload status message")
    file_path: str = Field(description="Path where the file was saved")


class FileDeleteResponse(BaseModel):
    """Response model for file delete operations"""

    success: bool = Field(description="Whether the deletion was successful")
    message: str = Field(description="Deletion status message")
    file_path: str = Field(description="Path of the deleted file")


class EchoRequest(BaseModel):
    """Request model for echo endpoint"""

    message: str = Field(description="Message to echo")
    data: Optional[Dict[str, Any]] = Field(
        default=None, description="Additional data to include"
    )
    headers: Optional[Dict[str, str]] = Field(
        default=None, description="Custom headers to send with the request"
    )
    query_params: Optional[Dict[str, str]] = Field(
        default=None, description="Query parameters to append to the URL"
    )


class EchoResponse(BaseModel):
    """Response model for echo endpoint"""

    original_request: EchoRequest = Field(
        description="The original request that was sent"
    )
    echo_response: Dict[str, Any] = Field(description="Response from the echo service")
    success: bool = Field(description="Whether the echo request was successful")
    error_message: Optional[str] = Field(
        default=None, description="Error message if the request failed"
    )
