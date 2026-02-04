"""Database schema definitions for Openbet."""

# SQL schema for creating tables

CREATE_MARKETS_TABLE = """
CREATE TABLE IF NOT EXISTS markets (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    close_time TIMESTAMP,
    status TEXT,
    category TEXT,
    min_tick_size REAL,
    max_tick_size REAL,
    metadata TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

CREATE_POSITIONS_TABLE = """
CREATE TABLE IF NOT EXISTS positions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    market_id TEXT NOT NULL,
    option TEXT NOT NULL,
    side TEXT NOT NULL,
    quantity INTEGER,
    avg_price REAL,
    current_value REAL,
    unrealized_pnl REAL,
    metadata TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (market_id) REFERENCES markets(id),
    UNIQUE(market_id, option, side)
);
"""

CREATE_ANALYSIS_RESULTS_TABLE = """
CREATE TABLE IF NOT EXISTS analysis_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    market_id TEXT NOT NULL,
    option TEXT NOT NULL,
    analysis_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    claude_response TEXT,
    openai_response TEXT,
    grok_response TEXT,
    gemini_response TEXT,

    yes_price REAL,
    no_price REAL,
    volume_24h REAL,
    liquidity_depth REAL,

    consensus_yes_confidence REAL,
    consensus_no_confidence REAL,
    consensus_method TEXT,

    previous_analysis_id INTEGER,
    metadata TEXT,

    FOREIGN KEY (market_id) REFERENCES markets(id),
    FOREIGN KEY (previous_analysis_id) REFERENCES analysis_results(id)
);
"""

CREATE_ANALYSIS_MARKET_INDEX = """
CREATE INDEX IF NOT EXISTS idx_analysis_market
ON analysis_results(market_id);
"""

CREATE_ANALYSIS_TIMESTAMP_INDEX = """
CREATE INDEX IF NOT EXISTS idx_analysis_timestamp
ON analysis_results(analysis_timestamp);
"""

CREATE_TRADING_SIGNALS_TABLE = """
CREATE TABLE IF NOT EXISTS trading_signals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    signal_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    market_id TEXT NOT NULL,
    option TEXT NOT NULL,
    signal_type TEXT NOT NULL,

    consensus_yes_prob REAL NOT NULL,
    consensus_no_prob REAL NOT NULL,
    market_yes_prob REAL NOT NULL,
    market_no_prob REAL NOT NULL,

    divergence_yes REAL NOT NULL,
    divergence_no REAL NOT NULL,
    selected_side TEXT,
    divergence_magnitude REAL NOT NULL,

    recommended_action TEXT,
    recommended_quantity INTEGER,
    recommended_price REAL,
    expected_profit REAL,

    volume_24h REAL,
    liquidity_depth REAL,
    open_interest INTEGER,

    analysis_id INTEGER,

    metadata TEXT,

    FOREIGN KEY (market_id) REFERENCES markets(id),
    FOREIGN KEY (analysis_id) REFERENCES analysis_results(id)
);
"""

CREATE_TRADE_DECISIONS_TABLE = """
CREATE TABLE IF NOT EXISTS trade_decisions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    decision_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    signal_id INTEGER NOT NULL,

    decision TEXT NOT NULL,
    user_notes TEXT,

    executed BOOLEAN DEFAULT FALSE,
    execution_timestamp TIMESTAMP,
    order_id TEXT,
    actual_quantity INTEGER,
    actual_price REAL,
    execution_cost REAL,

    position_id INTEGER,

    realized_pnl REAL,

    metadata TEXT,

    FOREIGN KEY (signal_id) REFERENCES trading_signals(id),
    FOREIGN KEY (position_id) REFERENCES positions(id)
);
"""

CREATE_SIGNALS_MARKET_INDEX = """
CREATE INDEX IF NOT EXISTS idx_signals_market
ON trading_signals(market_id);
"""

CREATE_SIGNALS_TYPE_INDEX = """
CREATE INDEX IF NOT EXISTS idx_signals_type
ON trading_signals(signal_type);
"""

CREATE_SIGNALS_TIMESTAMP_INDEX = """
CREATE INDEX IF NOT EXISTS idx_signals_timestamp
ON trading_signals(signal_timestamp);
"""

CREATE_DECISIONS_SIGNAL_INDEX = """
CREATE INDEX IF NOT EXISTS idx_decisions_signal
ON trade_decisions(signal_id);
"""

CREATE_DECISIONS_TIMESTAMP_INDEX = """
CREATE INDEX IF NOT EXISTS idx_decisions_timestamp
ON trade_decisions(decision_timestamp);
"""

ALL_TABLES = [
    CREATE_MARKETS_TABLE,
    CREATE_POSITIONS_TABLE,
    CREATE_ANALYSIS_RESULTS_TABLE,
    CREATE_ANALYSIS_MARKET_INDEX,
    CREATE_ANALYSIS_TIMESTAMP_INDEX,
    CREATE_TRADING_SIGNALS_TABLE,
    CREATE_TRADE_DECISIONS_TABLE,
    CREATE_SIGNALS_MARKET_INDEX,
    CREATE_SIGNALS_TYPE_INDEX,
    CREATE_SIGNALS_TIMESTAMP_INDEX,
    CREATE_DECISIONS_SIGNAL_INDEX,
    CREATE_DECISIONS_TIMESTAMP_INDEX,
]
