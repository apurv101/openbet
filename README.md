# Openbet

Automated betting analysis and execution on Kalshi markets using multiple LLM providers.

## Overview

Openbet is a Python CLI application that helps analyze betting markets on Kalshi by leveraging multiple Large Language Models (Claude, OpenAI, Grok, Gemini) to provide consensus-based confidence scores for betting decisions.

## Features

- **Market Tracking**: Add and monitor Kalshi markets in a local SQLite database
- **Multi-LLM Analysis**: Get betting insights from Claude, OpenAI, Grok, and Gemini simultaneously
- **Consensus Scoring**: Combine multiple LLM opinions into actionable confidence scores
- **Automated Betting**: Place bets based on stored analysis results
- **Full Context**: Analysis includes market details, prices, positions, history, and metrics

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd openbet
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

Or install in development mode:
```bash
pip install -e .
```

3. Configure environment variables:
```bash
cp .env.example .env
# Edit .env with your API credentials
```

## Configuration

Create a `.env` file with the following variables:

```ini
# Kalshi API
KALSHI_API_KEY=your_kalshi_api_key
KALSHI_API_SECRET=your_kalshi_api_secret
KALSHI_BASE_URL=https://api.kalshi.com/v2

# LLM Providers
ANTHROPIC_API_KEY=your_anthropic_api_key
OPENAI_API_KEY=your_openai_api_key
XAI_API_KEY=your_xai_api_key
GOOGLE_API_KEY=your_google_api_key

# Database
DATABASE_PATH=data/openbet.db

# Logging
LOG_LEVEL=INFO
LOG_FILE=openbet.log

# LLM Model Configuration (Optional - defaults shown)
DEFAULT_LLM_MODEL_CLAUDE=claude-3-5-sonnet-20241022
DEFAULT_LLM_MODEL_OPENAI=gpt-4o
DEFAULT_LLM_MODEL_GROK=grok-3
DEFAULT_LLM_MODEL_GEMINI=gemini-1.5-flash
```

### LLM Model Configuration

You can customize which models are used for each provider. Current recommended models:

| Provider | Model | Notes |
|----------|-------|-------|
| **Claude (Anthropic)** | `claude-3-5-sonnet-20241022` | Best balance of performance/cost |
| | `claude-opus-4-5-20251101` | Most capable (requires credits) |
| **OpenAI** | `gpt-4o` | Latest GPT-4 Optimized |
| | `o1` | For complex reasoning tasks |
| **Grok (XAI)** | `grok-3` | Latest Grok model |
| **Gemini (Google)** | `gemini-1.5-flash` | Fast and efficient |
| | `gemini-1.5-pro` | More capable |

> **Note**: Make sure you have sufficient API credits for your chosen providers. The analyzer will skip providers that fail and use available ones for consensus.

## Usage

### Check Market Details
Display information about a specific market:
```bash
python -m openbet.cli check-market <market_id>
```

Example:
```bash
python -m openbet.cli check-market KXFOXNEWSMENTION-26FEB04-TRUM
```

### Add Market to Database
Track a market for analysis and betting:
```bash
python -m openbet.cli add-market <market_id>
```

### List Markets in Database
View all markets currently tracked in the database:
```bash
python -m openbet.cli list-markets

# Filter by status
python -m openbet.cli list-markets --status active
```

### Find Markets by Series/Event Ticker
Discover all markets within a specific event or series:
```bash
# Find all markets in a series
python -m openbet.cli find-markets <event_ticker>

# Find and add all markets to database
python -m openbet.cli find-markets <event_ticker> --add-all
```

Example:
```bash
# Find all markets for the Fox News mention event
python -m openbet.cli find-markets kxfoxnewsmention-26feb04

# Add all markets from that series to database
python -m openbet.cli find-markets kxfoxnewsmention-26feb04 --add-all
```

### Run Analysis
Analyze one or all markets using multiple LLM providers (Claude, OpenAI, Grok, Gemini). The analyzer automatically adds markets to the database if they don't exist.

#### Basic Usage
```bash
# Analyze a specific market (auto-adds to database if needed)
python -m openbet.cli analyze --market-id <market_id>

# Analyze all tracked markets
python -m openbet.cli analyze --all

# Analyze specific option within a market
python -m openbet.cli analyze --market-id <market_id> --option <option_name>
```

#### Analysis Flags and Options

