class AppError(Exception):
    """Base for errors that should reach the client as the spec's error envelope:
    { "error": { "code": ..., "message": ... } }. Raise a specific subclass so the
    exception handler in main.py can map it to the right HTTP status."""

    def __init__(self, message: str, code: str = "internal_error", status_code: int = 500):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code


class UpstreamUnavailableError(AppError):
    def __init__(self, message: str):
        super().__init__(message, code="upstream_unavailable", status_code=503)
