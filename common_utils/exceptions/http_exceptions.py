class HTTPException(Exception):
    """Base class for HTTP rest_client."""

    def __init__(self, status_code: int, response_body: str):
        self.status_code = status_code
        self.response_body = response_body
        super().__init__(f"HTTP {status_code}: {response_body}")


class InternalServerErrorException(HTTPException):
    """Exception for 5xx server errors."""

    pass


class BadRequestException(HTTPException):
    """Exception for 4xx client errors."""

    pass


class NotFoundException(HTTPException):
    """Exception for 404 Not Found."""

    pass


class DuplicateRequestException(HTTPException):
    """Exception for 409 Conflict."""

    pass


class LockedException(HTTPException):
    """Exception for 423 Locked."""

    pass


class FailedDependencyException(HTTPException):
    """Exception for 424 Failed Dependency."""

    pass
