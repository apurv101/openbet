"""Exceptions for Kalshi API operations."""


class KalshiError(Exception):
    """Base exception for Kalshi API errors."""

    pass


class KalshiAuthenticationError(KalshiError):
    """Authentication failed."""

    pass


class KalshiAPIError(KalshiError):
    """API request failed."""

    def __init__(self, message: str, status_code: int = None, response_data: dict = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_data = response_data


class KalshiRateLimitError(KalshiError):
    """Rate limit exceeded."""

    pass


class KalshiMarketNotFoundError(KalshiError):
    """Market not found."""

    pass


class KalshiOrderError(KalshiError):
    """Order placement failed."""

    pass
