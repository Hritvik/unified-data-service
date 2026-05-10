"""
Model bridge rest_client for route planning.
"""


class ModelBridgeException(Exception):
    """Exception thrown when a route plan is invalid."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)


class InvalidRoutePlanException(ModelBridgeException):
    """Exception thrown when a route plan is invalid."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)
