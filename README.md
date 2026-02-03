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
```

## Usage

### Check Market Details
Display information about a specific market:
```bash
openbet check-market <market_id>
```

### Add Market to Database
Track a market for analysis and betting:
```bash
openbet add-market <market_id>
```

### Run Analysis
Analyze one or all markets using multiple LLM providers:
```bash
# Analyze a specific market
openbet analyze --market-id <market_id>

# Analyze all tracked markets
openbet analyze --all

# Analyze specific option within a market
openbet analyze --market-id <market_id> --option <option_name>
```

### Place a Bet
Execute a bet based on stored analysis:
```bash
openbet place-bet <market_id> --option <option_name> --side <yes|no> --quantity <amount>

# Show analysis before placing bet
openbet place-bet <market_id> --option <option_name> --side yes --quantity 10 --use-analysis
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