| Flag/Option | Description | Default |
|------------|-------------|---------|
| `--market-id <id>` | Specific market ticker to analyze | None |
| `--all` | Analyze all markets in database | False |
| `--option <name>` | Specific option within market to analyze | None |
| `--force` | Force fresh analysis, bypass cache | False |
| `--cache-hours <hours>` | Cache validity duration in hours | 24 |

#### Caching Behavior

By default, the analyze command uses **intelligent caching** to save API costs and improve speed:

- **First analysis**: Calls all LLM providers → saves to database → returns results
- **Within cache period** (default 24 hours): Returns cached results instantly
- **After cache expiry**: Runs fresh LLM analysis → updates database
- **Force mode** (`--force`): Always runs fresh analysis regardless of cache age

```bash
# Use cached results if available (within 24 hours)
python -m openbet.cli analyze --market-id KXPRESPERSON-28-JVAN

# Force fresh analysis, bypass cache
python -m openbet.cli analyze --market-id KXPRESPERSON-28-JVAN --force

# Custom cache duration (12 hours instead of 24)
python -m openbet.cli analyze --market-id KXPRESPERSON-28-JVAN --cache-hours 12

# Analyze all markets with caching
python -m openbet.cli analyze --all

# Force fresh analysis for all markets
python -m openbet.cli analyze --all --force
```

#### Example Output

When you run analysis, you'll see:
- ✅ Cache status (cached vs fresh analysis)
- 📊 Individual confidence scores from each LLM provider
- 🎯 Consensus confidence scores (YES/NO)
- ⏱️ Analysis timestamp

```
Analyzing market KXPRESPERSON-28-JVAN...

✓ Fresh analysis generated

Analysis Results
┏━━━━━━━━━━┳━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━┓
┃ Provider ┃ YES Confidence ┃ NO Confidence  ┃
┡━━━━━━━━━━╇━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━┩
│ Claude   │ 65.0%          │ 35.0%          │
│ Openai   │ 62.5%          │ 37.5%          │
│ Grok     │ 68.0%          │ 32.0%          │
│ Gemini   │ 64.5%          │ 35.5%          │
│ CONSENSUS│ 65.0%          │ 35.0%          │
└──────────┴────────────────┴────────────────┘

✓ Analysis complete
```

#### Auto-Add Markets

The analyze command automatically fetches and adds markets to the database if they don't exist:
```bash
# No need to run add-market first - just analyze directly
python -m openbet.cli analyze --market-id NEW-MARKET-TICKER

# Output:
# Analyzing market NEW-MARKET-TICKER...
# Market not in database, fetching from Kalshi...
# ✓ Fresh analysis generated
```

### Place a Bet
Execute a bet based on stored analysis:
```bash
python -m openbet.cli place-bet <market_id> --option <option_name> --side <yes|no> --quantity <amount>

# Show analysis before placing bet
python -m openbet.cli place-bet <market_id> --option <option_name> --side yes --quantity 10 --use-analysis
```

## Architecture

The project is organized into modular components:

- **`openbet/cli.py`**: Command-line interface with Click
- **`openbet/config.py`**: Configuration management from environment variables
- **`openbet/database/`**: SQLite database layer (models, repositories, connection)
- **`openbet/kalshi/`**: Kalshi API client and models
- **`openbet/llm/`**: LLM provider implementations (Claude, OpenAI, Grok)
- **`openbet/analysis/`**: Analysis orchestration, context building, and consensus logic
- **`openbet/utils/`**: Logging and helper utilities

## Database Schema

### Markets Table
Stores tracked Kalshi markets with metadata.

### Positions Table
Tracks user positions for each market option.

### Analysis Results Table
Stores LLM analysis results including individual provider responses and consensus scores.

## LLM Analysis

The analysis system:
1. Builds comprehensive context (market details, prices, position, historical analysis, metrics)
2. Calls all configured LLM providers in parallel
3. Calculates consensus using simple average of confidence scores
4. Stores results with full context for future reference

## Development

Install development dependencies:
```bash
pip install -e ".[dev]"
```

Run tests:
```bash
pytest
```

Format code:
```bash
black openbet/
```

Lint:
```bash
ruff openbet/
```

## Roadmap

Future enhancements:
- Automated heartbeat monitoring for continuous analysis
- Weighted consensus methods
- Backtesting and performance tracking
- Risk management and position sizing
- Web UI dashboard

## License

MIT License

## Disclaimer

This tool is for educational and research purposes. Betting involves financial risk. Use at your own discretion and ensure compliance with applicable laws and regulations.
