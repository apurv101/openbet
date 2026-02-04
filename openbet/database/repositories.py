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
