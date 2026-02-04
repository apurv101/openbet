"""
Pydantic models for trading operations.
"""

from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class TradingSignal(BaseModel):
    """Trading signal with recommendation."""

    signal_id: Optional[int] = None
    signal_timestamp: datetime
    market_id: str
    option: str
    signal_type: Literal["entry", "exit"]

    # Probabilities
    consensus_yes_prob: float
    consensus_no_prob: float
    market_yes_prob: float
    market_no_prob: float

    # Divergence
    divergence_yes: float
    divergence_no: float
    selected_side: Optional[Literal["yes", "no"]] = None
    divergence_magnitude: float

    # Recommendation
    recommended_action: str  # 'buy_yes', 'buy_no', 'sell_yes', 'sell_no'
    recommended_quantity: int
    recommended_price: float
    expected_profit: float

    # Context
    volume_24h: Optional[float] = None
    liquidity_depth: Optional[float] = None
    open_interest: Optional[int] = None
    analysis_id: Optional[int] = None

    # Risk assessment
    risk_warnings: List[str] = Field(default_factory=list)
    passed_filters: bool = True

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class TradeDecision(BaseModel):
    """User decision on trading signal."""

    decision_id: Optional[int] = None
    decision_timestamp: datetime = Field(default_factory=datetime.now)
    signal_id: int
    decision: Literal["approved", "rejected", "ignored"]
    user_notes: Optional[str] = None

    # Execution details
    executed: bool = False
    execution_timestamp: Optional[datetime] = None
    order_id: Optional[str] = None
    actual_quantity: Optional[int] = None
    actual_price: Optional[float] = None
    execution_cost: Optional[float] = None

    # Position tracking
    position_id: Optional[int] = None
    realized_pnl: Optional[float] = None

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class RiskConfig(BaseModel):
    """Risk management configuration."""

    min_liquidity: float = 100.0
    min_volume_24h: float = 50.0
    max_position_size: int = 100
    max_spread: float = 0.10  # 10% max bid-ask spread
    allowed_statuses: List[str] = Field(default_factory=lambda: ["open"])
