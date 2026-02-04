"""
Main trading strategy orchestrator.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any

from openbet.analysis.analyzer import Analyzer
from openbet.kalshi.client import KalshiClient
from openbet.database.repositories import (
    MarketRepository,
    PositionRepository,
    TradeDecisionRepository,
    TradingSignalRepository,
)
from openbet.trading.models import TradingSignal, TradeDecision, RiskConfig
from openbet.trading.signals import SignalGenerator


class TradingStrategy:
    """Main orchestrator for trading strategy execution."""

    def __init__(
        self,
        entry_threshold: float = 0.05,
        exit_threshold: float = 0.01,
        base_position_size: int = 10,
        max_position_size: int = 100,
        scaling_factor: float = 1.5,
        risk_config: Optional[RiskConfig] = None,
    ):
        """
        Initialize trading strategy.

        Args:
            entry_threshold: Minimum divergence for entry signals (default: 0.05 = 5%)
            exit_threshold: Convergence threshold for exits (default: 0.01 = 1%)
            base_position_size: Base position for minimum divergence (default: 10)
            max_position_size: Maximum position cap (default: 100)
            scaling_factor: Position sizing aggressiveness (default: 1.5)
            risk_config: Risk management configuration
        """
        self.entry_threshold = entry_threshold
        self.exit_threshold = exit_threshold
        self.base_position_size = base_position_size
        self.max_position_size = max_position_size
        self.scaling_factor = scaling_factor
        self.risk_config = risk_config or RiskConfig()

        # Initialize dependencies
        self.analyzer = Analyzer()
        self.kalshi_client = KalshiClient()
        self.market_repo = MarketRepository()
        self.position_repo = PositionRepository()
        self.signal_repo = TradingSignalRepository()
        self.decision_repo = TradeDecisionRepository()
        self.signal_generator = SignalGenerator(
            analyzer=self.analyzer,
            kalshi_client=self.kalshi_client,
            signal_repo=self.signal_repo,
        )

    def scan_for_opportunities(
        self,
        market_ids: Optional[List[str]] = None,
        force_analysis: bool = False,
    ) -> List[TradingSignal]:
        """
        Scan markets for entry opportunities.

        Process:
        1. Get markets to scan (all tracked or specific list)
        2. For each market:
           - Generate entry signal
           - Apply risk filters
           - If passed, add to opportunities list
        3. Sort by divergence magnitude (best first)
        4. Return ranked opportunities

        Args:
            market_ids: Optional list of specific markets to scan (None = scan all)
            force_analysis: Force fresh analysis for all markets

        Returns:
            List of TradingSignal objects sorted by divergence (best first)
        """
        opportunities = []

        # Get markets to scan
        if market_ids:
            markets = [self.market_repo.get(mid) for mid in market_ids]
            markets = [m for m in markets if m is not None]
        else:
            markets = self.market_repo.get_all()

        # Generate signals for each market
        for market in markets:
            market_id = market.get("id")
            if not market_id:
                continue

            try:
                signal = self.signal_generator.generate_entry_signal(
                    market_id=market_id,
                    option="yes",  # Can be parameterized
                    min_divergence_threshold=self.entry_threshold,
                    base_position=self.base_position_size,
                    max_position=self.max_position_size,
                    scaling_factor=self.scaling_factor,
                    risk_config=self.risk_config,
                    force_analysis=force_analysis,
                )

                if signal and signal.passed_filters:
                    opportunities.append(signal)

            except Exception as e:
                print(f"Error scanning market {market_id}: {e}")
                continue

        # Sort by divergence magnitude (highest first)
        opportunities.sort(key=lambda s: s.divergence_magnitude, reverse=True)

        return opportunities

    def monitor_exits(self, force_analysis: bool = False) -> List[TradingSignal]:
        """
        Monitor open positions for exit opportunities.

        Process:
        1. Get all open positions from database
        2. For each position:
           - Generate exit signal
           - Check convergence
           - If converged, add to exit list
        3. Return exit recommendations

        Args:
            force_analysis: Force fresh analysis for exit checks

        Returns:
            List of TradingSignal objects for positions ready to exit
        """
        exit_signals = []

        # Get all markets with positions
        markets = self.market_repo.get_all()

        for market in markets:
            market_id = market.get("id")
            if not market_id:
                continue

            # Get positions for this market
            positions = self.position_repo.get_by_market(market_id)

            for position in positions:
                try:
                    signal = self.signal_generator.generate_exit_signal(
                        position=position,
                        convergence_threshold=self.exit_threshold,
                        force_analysis=force_analysis,
                    )

                    if signal:
                        exit_signals.append(signal)

                except Exception as e:
                    print(f"Error checking exit for position {position.get('id')}: {e}")
                    continue

        return exit_signals

    def execute_signal(
        self,
        signal: TradingSignal,
        user_approved: bool,
        custom_quantity: Optional[int] = None,
        custom_price: Optional[float] = None,
        user_notes: Optional[str] = None,
    ) -> TradeDecision:
        """
        Execute approved trading signal.

        Process:
        1. Create trade decision record
        2. If user_approved:
           - Place order via KalshiClient
           - Update position in database
           - Mark decision as executed
        3. If rejected/ignored:
           - Record decision without execution
        4. Return TradeDecision with outcome

        Args:
            signal: Trading signal to execute
            user_approved: Whether user approved the trade
            custom_quantity: Optional quantity override
            custom_price: Optional price override
            user_notes: Optional user notes

        Returns:
            TradeDecision with execution results
        """
        decision = "approved" if user_approved else "rejected"
        quantity = custom_quantity or signal.recommended_quantity
        price = custom_price or signal.recommended_price

        trade_decision = TradeDecision(
            signal_id=signal.signal_id,
            decision=decision,
            user_notes=user_notes,
        )

        if not user_approved:
            # User rejected - just record decision
            decision_id = self.decision_repo.create(
                signal_id=signal.signal_id,
                decision=decision,
                user_notes=user_notes,
                executed=False,
            )
            trade_decision.decision_id = decision_id
            return trade_decision

        # User approved - execute the trade
        try:
            if signal.signal_type == "entry":
                # Place entry order
                action = "buy"
                side = signal.selected_side or "yes"

                order = self.kalshi_client.place_order(
                    ticker=signal.market_id,
                    side=side,
                    action=action,
                    count=quantity,
                    order_type="limit",
                    yes_price=price if side == "yes" else None,
                    no_price=price if side == "no" else None,
                )

                # Update position in database
                self.position_repo.create_or_update(
                    market_id=signal.market_id,
                    option=signal.option,
                    side=side,
                    quantity=quantity,
                    avg_price=price,
                    metadata={"order_id": order.order_id if hasattr(order, 'order_id') else None},
                )

                # Record successful execution
                execution_cost = quantity * price
                trade_decision.executed = True
                trade_decision.execution_timestamp = datetime.now()
                trade_decision.order_id = order.order_id if hasattr(order, 'order_id') else None
                trade_decision.actual_quantity = quantity
                trade_decision.actual_price = price
                trade_decision.execution_cost = execution_cost

            elif signal.signal_type == "exit":
                # Place exit order
                action = "sell"
                side = signal.selected_side or "yes"

                order = self.kalshi_client.place_order(
                    ticker=signal.market_id,
                    side=side,
                    action=action,
                    count=quantity,
                    order_type="limit",
                    yes_price=price if side == "yes" else None,
                    no_price=price if side == "no" else None,
                )

                # Update position (reduce or close)
                # For now, we'll close the position entirely
                # In production, you'd handle partial exits
                self.position_repo.create_or_update(
                    market_id=signal.market_id,
                    option=signal.option,
                    side=side,
                    quantity=0,  # Close position
                    avg_price=0.0,
                    metadata={"exit_order_id": order.order_id if hasattr(order, 'order_id') else None},
                )

                # Record successful execution with P&L
                trade_decision.executed = True
                trade_decision.execution_timestamp = datetime.now()
                trade_decision.order_id = order.order_id if hasattr(order, 'order_id') else None
                trade_decision.actual_quantity = quantity
                trade_decision.actual_price = price
                trade_decision.realized_pnl = signal.expected_profit

            # Save decision to database
            decision_id = self.decision_repo.create(
                signal_id=signal.signal_id,
                decision=decision,
                user_notes=user_notes,
                executed=trade_decision.executed,
                execution_timestamp=trade_decision.execution_timestamp.isoformat() if trade_decision.execution_timestamp else None,
                order_id=trade_decision.order_id,
                actual_quantity=trade_decision.actual_quantity,
                actual_price=trade_decision.actual_price,
                execution_cost=trade_decision.execution_cost,
                realized_pnl=trade_decision.realized_pnl,
            )

            trade_decision.decision_id = decision_id

        except Exception as e:
            print(f"Error executing trade: {e}")
            # Record failed execution
            trade_decision.executed = False
            trade_decision.user_notes = f"Execution failed: {str(e)}"

            decision_id = self.decision_repo.create(
                signal_id=signal.signal_id,
                decision="approved",
                user_notes=trade_decision.user_notes,
                executed=False,
            )
            trade_decision.decision_id = decision_id

        return trade_decision

    def get_signal_history(
        self,
        limit: int = 20,
        signal_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get recent trading signal history.

        Args:
            limit: Maximum number of signals to return
            signal_type: Optional filter by signal type ("entry" or "exit")

        Returns:
            List of signal dictionaries
        """
        if signal_type:
            return self.signal_repo.get_by_type(signal_type, limit)
        else:
            return self.signal_repo.get_recent(limit)

    def get_decision_history(
        self,
        limit: int = 20,
        decision_filter: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get trade decision history.

        Args:
            limit: Maximum number of decisions to return
            decision_filter: Optional filter by decision ("approved", "rejected", "ignored")

        Returns:
            List of decision dictionaries
        """
        return self.decision_repo.get_execution_history(limit, decision_filter)

    def get_performance_stats(self) -> Dict[str, Any]:
        """
        Calculate performance statistics from trade history.

        Returns:
            Dictionary with performance metrics
        """
        # Get all decisions
        all_decisions = self.decision_repo.get_execution_history(limit=1000)

        total_signals = len(self.signal_repo.get_recent(limit=1000))
        total_decisions = len(all_decisions)
        approved = len([d for d in all_decisions if d.get("decision") == "approved"])
        executed = len([d for d in all_decisions if d.get("executed")])

        # Calculate P&L for executed exits
        exits = [
            d for d in all_decisions
            if d.get("executed") and d.get("realized_pnl") is not None
        ]
        total_pnl = sum(d.get("realized_pnl", 0.0) for d in exits)
        wins = len([d for d in exits if d.get("realized_pnl", 0.0) > 0])
        losses = len([d for d in exits if d.get("realized_pnl", 0.0) < 0])

        return {
            "total_signals": total_signals,
            "total_decisions": total_decisions,
            "approved": approved,
            "rejected": total_decisions - approved,
            "approval_rate": approved / total_decisions if total_decisions > 0 else 0,
            "executed": executed,
            "execution_rate": executed / approved if approved > 0 else 0,
            "total_trades": len(exits),
            "wins": wins,
            "losses": losses,
            "win_rate": wins / len(exits) if exits else 0,
            "total_pnl": total_pnl,
            "avg_pnl_per_trade": total_pnl / len(exits) if exits else 0,
        }
