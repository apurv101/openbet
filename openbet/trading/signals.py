"""
Signal generation logic for trading strategy.
"""

from datetime import datetime
from typing import Dict, Optional, Any

from openbet.analysis.analyzer import Analyzer
from openbet.kalshi.client import KalshiClient
from openbet.trading.models import TradingSignal, RiskConfig
from openbet.trading.sizing import calculate_position_size, calculate_expected_profit
from openbet.trading.risk import apply_risk_filters
from openbet.database.repositories import TradingSignalRepository


class SignalGenerator:
    """Generates trading signals based on consensus vs market divergence."""

    def __init__(
        self,
        analyzer: Optional[Analyzer] = None,
        kalshi_client: Optional[KalshiClient] = None,
        signal_repo: Optional[TradingSignalRepository] = None,
    ):
        """Initialize signal generator with dependencies."""
        self.analyzer = analyzer or Analyzer()
        self.kalshi_client = kalshi_client or KalshiClient()
        self.signal_repo = signal_repo or TradingSignalRepository()

    def generate_entry_signal(
        self,
        market_id: str,
        option: str = "yes",
        min_divergence_threshold: float = 0.05,
        base_position: int = 10,
        max_position: int = 100,
        scaling_factor: float = 1.5,
        risk_config: Optional[RiskConfig] = None,
        force_analysis: bool = False,
        cache_hours: int = 24,
    ) -> Optional[TradingSignal]:
        """
        Generate entry signal by comparing consensus vs market probabilities.

        Algorithm:
        1. Get or generate fresh AI consensus (use cached if fresh)
        2. Fetch current market orderbook
        3. Calculate divergences for YES and NO
        4. If max(divergence_yes, divergence_no) >= threshold:
           - Select side with larger divergence
           - Calculate position size
           - Generate signal with recommendation
        5. Apply risk filters
        6. Store signal in database

        Args:
            market_id: Market ticker ID
            option: Option to analyze (default: "yes")
            min_divergence_threshold: Minimum divergence to trigger signal (default: 0.05 = 5%)
            base_position: Base position size for minimum divergence (default: 10)
            max_position: Maximum position cap (default: 100)
            scaling_factor: Position sizing aggressiveness (default: 1.5)
            risk_config: Risk management configuration
            force_analysis: Force fresh analysis (skip cache)
            cache_hours: Cache validity period (default: 24)

        Returns:
            TradingSignal if opportunity found, None otherwise
        """
        risk_config = risk_config or RiskConfig()

        # Step 1: Get AI consensus
        analysis_result = self.analyzer.analyze_market(
            market_id=market_id,
            option=option,
            force=force_analysis,
            cache_hours=cache_hours,
        )

        if not analysis_result or "error" in analysis_result:
            return None

        consensus_yes = analysis_result.get("consensus_yes_confidence", 0.0)
        consensus_no = analysis_result.get("consensus_no_confidence", 0.0)
        analysis_id = analysis_result.get("analysis_id")

        # Step 2: Fetch current market prices
        try:
            market = self.kalshi_client.get_market(market_id)
            orderbook = self.kalshi_client.get_orderbook(market_id)
        except Exception as e:
            print(f"Error fetching market data: {e}")
            return None

        market_yes_prob = orderbook.yes_mid_price or 0.0
        market_no_prob = orderbook.no_mid_price or 0.0

        # Step 3: Calculate divergences
        divergence_yes = abs(consensus_yes - market_yes_prob)
        divergence_no = abs(consensus_no - market_no_prob)

        # Step 4: Check if divergence meets threshold
        max_divergence = max(divergence_yes, divergence_no)

        if max_divergence < min_divergence_threshold:
            return None

        # Determine which side to buy (undervalued by market)
        if divergence_yes > divergence_no:
            # YES is undervalued if consensus > market
            if consensus_yes > market_yes_prob:
                selected_side = "yes"
                recommended_action = "buy_yes"
                recommended_price = market_yes_prob
                target_price = consensus_yes
                divergence_magnitude = divergence_yes
            else:
                # Consensus says NO is more likely, but market disagrees
                return None
        else:
            # NO is undervalued if consensus > market
            if consensus_no > market_no_prob:
                selected_side = "no"
                recommended_action = "buy_no"
                recommended_price = market_no_prob
                target_price = consensus_no
                divergence_magnitude = divergence_no
            else:
                return None

        # Step 5: Calculate position size
        recommended_quantity = calculate_position_size(
            divergence=divergence_magnitude,
            base_amount=base_position,
            max_position=max_position,
            scaling_factor=scaling_factor,
        )

        # Calculate expected profit
        expected_profit = calculate_expected_profit(
            quantity=recommended_quantity,
            entry_price=recommended_price,
            target_price=target_price,
        )

        # Extract market metadata
        volume_24h = analysis_result.get("volume_24h")
        liquidity_depth = analysis_result.get("liquidity_depth")
        open_interest = market.open_interest if hasattr(market, 'open_interest') else None

        # Create signal object
        signal = TradingSignal(
            signal_timestamp=datetime.now(),
            market_id=market_id,
            option=option,
            signal_type="entry",
            consensus_yes_prob=consensus_yes,
            consensus_no_prob=consensus_no,
            market_yes_prob=market_yes_prob,
            market_no_prob=market_no_prob,
            divergence_yes=divergence_yes,
            divergence_no=divergence_no,
            selected_side=selected_side,
            divergence_magnitude=divergence_magnitude,
            recommended_action=recommended_action,
            recommended_quantity=recommended_quantity,
            recommended_price=recommended_price,
            expected_profit=expected_profit,
            volume_24h=volume_24h,
            liquidity_depth=liquidity_depth,
            open_interest=open_interest,
            analysis_id=analysis_id,
        )

        # Step 6: Apply risk filters
        market_dict = {
            "status": market.status if hasattr(market, 'status') else "unknown",
            "open_interest": open_interest,
            "close_time": market.close_time if hasattr(market, 'close_time') else None,
        }

        passed, warnings = apply_risk_filters(signal, market_dict, risk_config)
        signal.passed_filters = passed
        signal.risk_warnings = warnings

        # Store signal in database
        signal_id = self.signal_repo.create(
            market_id=signal.market_id,
            option=signal.option,
            signal_type=signal.signal_type,
            consensus_yes_prob=signal.consensus_yes_prob,
            consensus_no_prob=signal.consensus_no_prob,
            market_yes_prob=signal.market_yes_prob,
            market_no_prob=signal.market_no_prob,
            divergence_yes=signal.divergence_yes,
            divergence_no=signal.divergence_no,
            selected_side=signal.selected_side,
            divergence_magnitude=signal.divergence_magnitude,
            recommended_action=signal.recommended_action,
            recommended_quantity=signal.recommended_quantity,
            recommended_price=signal.recommended_price,
            expected_profit=signal.expected_profit,
            volume_24h=signal.volume_24h,
            liquidity_depth=signal.liquidity_depth,
            open_interest=signal.open_interest,
            analysis_id=signal.analysis_id,
            metadata={"risk_warnings": warnings, "passed_filters": passed},
        )

        signal.signal_id = signal_id

        return signal

    def generate_exit_signal(
        self,
        position: Dict[str, Any],
        convergence_threshold: float = 0.01,
        force_analysis: bool = False,
    ) -> Optional[TradingSignal]:
        """
        Generate exit signal for open position when price converges to consensus.

        Algorithm:
        1. Get current consensus for position's market
        2. Fetch current market price
        3. Calculate current divergence
        4. If abs(current_price - consensus_prob) <= threshold:
           - Generate exit signal
           - Calculate expected profit/loss
           - Store signal

        Args:
            position: Position dictionary from database
            convergence_threshold: Maximum divergence for exit (default: 0.01 = 1%)
            force_analysis: Force fresh analysis

        Returns:
            TradingSignal for exit if converged, None otherwise
        """
        market_id = position.get("market_id")
        option = position.get("option", "yes")
        side = position.get("side", "yes")
        entry_price = position.get("avg_price", 0.0)
        quantity = position.get("quantity", 0)

        if not market_id or quantity == 0:
            return None

        # Get current consensus
        analysis_result = self.analyzer.analyze_market(
            market_id=market_id,
            option=option,
            force=force_analysis,
        )

        if not analysis_result or "error" in analysis_result:
            return None

        consensus_yes = analysis_result.get("consensus_yes_confidence", 0.0)
        consensus_no = analysis_result.get("consensus_no_confidence", 0.0)
        analysis_id = analysis_result.get("analysis_id")

        # Get current market price
        try:
            orderbook = self.kalshi_client.get_orderbook(market_id)
            market = self.kalshi_client.get_market(market_id)
        except Exception as e:
            print(f"Error fetching market data: {e}")
            return None

        market_yes_prob = orderbook.yes_mid_price or 0.0
        market_no_prob = orderbook.no_mid_price or 0.0

        # Determine current price and consensus for the held side
        if side.lower() == "yes":
            current_price = market_yes_prob
            consensus_price = consensus_yes
            recommended_action = "sell_yes"
        else:
            current_price = market_no_prob
            consensus_price = consensus_no
            recommended_action = "sell_no"

        # Calculate current divergence
        current_divergence = abs(current_price - consensus_price)

        # Check convergence
        if current_divergence > convergence_threshold:
            return None

        # Calculate realized P&L
        expected_profit = calculate_expected_profit(
            quantity=quantity,
            entry_price=entry_price,
            target_price=current_price,
        )

        # Create exit signal
        signal = TradingSignal(
            signal_timestamp=datetime.now(),
            market_id=market_id,
            option=option,
            signal_type="exit",
            consensus_yes_prob=consensus_yes,
            consensus_no_prob=consensus_no,
            market_yes_prob=market_yes_prob,
            market_no_prob=market_no_prob,
            divergence_yes=abs(consensus_yes - market_yes_prob),
            divergence_no=abs(consensus_no - market_no_prob),
            selected_side=side,
            divergence_magnitude=current_divergence,
            recommended_action=recommended_action,
            recommended_quantity=quantity,
            recommended_price=current_price,
            expected_profit=expected_profit,
            analysis_id=analysis_id,
            passed_filters=True,
            risk_warnings=[],
        )

        # Store signal in database
        signal_id = self.signal_repo.create(
            market_id=signal.market_id,
            option=signal.option,
            signal_type=signal.signal_type,
            consensus_yes_prob=signal.consensus_yes_prob,
            consensus_no_prob=signal.consensus_no_prob,
            market_yes_prob=signal.market_yes_prob,
            market_no_prob=signal.market_no_prob,
            divergence_yes=signal.divergence_yes,
            divergence_no=signal.divergence_no,
            selected_side=signal.selected_side,
            divergence_magnitude=signal.divergence_magnitude,
            recommended_action=signal.recommended_action,
            recommended_quantity=signal.recommended_quantity,
            recommended_price=signal.recommended_price,
            expected_profit=signal.expected_profit,
            analysis_id=signal.analysis_id,
            metadata={"entry_price": entry_price, "position_id": position.get("id")},
        )

        signal.signal_id = signal_id

        return signal
