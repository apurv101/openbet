"""Helper utilities for Openbet."""

import time
from functools import wraps
from typing import Any, Callable, Optional


def retry_on_exception(
    max_retries: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple = (Exception,),
):
    """Decorator to retry function on exception.

    Args:
        max_retries: Maximum number of retry attempts
        delay: Initial delay between retries in seconds
        backoff: Backoff multiplier for delay
        exceptions: Tuple of exceptions to catch

    Returns:
        Decorated function
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            current_delay = delay
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e

                    if attempt < max_retries:
                        print(
                            f"Attempt {attempt + 1}/{max_retries + 1} failed: {e}. "
                            f"Retrying in {current_delay}s..."
                        )
                        time.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        print(f"All {max_retries + 1} attempts failed.")

            raise last_exception

        return wrapper

    return decorator


def format_price(price: Optional[float]) -> str:
    """Format price for display.

    Args:
        price: Price value

    Returns:
        Formatted price string
    """
    if price is None:
        return "N/A"
    return f"${price:.2f}"


def format_percentage(value: Optional[float]) -> str:
    """Format percentage for display.

    Args:
        value: Percentage value (0-1)

    Returns:
        Formatted percentage string
    """
    if value is None:
        return "N/A"
    return f"{value * 100:.1f}%"


def validate_side(side: str) -> str:
    """Validate and normalize bet side.

    Args:
        side: Side string ("yes" or "no")

    Returns:
        Normalized side string

    Raises:
        ValueError: If side is invalid
    """
    side_lower = side.lower()
    if side_lower not in ["yes", "no"]:
        raise ValueError(f"Invalid side: {side}. Must be 'yes' or 'no'.")
    return side_lower


def validate_action(action: str) -> str:
    """Validate and normalize bet action.

    Args:
        action: Action string ("buy" or "sell")

    Returns:
        Normalized action string

    Raises:
        ValueError: If action is invalid
    """
    action_lower = action.lower()
    if action_lower not in ["buy", "sell"]:
        raise ValueError(f"Invalid action: {action}. Must be 'buy' or 'sell'.")
    return action_lower
