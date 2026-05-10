class RetryableHttpException(Exception):
    """Exception thrown when an HTTP request should be retried."""

    def __init__(self, status_code: int, response_body: str):
        self.status_code = status_code
        self.response_body = response_body
        super().__init__(f"Retryable HTTP error: {status_code} - {response_body}")
