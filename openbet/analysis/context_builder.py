"""Build comprehensive context for LLM analysis."""

from typing import Optional

from openbet.database.repositories import (
    AnalysisRepository,
    MarketRepository,
    PositionRepository,
)
from openbet.kalshi.client import KalshiClient
from openbet.llm.models import MarketContext


class ContextBuilder:
    """Builds market context for LLM analysis."""

    def __init__(self):
        """Initialize context builder with database repositories and API client."""
        self.market_repo = MarketRepository()
        self.position_repo = PositionRepository()
        self.analysis_repo = AnalysisRepository()
        self.kalshi_client = KalshiClient()

    def build_context(
        self, market_id: str, option: Optional[str] = None
    ) -> MarketContext:
        """Build comprehensive context for market analysis.

        Args:
            market_id: Market ticker
            option: Specific option to analyze (optional)

        Returns:
            MarketContext with all available information

        Raises:
            ValueError: If market not found
        """
        # Get market from database
        market = self.market_repo.get(market_id)
        if not market:
            raise ValueError(f"Market {market_id} not found in database")

        # Get current market data from Kalshi
        kalshi_market = self.kalshi_client.get_market(market_id)
        orderbook = self.kalshi_client.get_orderbook(market_id)

        # Get position information
        option_key = option or market_id
        positions = self.position_repo.get_by_market(market_id)

        has_position = len(positions) > 0
        position_data = {}
        if has_position and positions:
            # Use first position for now (could be refined)
            pos = positions[0]
            position_data = {
                "has_position": True,
                "position_side": pos["side"],
                "position_quantity": pos["quantity"],
                "position_avg_price": pos["avg_price"],
                "position_pnl": pos.get("unrealized_pnl"),
            }

        # Get historical analysis
        historical_analyses = self.analysis_repo.get_history_by_market(
            market_id, limit=5
        )

        # Build context
        context = MarketContext(
            market_id=market_id,
            title=market["title"],
            close_time=market.get("close_time"),
            status=market.get("status"),
            yes_price=orderbook.yes_mid_price,
            no_price=orderbook.no_mid_price,
            volume_24h=kalshi_market.volume_24h,
            liquidity_depth=float(kalshi_market.liquidity or 0) if kalshi_market.liquidity else None,
            open_interest=kalshi_market.open_interest,
            historical_analyses=historical_analyses,
            **position_data,
        )

        return context
