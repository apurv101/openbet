"""Data access layer for Openbet database operations."""

import json
import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional

from openbet.database.db import get_db


class MarketRepository:
    """Repository for market operations."""

    def __init__(self, db=None):
        """Initialize repository with database connection."""
        self.db = db or get_db()

    def create(
        self,
        market_id: str,
        title: str,
        close_time: Optional[str] = None,
        status: Optional[str] = None,
        category: Optional[str] = None,
        min_tick_size: Optional[float] = None,
        max_tick_size: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Create a new market record."""
        metadata_json = json.dumps(metadata) if metadata else None

        cursor = self.db.conn.cursor()
        cursor.execute(
            """
            INSERT INTO markets (
                id, title, close_time, status, category,
                min_tick_size, max_tick_size, metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                market_id,
                title,
                close_time,
                status,
                category,
                min_tick_size,
                max_tick_size,
                metadata_json,
            ),
        )
        self.db.conn.commit()

    def get(self, market_id: str) -> Optional[Dict[str, Any]]:
        """Get market by ID."""
        cursor = self.db.conn.cursor()
        cursor.execute("SELECT * FROM markets WHERE id = ?", (market_id,))
        row = cursor.fetchone()

        if row is None:
            return None

        return dict(row)

    def get_all(self) -> List[Dict[str, Any]]:
        """Get all markets."""
        cursor = self.db.conn.cursor()
        cursor.execute("SELECT * FROM markets ORDER BY created_at DESC")
        return [dict(row) for row in cursor.fetchall()]

    def exists(self, market_id: str) -> bool:
        """Check if market exists."""
        return self.get(market_id) is not None

    def update_status(self, market_id: str, status: str) -> None:
        """Update market status."""
        cursor = self.db.conn.cursor()
        cursor.execute(
            """
            UPDATE markets
            SET status = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (status, market_id),
        )
        self.db.conn.commit()


class PositionRepository:
    """Repository for position operations."""

    def __init__(self, db=None):
        """Initialize repository with database connection."""
        self.db = db or get_db()

    def create_or_update(
        self,
        market_id: str,
        option: str,
        side: str,
        quantity: int,
        avg_price: float,
        current_value: Optional[float] = None,
        unrealized_pnl: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Create or update a position."""
        metadata_json = json.dumps(metadata) if metadata else None

        cursor = self.db.conn.cursor()
        cursor.execute(
            """
            INSERT INTO positions (
                market_id, option, side, quantity, avg_price,
                current_value, unrealized_pnl, metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(market_id, option, side) DO UPDATE SET
                quantity = excluded.quantity,
                avg_price = excluded.avg_price,
                current_value = excluded.current_value,
                unrealized_pnl = excluded.unrealized_pnl,
                metadata = excluded.metadata,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                market_id,
                option,
                side,
                quantity,
                avg_price,
                current_value,
                unrealized_pnl,
                metadata_json,
            ),
        )
        self.db.conn.commit()

    def get_by_market(self, market_id: str) -> List[Dict[str, Any]]:
        """Get all positions for a market."""
        cursor = self.db.conn.cursor()
        cursor.execute(
            "SELECT * FROM positions WHERE market_id = ?", (market_id,)
        )
        return [dict(row) for row in cursor.fetchall()]

    def get_by_market_and_option(
        self, market_id: str, option: str, side: str
    ) -> Optional[Dict[str, Any]]:
        """Get specific position."""
        cursor = self.db.conn.cursor()
        cursor.execute(
            """
            SELECT * FROM positions
            WHERE market_id = ? AND option = ? AND side = ?
            """,
            (market_id, option, side),
        )
        row = cursor.fetchone()
        return dict(row) if row else None


class AnalysisRepository:
    """Repository for analysis results operations."""

    def __init__(self, db=None):
        """Initialize repository with database connection."""
        self.db = db or get_db()

    def create(
        self,
        market_id: str,
        option: str,
        claude_response: Optional[Dict[str, Any]] = None,
        openai_response: Optional[Dict[str, Any]] = None,
        grok_response: Optional[Dict[str, Any]] = None,
        gemini_response: Optional[Dict[str, Any]] = None,
        yes_price: Optional[float] = None,
        no_price: Optional[float] = None,
        volume_24h: Optional[float] = None,
        liquidity_depth: Optional[float] = None,
        consensus_yes_confidence: Optional[float] = None,
        consensus_no_confidence: Optional[float] = None,
        consensus_method: str = "iterative_reasoning",
        previous_analysis_id: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> int:
        """Create a new analysis result and return its ID."""
        claude_json = json.dumps(claude_response) if claude_response else None
        openai_json = json.dumps(openai_response) if openai_response else None
        grok_json = json.dumps(grok_response) if grok_response else None
        gemini_json = json.dumps(gemini_response) if gemini_response else None
        metadata_json = json.dumps(metadata) if metadata else None

        cursor = self.db.conn.cursor()
        cursor.execute(
            """
            INSERT INTO analysis_results (
                market_id, option,
                claude_response, openai_response, grok_response, gemini_response,
                yes_price, no_price, volume_24h, liquidity_depth,
                consensus_yes_confidence, consensus_no_confidence,
                consensus_method, previous_analysis_id, metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                market_id,
                option,
                claude_json,
                openai_json,
                grok_json,
                gemini_json,
                yes_price,
                no_price,
                volume_24h,
                liquidity_depth,
                consensus_yes_confidence,
                consensus_no_confidence,
                consensus_method,
                previous_analysis_id,
                metadata_json,
            ),
        )
        self.db.conn.commit()
        return cursor.lastrowid

    def get_latest_by_market(
        self, market_id: str, option: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Get latest analysis for a market/option."""
        cursor = self.db.conn.cursor()

        if option:
            cursor.execute(
                """
                SELECT * FROM analysis_results
                WHERE market_id = ? AND option = ?
                ORDER BY analysis_timestamp DESC
                LIMIT 1
                """,
                (market_id, option),
            )
        else:
            cursor.execute(
                """
                SELECT * FROM analysis_results
                WHERE market_id = ?
                ORDER BY analysis_timestamp DESC
                LIMIT 1
                """,
                (market_id,),
            )

        row = cursor.fetchone()
        return dict(row) if row else None

    def get_history_by_market(
        self, market_id: str, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get analysis history for a market."""
        cursor = self.db.conn.cursor()
        cursor.execute(
            """
            SELECT * FROM analysis_results
            WHERE market_id = ?
            ORDER BY analysis_timestamp DESC
            LIMIT ?
            """,
            (market_id, limit),
        )
        return [dict(row) for row in cursor.fetchall()]

    def get_all_latest_analyses(self) -> List[Dict[str, Any]]:
        """Get latest analysis for each market."""
        cursor = self.db.conn.cursor()
        cursor.execute(
            """
            SELECT a1.*
            FROM analysis_results a1
            INNER JOIN (
                SELECT market_id, MAX(analysis_timestamp) as max_timestamp
                FROM analysis_results
                GROUP BY market_id
            ) a2
            ON a1.market_id = a2.market_id
            AND a1.analysis_timestamp = a2.max_timestamp
            ORDER BY a1.analysis_timestamp DESC
            """
        )
        return [dict(row) for row in cursor.fetchall()]


class TradingSignalRepository:
    """Repository for trading signal operations."""

    def __init__(self, db=None):
        """Initialize repository with database connection."""
        self.db = db or get_db()

    def create(
        self,
        market_id: str,
        option: str,
        signal_type: str,
        consensus_yes_prob: float,
        consensus_no_prob: float,
        market_yes_prob: float,
        market_no_prob: float,
        divergence_yes: float,
        divergence_no: float,
        divergence_magnitude: float,
        recommended_action: str,
        recommended_quantity: int,
        recommended_price: float,
        expected_profit: float,
        selected_side: Optional[str] = None,
        volume_24h: Optional[float] = None,
        liquidity_depth: Optional[float] = None,
        open_interest: Optional[int] = None,
        analysis_id: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> int:
        """Create a new trading signal and return its ID."""
        metadata_json = json.dumps(metadata) if metadata else None

        cursor = self.db.conn.cursor()
        cursor.execute(
            """
            INSERT INTO trading_signals (
                market_id, option, signal_type,
                consensus_yes_prob, consensus_no_prob,
                market_yes_prob, market_no_prob,
                divergence_yes, divergence_no, selected_side,
                divergence_magnitude,
                recommended_action, recommended_quantity,
                recommended_price, expected_profit,
                volume_24h, liquidity_depth, open_interest,
                analysis_id, metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                market_id,
                option,
                signal_type,
                consensus_yes_prob,
                consensus_no_prob,
                market_yes_prob,
                market_no_prob,
                divergence_yes,
                divergence_no,
                selected_side,
                divergence_magnitude,
                recommended_action,
                recommended_quantity,
                recommended_price,
                expected_profit,
                volume_24h,
                liquidity_depth,
                open_interest,
                analysis_id,
                metadata_json,
            ),
        )
        self.db.conn.commit()
        return cursor.lastrowid

    def get_by_market(
        self, market_id: str, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get trading signals for a market."""
        cursor = self.db.conn.cursor()
        cursor.execute(
            """
            SELECT * FROM trading_signals
            WHERE market_id = ?
            ORDER BY signal_timestamp DESC
            LIMIT ?
            """,
            (market_id, limit),
        )
        return [dict(row) for row in cursor.fetchall()]

    def get_recent(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent trading signals."""
        cursor = self.db.conn.cursor()
        cursor.execute(
            """
            SELECT * FROM trading_signals
            ORDER BY signal_timestamp DESC
            LIMIT ?
            """,
            (limit,),
        )
        return [dict(row) for row in cursor.fetchall()]

    def get_by_type(
        self, signal_type: str, limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Get signals by type (entry or exit)."""
        cursor = self.db.conn.cursor()
        cursor.execute(
            """
            SELECT * FROM trading_signals
            WHERE signal_type = ?
            ORDER BY signal_timestamp DESC
            LIMIT ?
            """,
            (signal_type, limit),
        )
        return [dict(row) for row in cursor.fetchall()]


class TradeDecisionRepository:
    """Repository for trade decision operations."""

    def __init__(self, db=None):
        """Initialize repository with database connection."""
        self.db = db or get_db()

    def create(
        self,
        signal_id: int,
        decision: str,
        user_notes: Optional[str] = None,
        executed: bool = False,
        execution_timestamp: Optional[str] = None,
        order_id: Optional[str] = None,
        actual_quantity: Optional[int] = None,
        actual_price: Optional[float] = None,
        execution_cost: Optional[float] = None,
        position_id: Optional[int] = None,
        realized_pnl: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> int:
        """Create a new trade decision and return its ID."""
        metadata_json = json.dumps(metadata) if metadata else None

        cursor = self.db.conn.cursor()
        cursor.execute(
            """
            INSERT INTO trade_decisions (
                signal_id, decision, user_notes,
                executed, execution_timestamp, order_id,
                actual_quantity, actual_price, execution_cost,
                position_id, realized_pnl, metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                signal_id,
                decision,
                user_notes,
                executed,
                execution_timestamp,
                order_id,
                actual_quantity,
                actual_price,
                execution_cost,
                position_id,
                realized_pnl,
                metadata_json,
            ),
        )
        self.db.conn.commit()
        return cursor.lastrowid

    def get_by_signal(self, signal_id: int) -> Optional[Dict[str, Any]]:
        """Get decision for a specific signal."""
        cursor = self.db.conn.cursor()
        cursor.execute(
            """
            SELECT * FROM trade_decisions
            WHERE signal_id = ?
            ORDER BY decision_timestamp DESC
            LIMIT 1
            """,
            (signal_id,),
        )
        row = cursor.fetchone()
        return dict(row) if row else None

    def get_execution_history(
        self, limit: int = 20, decision_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get trade execution history."""
        cursor = self.db.conn.cursor()

        if decision_filter:
            cursor.execute(
                """
                SELECT * FROM trade_decisions
                WHERE decision = ?
                ORDER BY decision_timestamp DESC
                LIMIT ?
                """,
                (decision_filter, limit),
            )
        else:
            cursor.execute(
                """
                SELECT * FROM trade_decisions
                ORDER BY decision_timestamp DESC
                LIMIT ?
                """,
                (limit,),
            )

        return [dict(row) for row in cursor.fetchall()]

    def get_with_signals(
        self, limit: int = 20, signal_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get decisions with their corresponding signals."""
        cursor = self.db.conn.cursor()

        if signal_type:
            cursor.execute(
                """
                SELECT d.*, s.*
                FROM trade_decisions d
                JOIN trading_signals s ON d.signal_id = s.id
                WHERE s.signal_type = ?
                ORDER BY d.decision_timestamp DESC
                LIMIT ?
                """,
                (signal_type, limit),
            )
        else:
            cursor.execute(
                """
                SELECT d.*, s.*
                FROM trade_decisions d
                JOIN trading_signals s ON d.signal_id = s.id
                ORDER BY d.decision_timestamp DESC
                LIMIT ?
                """,
                (limit,),
            )

        return [dict(row) for row in cursor.fetchall()]


class EventRepository:
    """Repository for event operations."""

    def __init__(self, db=None):
        """Initialize repository with database connection."""
        self.db = db or get_db()

    def create_or_update(
        self,
        event_ticker: str,
        title: str,
        category: Optional[str] = None,
        series_ticker: Optional[str] = None,
        sub_title: Optional[str] = None,
        mutually_exclusive: Optional[bool] = None,
        status: Optional[str] = None,
        strike_date: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Insert or update event using UPSERT pattern."""
        metadata_json = json.dumps(metadata) if metadata else None

        cursor = self.db.conn.cursor()
        cursor.execute(
            """
            INSERT INTO events (
                event_ticker, title, category, series_ticker, sub_title,
                mutually_exclusive, status, strike_date, metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(event_ticker) DO UPDATE SET
                title = excluded.title,
                category = excluded.category,
                series_ticker = excluded.series_ticker,
                sub_title = excluded.sub_title,
                mutually_exclusive = excluded.mutually_exclusive,
                status = excluded.status,
                strike_date = excluded.strike_date,
                metadata = excluded.metadata,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                event_ticker,
                title,
                category,
                series_ticker,
                sub_title,
                mutually_exclusive,
                status,
                strike_date,
                metadata_json,
            ),
        )
        self.db.conn.commit()

    def get(self, event_ticker: str) -> Optional[Dict[str, Any]]:
        """Get event by ticker."""
        cursor = self.db.conn.cursor()
        cursor.execute("SELECT * FROM events WHERE event_ticker = ?", (event_ticker,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def get_all(
        self, category: Optional[str] = None, status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get all events with optional filters."""
        cursor = self.db.conn.cursor()

        if category and status:
            cursor.execute(
                """
                SELECT * FROM events
                WHERE category = ? AND status = ?
                ORDER BY created_at DESC
                """,
                (category, status),
            )
        elif category:
            cursor.execute(
                """
                SELECT * FROM events
                WHERE category = ?
                ORDER BY created_at DESC
                """,
                (category,),
            )
        elif status:
            cursor.execute(
                """
                SELECT * FROM events
                WHERE status = ?
                ORDER BY created_at DESC
                """,
                (status,),
            )
        else:
            cursor.execute("SELECT * FROM events ORDER BY created_at DESC")

        return [dict(row) for row in cursor.fetchall()]

    def exists(self, event_ticker: str) -> bool:
        """Check if event exists."""
        return self.get(event_ticker) is not None


class EventDependencyRepository:
    """Repository for event dependency operations."""

    def __init__(self, db=None):
        """Initialize repository with database connection."""
        self.db = db or get_db()

    def create(
        self,
        event_a_ticker: str,
        event_b_ticker: str,
        dependency_type: str,
        dependency_score: float,
        constraints: Dict[str, Any],
        llm_responses: Dict[str, Any],
        consensus_method: str,
        round_1_responses: Optional[Dict[str, Any]] = None,
        round_2_responses: Optional[Dict[str, Any]] = None,
        convergence_metrics: Optional[Dict[str, Any]] = None,
        analysis_mode: str = "full_analysis",
    ) -> int:
        """Create dependency record, returns new ID."""
        constraints_json = json.dumps(constraints)
        llm_responses_json = json.dumps(llm_responses)
        round_1_json = json.dumps(round_1_responses) if round_1_responses else None
        round_2_json = json.dumps(round_2_responses) if round_2_responses else None
        convergence_json = json.dumps(convergence_metrics) if convergence_metrics else None

        cursor = self.db.conn.cursor()
        cursor.execute(
            """
            INSERT INTO event_dependencies (
                event_a_ticker, event_b_ticker, dependency_type, dependency_score,
                constraints_json, llm_responses_json, consensus_method,
                round_1_responses, round_2_responses, convergence_metrics, analysis_mode
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event_a_ticker,
                event_b_ticker,
                dependency_type,
                dependency_score,
                constraints_json,
                llm_responses_json,
                consensus_method,
                round_1_json,
                round_2_json,
                convergence_json,
                analysis_mode,
            ),
        )
        self.db.conn.commit()
        return cursor.lastrowid

    def get(self, dependency_id: int) -> Optional[Dict[str, Any]]:
        """Get dependency by ID."""
        cursor = self.db.conn.cursor()
        cursor.execute(
            "SELECT * FROM event_dependencies WHERE id = ?", (dependency_id,)
        )
        row = cursor.fetchone()
        return dict(row) if row else None

    def get_by_event_pair(
        self, event_a_ticker: str, event_b_ticker: str
    ) -> Optional[Dict[str, Any]]:
        """Get dependency for specific event pair."""
        cursor = self.db.conn.cursor()
        cursor.execute(
            """
            SELECT * FROM event_dependencies
            WHERE event_a_ticker = ? AND event_b_ticker = ?
            """,
            (event_a_ticker, event_b_ticker),
        )
        row = cursor.fetchone()
        return dict(row) if row else None

    def get_all(self) -> List[Dict[str, Any]]:
        """Get all dependencies."""
        cursor = self.db.conn.cursor()
        cursor.execute(
            "SELECT * FROM event_dependencies ORDER BY detected_at DESC"
        )
        return [dict(row) for row in cursor.fetchall()]

    def get_all_unverified(self) -> List[Dict[str, Any]]:
        """Get all dependencies pending human verification."""
        cursor = self.db.conn.cursor()
        cursor.execute(
            """
            SELECT * FROM event_dependencies
            WHERE human_verified = FALSE
            ORDER BY dependency_score DESC, detected_at DESC
            """
        )
        return [dict(row) for row in cursor.fetchall()]

    def mark_verified(
        self, dependency_id: int, verified: bool, notes: Optional[str] = None
    ) -> None:
        """Mark dependency as verified by human."""
        cursor = self.db.conn.cursor()
        cursor.execute(
            """
            UPDATE event_dependencies
            SET human_verified = ?,
                verification_notes = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (verified, notes, dependency_id),
        )
        self.db.conn.commit()

    def check_pairs_exist(
        self, event_pairs: List[tuple[str, str]]
    ) -> Dict[tuple[str, str], bool]:
        """Batch check if pairs already analyzed (any mode).

        Args:
            event_pairs: List of (ticker_a, ticker_b) tuples

        Returns:
            Dict mapping (ticker_a, ticker_b) -> exists
        """
        if not event_pairs:
            return {}

        # Batch queries to avoid SQLite expression tree depth limit (1000)
        # Process in chunks of 100 pairs to stay well under the limit
        BATCH_SIZE = 100
        existing = set()

        for i in range(0, len(event_pairs), BATCH_SIZE):
            batch = event_pairs[i:i + BATCH_SIZE]

            # Build query with OR conditions for this batch
            placeholders = " OR ".join(
                ["(event_a_ticker = ? AND event_b_ticker = ?)"] * len(batch)
            )
            flat_values = [val for pair in batch for val in pair]

            query = f"""
                SELECT event_a_ticker, event_b_ticker
                FROM event_dependencies
                WHERE {placeholders}
            """

            cursor = self.db.conn.cursor()
            cursor.execute(query, flat_values)
            result = cursor.fetchall()

            # Add results from this batch to existing set
            existing.update((row[0], row[1]) for row in result)

        # Return dict with existence status for each input pair
        return {pair: pair in existing for pair in event_pairs}


class ArbitrageOpportunityRepository:
    """Repository for arbitrage opportunity operations."""

    def __init__(self, db=None):
        """Initialize repository with database connection."""
        self.db = db or get_db()

    def create(
        self,
        dependency_id: int,
        event_a_ticker: str,
        event_b_ticker: str,
        min_cost: float,
        expected_profit: float,
        optimal_portfolio: Dict[str, Any],
        market_ids: List[str],
        current_prices: Dict[str, float],
        constraints: Dict[str, Any],
        ip_solver_metadata: Optional[Dict[str, Any]] = None,
    ) -> int:
        """Create arbitrage opportunity record."""
        optimal_portfolio_json = json.dumps(optimal_portfolio)
        market_ids_json = json.dumps(market_ids)
        current_prices_json = json.dumps(current_prices)
        constraints_json = json.dumps(constraints)
        ip_solver_json = json.dumps(ip_solver_metadata) if ip_solver_metadata else None

        cursor = self.db.conn.cursor()
        cursor.execute(
            """
            INSERT INTO arbitrage_opportunities (
                dependency_id, event_a_ticker, event_b_ticker,
                min_cost, expected_profit, optimal_portfolio_json,
                market_ids_json, current_prices_json, constraints_json,
                ip_solver_metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                dependency_id,
                event_a_ticker,
                event_b_ticker,
                min_cost,
                expected_profit,
                optimal_portfolio_json,
                market_ids_json,
                current_prices_json,
                constraints_json,
                ip_solver_json,
            ),
        )
        self.db.conn.commit()
        return cursor.lastrowid

    def get(self, arbitrage_id: int) -> Optional[Dict[str, Any]]:
        """Get arbitrage opportunity by ID."""
        cursor = self.db.conn.cursor()
        cursor.execute(
            "SELECT * FROM arbitrage_opportunities WHERE id = ?", (arbitrage_id,)
        )
        row = cursor.fetchone()
        return dict(row) if row else None

    def get_all(self) -> List[Dict[str, Any]]:
        """Get all opportunities."""
        cursor = self.db.conn.cursor()
        cursor.execute(
            """
            SELECT * FROM arbitrage_opportunities
            ORDER BY expected_profit DESC, detected_at DESC
            """
        )
        return [dict(row) for row in cursor.fetchall()]

    def get_by_status(self, status: str) -> List[Dict[str, Any]]:
        """Get opportunities by status (detected, verified, rejected, executed)."""
        cursor = self.db.conn.cursor()
        cursor.execute(
            """
            SELECT * FROM arbitrage_opportunities
            WHERE status = ?
            ORDER BY expected_profit DESC, detected_at DESC
            """,
            (status,),
        )
        return [dict(row) for row in cursor.fetchall()]

    def update_status(
        self, arbitrage_id: int, status: str, notes: Optional[str] = None
    ) -> None:
        """Update opportunity status."""
        cursor = self.db.conn.cursor()

        if notes:
            cursor.execute(
                """
                UPDATE arbitrage_opportunities
                SET status = ?,
                    verification_notes = ?,
                    human_verified = TRUE,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (status, notes, arbitrage_id),
            )
        else:
            cursor.execute(
                """
                UPDATE arbitrage_opportunities
                SET status = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (status, arbitrage_id),
            )
        self.db.conn.commit()

    def mark_executed(
        self, arbitrage_id: int, execution_details: Dict[str, Any]
    ) -> None:
        """Mark opportunity as executed with trade details."""
        execution_json = json.dumps(execution_details)

        cursor = self.db.conn.cursor()
        cursor.execute(
            """
            UPDATE arbitrage_opportunities
            SET trade_executed = TRUE,
                execution_details = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (execution_json, arbitrage_id),
        )
        self.db.conn.commit()
