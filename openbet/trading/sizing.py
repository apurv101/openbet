"""
Position sizing calculations for trading strategy.
"""


def calculate_position_size(
    divergence: float,
    base_amount: int = 10,
    max_position: int = 100,
    scaling_factor: float = 1.5,
) -> int:
    """
    Calculate position size proportional to divergence.

    Formula: position = base_amount * (divergence / 0.05) ^ scaling_factor

    Args:
        divergence: Absolute divergence (e.g., 0.08 for 8%)
        base_amount: Minimum position size for 5% divergence (default: 10)
        max_position: Maximum position size cap (default: 100)
        scaling_factor: Controls aggressiveness - higher = more aggressive (default: 1.5)

    Returns:
        Integer contract count

    Examples:
        >>> calculate_position_size(0.05)  # 5% divergence
        10
        >>> calculate_position_size(0.10)  # 10% divergence
        28
        >>> calculate_position_size(0.15)  # 15% divergence
        52
        >>> calculate_position_size(0.20)  # 20% divergence
        80
        >>> calculate_position_size(0.30)  # 30% divergence (capped)
        100
    """
    if divergence <= 0:
        return 0

    # Calculate raw position based on divergence
    # Reference divergence is 5% (0.05) which maps to base_amount
    ratio = divergence / 0.05
    raw_position = base_amount * (ratio ** scaling_factor)

    # Round to nearest integer and cap at maximum
    position = min(int(round(raw_position)), max_position)

    return position


def calculate_expected_profit(
    quantity: int,
    entry_price: float,
    target_price: float,
) -> float:
    """
    Calculate expected profit for a position.

    Args:
        quantity: Number of contracts
        entry_price: Entry price per contract
        target_price: Expected target price (consensus probability)

    Returns:
        Expected profit in dollars

    Example:
        >>> calculate_expected_profit(10, 0.06, 0.07)
        1.0
    """
    price_diff = target_price - entry_price
    profit = quantity * price_diff
    return round(profit, 2)


def calculate_risk_reward_ratio(
    entry_price: float,
    target_price: float,
    stop_price: float,
) -> float:
    """
    Calculate risk-reward ratio.

    Args:
        entry_price: Entry price per contract
        target_price: Target price (profit)
        stop_price: Stop loss price (loss)

    Returns:
        Risk-reward ratio (positive is favorable)

    Example:
        >>> calculate_risk_reward_ratio(0.06, 0.07, 0.05)
        1.0
    """
    reward = abs(target_price - entry_price)
    risk = abs(entry_price - stop_price)

    if risk == 0:
        return float('inf')

    return reward / risk
