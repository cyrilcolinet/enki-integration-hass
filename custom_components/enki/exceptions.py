"""Enki API exceptions."""


class EnkiError(Exception):
    """Base Enki error."""


class EnkiAuthError(EnkiError):
    """Invalid credentials or expired session."""


class EnkiConnectionError(EnkiError):
    """Network or upstream API failure."""

    def __init__(
        self,
        message: str,
        *,
        status: int | None = None,
        service: str | None = None,
        report: dict[str, object] | None = None,
    ) -> None:
        super().__init__(message)
        self.status = status
        self.service = service
        self.report = report


class EnkiApiNotFoundError(EnkiConnectionError):
    """HTTP 404 from an Enki microservice."""
