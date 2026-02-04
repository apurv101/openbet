"""
Risk management filters for trading signals.
"""

from typing import Dict, List, Tuple, Any

from openbet.trading.models import RiskConfig, TradingSignal


def apply_risk_filters(
    signal: TradingSignal,
    market: Dict[str, Any],
    risk_config: RiskConfig,
) -> Tuple[bool, List[str]]:
    """
    Apply risk management filters to a trading signal.

    Args:
        signal: Trading signal to evaluate
        market: Market data dictionary
        risk_config: Risk configuration parameters

    Returns:
        Tuple of (passed: bool, warnings: List[str])

    Filters applied:
        1. Minimum liquidity check
        2. Minimum volume check
        3. Maximum position size enforcement
        4. Market status check (must be in allowed statuses)
        5. Spread check (if applicable)
    """
    warnings = []
    passed = True

    # Extract market data
    liquidity = signal.liquidity_depth or 0
    volume = signal.volume_24h or 0
    position_size = signal.recommended_quantity
    status = market.get("status", "unknown")

    # 1. Minimum liquidity check
    if liquidity < risk_config.min_liquidity:
        warnings.append(
            f"Low liquidity: {liquidity:.2f} < {risk_config.min_liquidity:.2f}"
        )
        passed = False

    # 2. Minimum volume check
    if volume < risk_config.min_volume_24h:
        warnings.append(
            f"Low 24h volume: {volume:.2f} < {risk_config.min_volume_24h:.2f}"
        )
        passed = False

    # 3. Maximum position size enforcement
    if position_size > risk_config.max_position_size:
        warnings.append(
            f"Position too large: {position_size} > {risk_config.max_position_size} (will be capped)"
        )
        # Don't fail, just warn - will be capped during sizing

    # 4. Market status check
    if status not in risk_config.allowed_statuses:
        warnings.append(
            f"Market status '{status}' not in allowed list: {risk_config.allowed_statuses}"
        )
        passed = False

    # 5. Spread check (if we have price data)
    # Calculate spread from recommended price assumptions
    if signal.market_yes_prob > 0 and signal.market_no_prob > 0:
        # Estimate spread based on YES/NO price consistency
        # For a fair market: yes_price + no_price ≈ 1.0
        # Large deviation suggests wide spread
        price_sum = signal.market_yes_prob + signal.market_no_prob
        spread_indicator = abs(price_sum - 1.0)

        if spread_indicator > risk_config.max_spread:
            warnings.append(
                f"Wide spread detected: {spread_indicator:.1%} deviation from fair pricing"
            )
            passed = False

    return passed, warnings


def check_position_limits(
    market_id: str,
    new_quantity: int,
    existing_positions: List[Dict[str, Any]],
    max_per_market: int = 200,
    max_total_exposure: int = 1000,
) -> Tuple[bool, str]:
    """
    Check if new position would exceed position limits.

    Args:
        market_id: Market identifier
        new_quantity: Proposed new position quantity
        existing_positions: List of existing positions across all markets
        max_per_market: Maximum contracts per market (default: 200)
        max_total_exposure: Maximum total contracts across all markets (default: 1000)

    Returns:
        Tuple of (allowed: bool, message: str)
    """
    # Calculate current exposure in this market
    current_market_exposure = sum(
        pos.get("quantity", 0)
        for pos in existing_positions
        if pos.get("market_id") == market_id
    )

    # Calculate total exposure across all markets
    total_exposure = sum(pos.get("quantity", 0) for pos in existing_positions)

    # Check market-specific limit
    new_market_exposure = current_market_exposure + new_quantity
    if new_market_exposure > max_per_market:
        return False, (
            f"Market limit exceeded: {new_market_exposure} contracts "
            f"(limit: {max_per_market})"
        )

    # Check total exposure limit
    new_total_exposure = total_exposure + new_quantity
    if new_total_exposure > max_total_exposure:
        return False, (
            f"Total exposure limit exceeded: {new_total_exposure} contracts "
            f"(limit: {max_total_exposure})"
        )

    return True, "Position limits OK"


def check_daily_trade_limit(
    trades_today: int,
    max_daily_trades: int = 10,
) -> Tuple[bool, str]:
    """
    Check if daily trade limit has been reached.

    Args:
        trades_today: Number of trades executed today
        max_daily_trades: Maximum trades per day (default: 10)

    Returns:
        Tuple of (allowed: bool, message: str)
    """
    if trades_today >= max_daily_trades:
        return False, (
            f"Daily trade limit reached: {trades_today}/{max_daily_trades} trades"
        )

    remaining = max_daily_trades - trades_today
    return True, f"Daily limit OK ({remaining} trades remaining)"


def validate_market_health(
    market: Dict[str, Any],
    min_open_interest: int = 100,
) -> Tuple[bool, List[str]]:
    """
    Validate overall market health for trading.

    Args:
        market: Market data dictionary
        min_open_interest: Minimum open interest required (default: 100)

    Returns:
        Tuple of (healthy: bool, issues: List[str])
    """
    issues = []
    healthy = True

    # Check open interest
    open_interest = market.get("open_interest", 0)
    if open_interest < min_open_interest:
        issues.append(
            f"Low open interest: {open_interest} < {min_open_interest}"
        )
        healthy = False

    # Check if market is close to expiry (within 1 day)
    close_time = market.get("close_time")
    if close_time:
        from datetime import datetime, timedelta
        try:
            if isinstance(close_time, str):
                close_dt = datetime.fromisoformat(close_time.replace('+00:00', ''))
            else:
                close_dt = close_time

            time_to_close = close_dt - datetime.now()
            if time_to_close < timedelta(days=1):
                issues.append(
                    f"Market closes soon: {time_to_close.total_seconds() / 3600:.1f} hours"
                )
                healthy = False
        except (ValueError, TypeError):
            pass

    return healthy, issues
