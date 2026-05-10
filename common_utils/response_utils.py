import json
from typing import Any, Tuple, Type, TypeVar

from fastapi.responses import JSONResponse

from common_utils.exceptions.http_exceptions import (
    BadRequestException,
    DuplicateRequestException,
    FailedDependencyException,
    InternalServerErrorException,
    LockedException,
    NotFoundException,
)

T = TypeVar("T")


class ResponseUtils:
    """Utility methods for handling HTTP responses."""

    _object_mapper = None  # Static object mapper like Java version

    @classmethod
    def _get_object_mapper(cls) -> json.JSONDecoder:
        """Get the object mapper instance (lazy initialization)."""
        if cls._object_mapper is None:
            cls._object_mapper = json
        return cls._object_mapper

    @staticmethod
    def is_2xx(http_status_code: int) -> bool:
        """Check if status code is in 2xx range."""
        return 200 <= http_status_code < 300

    @staticmethod
    def is_4xx(http_status_code: int) -> bool:
        """Check if status code is in 4xx range."""
        return 400 <= http_status_code < 500

    @classmethod
    def command_response_handler_error_string(
        cls, resp: Tuple[int, str], response_type: Type[T]
    ) -> T:
        """Handle response with error string - allows 2xx and 4xx status codes."""
        status_code, response_body = resp

        if cls.is_2xx(status_code) or cls.is_4xx(status_code):
            return cls._parse_response_body(response_body, response_type)
        else:
            raise InternalServerErrorException(status_code, response_body)

    @classmethod
    def command_response_handler_v3(
        cls, resp: Tuple[int, str], response_type: Type[T]
    ) -> T:
        """Handle response v3 - throws specific rest_client for different status codes."""
        status_code, response_body = resp

        if cls.is_2xx(status_code):
            return cls._parse_response_body(response_body, response_type)
        elif cls.is_4xx(status_code):
            raise cls._handle_4xx_errors(status_code, response_body)
        else:
            raise InternalServerErrorException(status_code, response_body)

    @classmethod
    def _parse_response_body(cls, response_body: str, response_type: Type[T]) -> T:
        """Parse response body to specified type."""
        if not response_body or response_body.strip() == "":
            if response_type is str:
                return ""  # type: ignore
            elif response_type is dict:
                return {}  # type: ignore
            elif response_type is bytes:
                return b""  # type: ignore
            else:
                raise ValueError("Cannot parse empty response body for custom type")

        object_mapper = cls._get_object_mapper()

        if response_type is str:
            return response_body  # type: ignore
        elif response_type is dict:
            return object_mapper.loads(response_body)  # type: ignore
        elif response_type is bytes:
            return response_body.encode("utf-8")  # type: ignore
        else:
            # For custom types, try to deserialize JSON
            data = object_mapper.loads(response_body)
            return response_type(**data)

    @staticmethod
    def _handle_4xx_errors(status_code: int, response_body: str) -> Exception:
        """Handle 4xx errors with specific exception types."""
        if status_code == 423:
            return LockedException(status_code, response_body)
        elif status_code == 424:
            return FailedDependencyException(status_code, response_body)
        elif status_code == 404:
            return NotFoundException(status_code, response_body)
        elif status_code == 409:
            return DuplicateRequestException(status_code, response_body)
        else:
            return BadRequestException(status_code, response_body)

    # Keep backward compatibility methods
    @staticmethod
    def command_response_handler(response_text: str, response_type: Type[T]) -> T:
        """Handle response conversion to specified type (backward compatibility)."""
        if response_type is str:
            return response_text  # type: ignore
        elif response_type is dict:
            return json.loads(response_text)  # type: ignore
        elif response_type is bytes:
            return response_text.encode("utf-8")  # type: ignore
        else:
            # For custom types, try to deserialize JSON
            data = json.loads(response_text)
            return response_type(**data)


def create_response(
    data: Any = None, message: str = "Success", status_code: int = 200, **kwargs
) -> JSONResponse:
    """
    Create a standardized JSON response.

    Args:
        data: Response data
        message: Response message
        status_code: HTTP status code
        **kwargs: Additional fields to include in response

    Returns:
        JSONResponse with standardized format
    """
    response_data = {"message": message, "status_code": status_code, **kwargs}

    if data is not None:
        response_data["data"] = data

    return JSONResponse(content=response_data, status_code=status_code)
