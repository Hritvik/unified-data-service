from common_utils.exceptions.business_logic_exceptions import InternalServerException


class ResponseGenerationError(InternalServerException):
    """Raised when response generation fails."""

    def __init__(
        self,
        message: str,
        error_code: str = "RESPONSE_GENERATION_ERROR",
        details: dict = None,
    ):
        super().__init__(message, error_code, details)


class SimpleAgentError(Exception):
    """Raised when simple agent fails."""

    def __init__(self, message: str):
        super().__init__(message)
