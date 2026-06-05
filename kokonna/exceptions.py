"""Exceptions for the KoKonna OpenAPI client."""


class KokonnaError(Exception):
    """Base error for the KoKonna client."""


class KokonnaAuthError(KokonnaError):
    """Raised when the API key is invalid or not associated with a device.

    Maps to the server response ``"can not find robot <apikey>"`` (HTTP 500)
    and any 401/403 responses.
    """


class KokonnaNotFoundError(KokonnaError):
    """Raised when a referenced image / method does not exist on the device.

    Maps to ``"image not found"`` (HTTP 500) and HTTP 404 responses for
    unknown methods.
    """


class KokonnaRateLimitError(KokonnaError):
    """Raised when the per-device rate limit (20 req/min) is exceeded.

    Maps to HTTP 429 with the body ``"Too many requests, please try again
    later."``.
    """


class KokonnaServerError(KokonnaError):
    """Raised for any other 5xx response or transport-level failure."""
