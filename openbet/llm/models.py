"""Models for LLM provider requests and responses."""

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class LLMAnalysisResponse(BaseModel):
    """Structured response from an LLM provider."""

    yes_confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence in YES (0-1)")
    no_confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence in NO (0-1)")
    reasoning: str = Field(..., description="Explanation for the confidence scores")
    provider: Optional[str] = Field(None, description="Provider name")


class MarketContext(BaseModel):
    """Context information for market analysis."""

    market_id: str
    title: str
    close_time: Optional[str] = None
    status: Optional[str] = None

    # Current prices
    yes_price: Optional[float] = None
    no_price: Optional[float] = None

    # Position information
    has_position: bool = False
    position_side: Optional[str] = None
    position_quantity: Optional[int] = None
    position_avg_price: Optional[float] = None
    position_pnl: Optional[float] = None

    # Market metrics
    volume_24h: Optional[float] = None
    liquidity_depth: Optional[float] = None
    open_interest: Optional[int] = None

    # Historical analysis
    historical_analyses: list[Dict[str, Any]] = Field(default_factory=list)

    # Additional metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def to_prompt_text(self) -> str:
        """Convert context to text suitable for LLM prompt."""
        parts = [
            f"Market: {self.title}",
            f"Market ID: {self.market_id}",
        ]

        if self.status:
            parts.append(f"Status: {self.status}")

        if self.close_time:
            parts.append(f"Closes: {self.close_time}")

        if self.yes_price is not None and self.no_price is not None:
            parts.append(f"\nCurrent Prices:")
            parts.append(f"  YES: ${self.yes_price:.2f}")
            parts.append(f"  NO: ${self.no_price:.2f}")

        if self.has_position:
            parts.append(f"\nYour Current Position:")
            parts.append(f"  Side: {self.position_side}")
            parts.append(f"  Quantity: {self.position_quantity}")
            parts.append(f"  Avg Price: ${self.position_avg_price:.2f}")
            if self.position_pnl:
                parts.append(f"  Unrealized P&L: ${self.position_pnl:.2f}")

        if self.volume_24h or self.liquidity_depth or self.open_interest:
            parts.append(f"\nMarket Metrics:")
            if self.volume_24h:
                parts.append(f"  24h Volume: {self.volume_24h}")
            if self.liquidity_depth:
                parts.append(f"  Liquidity Depth: {self.liquidity_depth}")
            if self.open_interest:
                parts.append(f"  Open Interest: {self.open_interest}")

        if self.historical_analyses:
            parts.append(f"\nHistorical Analysis:")
            for i, analysis in enumerate(self.historical_analyses[:3], 1):
                parts.append(f"  Analysis #{i}:")
                parts.append(
                    f"    Timestamp: {analysis.get('analysis_timestamp', 'N/A')}"
                )
                parts.append(
                    f"    Consensus YES: {analysis.get('consensus_yes_confidence', 0):.1%}"
                )
                parts.append(
                    f"    Consensus NO: {analysis.get('consensus_no_confidence', 0):.1%}"
                )

        return "\n".join(parts)
