"""Custom error type used by services, turned into JSON responses in main.py."""


class AppError(Exception):
    """
    A business rule error that should be returned to the client.

    Args:
        message: Human readable explanation (shown in a toast on the frontend).
        status_code: HTTP status code to return, 400 by default.
    """

    def __init__(self, message: str, status_code: int = 400) -> None:
        """
        Store the message and HTTP status code.

        Args:
            message (str): Error message shown to the client.
            status_code (int): HTTP status code to return.
        """
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class NotFoundError(AppError):
    """Raised when a requested object does not exist."""

    def __init__(self, message: str = "Not found") -> None:
        """
        Create a 404 error.

        Args:
            message (str): Error message shown to the client.
        """
        super().__init__(message, 404)


class ForbiddenError(AppError):
    """Raised when the user is not allowed to do something."""

    def __init__(self, message: str = "You do not have permission to perform this action") -> None:
        """
        Create a 403 error.

        Args:
            message (str): Error message shown to the client.
        """
        super().__init__(message, 403)
