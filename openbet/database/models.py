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

ALL_TABLES = [
    CREATE_MARKETS_TABLE,
    CREATE_POSITIONS_TABLE,
    CREATE_ANALYSIS_RESULTS_TABLE,
    CREATE_ANALYSIS_MARKET_INDEX,
    CREATE_ANALYSIS_TIMESTAMP_INDEX,
]
