# Openbet

Automated betting analysis and execution on Kalshi markets using multiple LLM providers.

## Overview

Openbet is a Python CLI application that helps analyze betting markets on Kalshi by leveraging multiple Large Language Models (Claude, OpenAI, Grok, Gemini) to provide consensus-based confidence scores for betting decisions.

## Features

- **Market Screening**: Pre-filter markets by liquidity, volume, and open interest to identify quality trading opportunities before spending token money
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

### Screen Markets (Pre-Filter Before Analysis)
Filter markets by liquidity, volume, and open interest to identify which markets are worth spending token money on for LLM analysis. This helps you avoid wasting API costs on low-quality or illiquid markets.

#### Basic Usage
```bash
# Screen top 50 markets with default thresholds
python -m openbet.cli screen-markets

# Screen markets in a specific series
python -m openbet.cli screen-markets --event-ticker KXTRUMPMEET-26FEB

# Screen tracked markets from database
python -m openbet.cli screen-markets --tracked

# Show only markets that pass all filters
python -m openbet.cli screen-markets --passed-only
```

#### Custom Thresholds
```bash
# Set custom thresholds for high-quality markets
python -m openbet.cli screen-markets \
  --min-liquidity 500000 \
  --min-volume 200 \
  --min-open-interest 500 \
  --passed-only

# Lower thresholds for more permissive filtering
python -m openbet.cli screen-markets \
  --min-liquidity 50 \
  --min-volume 10 \
  --min-open-interest 50
```

#### Sorting Options
```bash
# Sort by liquidity (highest first)
python -m openbet.cli screen-markets --sort-by liquidity

# Sort by quality score (default - composite metric)
python -m openbet.cli screen-markets --sort-by quality

# Sort by 24h volume
python -m openbet.cli screen-markets --sort-by volume

# Sort by open interest
python -m openbet.cli screen-markets --sort-by open-interest

# Sort by close time (soonest first)
python -m openbet.cli screen-markets --sort-by close-time
```

#### Screening Flags and Options

| Flag/Option | Description | Default |
|------------|-------------|---------|
| `--tracked` | Screen only tracked markets from database | False |
| `--status <status>` | Filter by market status on API (e.g., 'open') | All statuses |
| `--min-liquidity <amount>` | Minimum liquidity threshold | 100.0 |
| `--min-volume <amount>` | Minimum 24h volume threshold | 50.0 |
| `--min-open-interest <amount>` | Minimum open interest threshold | 100 |
| `--sort-by <field>` | Sort order: quality, liquidity, volume, open-interest, close-time | quality |
| `--passed-only` | Show only markets that pass all filters | False |
| `--limit <count>` | Maximum markets to screen | 50 |
| `--event-ticker <ticker>` | Filter by event/series ticker | None |

#### Understanding the Metrics

**Liquidity** - Total capital available in the market's liquidity pool
- Higher liquidity = Tighter spreads between YES/NO prices
- Higher liquidity = Easier to enter/exit positions without moving price
- Recommended: ≥ $100,000 for serious trading

**Volume (24h)** - Number of contracts traded in last 24 hours
- Indicates recent market activity and interest
- Low volume may mean stale prices or low trader confidence
- Recommended: ≥ 100 contracts for active markets

**Open Interest** - Total number of outstanding contracts
- Shows total market participation and commitment
- Higher OI = More established market with trader conviction
- Recommended: ≥ 500 for meaningful markets

**Quality Score** - Composite metric calculated as:
```
quality_score = (liquidity / min_liquidity) × 0.4 +
                (volume_24h / min_volume) × 0.3 +
                (open_interest / min_open_interest) × 0.3
```

#### Example Output

```
Screening 10 market(s)
Thresholds: Liquidity ≥ 100, Volume ≥ 50, Open Interest ≥ 100

┏━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━┓
┃ Status ┃ Ticker                     ┃  Liquidity ┃ Volume 24h ┃ Open Int. ┃ Quality┃ Issues               ┃
┡━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━┩
│ ✓      │ KXTRUMPMEET-26FEB-JPOW     │    581,550 │        516 │       991 │   5.82 │ —                    │
│ ✗      │ KXELECTION-2026-HOUSE      │     45,000 │         32 │       150 │   0.83 │ Low liquidity...     │
│ ✓      │ KXFED-MAR-RATE-CUT         │    920,000 │      2,100 │     1,500 │  18.20 │ —                    │
└────────┴────────────────────────────┴────────────┴────────────┴───────────┴────────┴──────────────────────┘

Summary
✓ Passed: 7/10
✗ Failed: 3/10

Next: Run 'openbet analyze --market-id <TICKER>' for markets that passed
```

#### Typical Workflow

```bash
# Step 1: Screen markets to find quality candidates
python -m openbet.cli screen-markets --event-ticker KXTRUMPMEET-26FEB --passed-only

# Step 2: Analyze only the markets that passed screening
python -m openbet.cli analyze --market-id KXTRUMPMEET-26FEB-JPOW

# Or for series analysis with pre-screening
python -m openbet.cli screen-markets --event-ticker KXELECTION --passed-only
python -m openbet.cli analyze-series KXELECTION --add-markets
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

### Analyze Markets in a Series

Discover and analyze all markets within a specific event or series in one command:

```bash
# Find and analyze all markets in a series
python -m openbet.cli analyze-series <event_ticker>

# Force fresh analysis for all markets
python -m openbet.cli analyze-series kxtrumpmeet-26feb --force

# Auto-add markets to database before analysis
python -m openbet.cli analyze-series kxtrumpmeet-26feb --add-markets

# Custom cache duration
python -m openbet.cli analyze-series kxtrumpmeet-26feb --cache-hours 12
```

**Example:**
```bash
# Analyze all markets in the Trump meeting series
python -m openbet.cli analyze-series kxtrumpmeet-26feb

# Output:
# Finding markets in series: kxtrumpmeet-26feb...
#
# Found 20 market(s) in series KXTRUMPMEET-26FEB
#
# Analyzing 20 markets...
#
# 1/20 Analyzing KXTRUMPMEET-26FEB-T100 (100+ appearances)...
# ✓ Fresh analysis generated
# [Analysis results table...]
#
# 2/20 Analyzing KXTRUMPMEET-26FEB-T75 (75-99 appearances)...
# ℹ Using cached analysis from 2026-02-03 10:30:45
# [Analysis results table...]
# ...
#
# Analysis Complete
# ✓ Successfully analyzed: 20/20
```

**Options:**

| Flag/Option | Description | Default |
|------------|-------------|---------|
| `--force` | Force fresh analysis for all markets, bypass cache | False |
| `--cache-hours <hours>` | Cache validity duration in hours | 24 |
| `--add-markets` | Add all found markets to database before analysis | False |

**Use Cases:**
- Quickly analyze an entire event series at once
- Refresh analysis for all markets in a series with `--force`
- Discover and analyze new markets without manual add-market commands

### Place a Bet
Execute a bet based on stored analysis:
```bash
python -m openbet.cli place-bet <market_id> --option <option_name> --side <yes|no> --quantity <amount>

# Show analysis before placing bet
python -m openbet.cli place-bet <market_id> --option <option_name> --side yes --quantity 10 --use-analysis
```

## Automated Trading Algorithm

Openbet includes a sophisticated **semi-automated trading algorithm** that identifies and executes profitable trades based on divergence between AI consensus predictions and market-implied probabilities.

### Trading Strategy Overview

The core insight is that markets sometimes misprice outcomes relative to what multiple AI models predict. When there's a significant divergence between the AI consensus and the market price, it presents a trading opportunity. The algorithm:

1. **Identifies Opportunities**: Detects when consensus probability diverges from market-implied probability by a threshold (default: 5%)
2. **Sizes Positions**: Calculates position size proportional to divergence magnitude (bigger edge = larger position)
3. **Enters Trades**: Buys undervalued contracts with user approval
4. **Monitors Convergence**: Tracks positions for exit when market converges to consensus (within 1%)
5. **Exits Profitably**: Sells when convergence occurs, capturing the difference

#### Example Trade Flow

```
Market: KXPRESPERSON-28-MRUB (Who will win the presidential election? :: Republican - Marco Rubio)

Initial State:
├─ AI Consensus (YES): 12.0%
├─ Market Implied (YES): 6.0%
└─ Divergence: 6.0% ✓ Exceeds 5% threshold

Entry Signal Generated:
├─ Action: BUY YES
├─ Reasoning: Market undervalues YES (6%) vs AI consensus (12%)
├─ Position Size: 17 contracts (proportional to 6% divergence)
├─ Entry Price: $0.06 per contract
├─ Expected Profit: $1.02 (if market moves to consensus)
└─ Cost: $1.02 (17 × $0.06)

Position Monitoring:
├─ Day 1: Market 6%, Consensus 12% → Hold (divergence: 6%)
├─ Day 2: Market 8%, Consensus 12% → Hold (divergence: 4%)
├─ Day 3: Market 11%, Consensus 12% → Exit! (divergence: 1% ✓ Within threshold)
└─ Exit Price: $0.11 per contract

Exit Execution:
├─ Sell 17 contracts at $0.11
├─ Revenue: $1.87 (17 × $0.11)
├─ Cost: $1.02
└─ Realized Profit: $0.85 (+83% return)
```

### Trading Commands

#### 1. Scan for Opportunities

Automatically scan all tracked markets to find trading opportunities:

```bash
# Scan all markets with default 5% threshold
python -m openbet.cli scan-opportunities

# Scan specific market
python -m openbet.cli scan-opportunities --market-id KXPRESPERSON-28-MRUB

# More aggressive (2% threshold)
python -m openbet.cli scan-opportunities --threshold 0.02

# More conservative (10% threshold)
python -m openbet.cli scan-opportunities --threshold 0.10

# Show top 5 opportunities
python -m openbet.cli scan-opportunities --limit 5

# Force fresh analysis (bypass cache)
python -m openbet.cli scan-opportunities --force
```

**Output Example:**
```
Scanning for opportunities (threshold: 5.0%)...

Trading Opportunities (3 found)

┏━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━┳━━━━━┳━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━┓
┃ Market ID            ┃ Side ┃ Divergence ┃ Consensus ┃ Market  ┃ Qty ┃ Price  ┃ Expected $ ┃ Warnings ┃
┡━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━╇━━━━━╇━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━┩
│ KXPRESPERSON-28-MRUB │ YES  │ 8.5%       │ 14.5%     │ 6.0%    │ 24  │ $0.06  │ $2.04      │ -        │
│ KXMARKET-28-OPTION   │ NO   │ 6.2%       │ 42.4%     │ 36.2%   │ 16  │ $0.36  │ $0.99      │ -        │
│ KXOTHER-28-TRADE     │ YES  │ 5.3%       │ 25.3%     │ 20.0%   │ 12  │ $0.20  │ $0.64      │ 1        │
└──────────────────────┴──────┴────────────┴───────────┴─────────┴─────┴────────┴────────────┴──────────┘

Use 'recommend-trade <MARKET_ID>' to analyze a specific opportunity
```

**Options:**

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--market-id` | String | All markets | Scan specific market instead of all |
| `--threshold` | Float | 0.05 | Minimum divergence to trigger signal (e.g., 0.05 = 5%) |
| `--limit` | Integer | 10 | Maximum opportunities to display |
| `--force` | Boolean | False | Force fresh analysis, bypass cache |

#### 2. Recommend Trade

Get detailed analysis and execute a trade on a specific market:

```bash
# Analyze and recommend trade (with approval prompt)
python -m openbet.cli recommend-trade KXPRESPERSON-28-MRUB

# Auto-approve (skip confirmation prompt)
python -m openbet.cli recommend-trade KXPRESPERSON-28-MRUB --auto-approve

# Override recommended quantity
python -m openbet.cli recommend-trade KXPRESPERSON-28-MRUB --quantity 20

# Override recommended price
python -m openbet.cli recommend-trade KXPRESPERSON-28-MRUB --price 0.07

# Force fresh analysis (bypass cache)
python -m openbet.cli recommend-trade KXPRESPERSON-28-MRUB --force

# Custom cache duration
python -m openbet.cli recommend-trade KXPRESPERSON-28-MRUB --cache-hours 12
```

**Output Example:**
```
Analyzing KXPRESPERSON-28-MRUB...

Market Analysis

┏━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Metric      ┃ Value                                        ┃
┡━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ Market ID   │ KXPRESPERSON-28-MRUB                         │
│ Signal Type │ ENTRY                                        │
│ Timestamp   │ 2026-02-03 18:30:45                          │
└─────────────┴──────────────────────────────────────────────┘

Consensus vs Market

┏━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━━━┓
┃ Side ┃ Consensus ┃ Market  ┃ Divergence ┃
┡━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━━━┩
│ YES  │ 14.5%     │ 6.0%    │ 8.5%       │
│ NO   │ 85.5%     │ 94.0%   │ 8.5%       │
└──────┴───────────┴─────────┴────────────┘

Recommendation

┏━━━━━━━━━━━━━━━┳━━━━━━━━━┓
┃ Field         ┃ Value   ┃
┡━━━━━━━━━━━━━━━╇━━━━━━━━━┩
│ Action        │ BUY_YES │
│ Side          │ YES     │
│ Quantity      │ 24      │
│ Price         │ $0.06   │
│ Expected Profit│ $2.04  │
│ Divergence    │ 8.5%    │
└───────────────┴─────────┘

Proceed with trade? [y/N]: y

Executing trade...
✓ Trade executed successfully!
Order ID: abc123xyz789
Quantity: 24
Price: $0.06
Cost: $1.44
```

**Options:**

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--auto-approve` | Boolean | False | Skip confirmation prompt, execute immediately |
| `--quantity` | Integer | Calculated | Override recommended position size |
| `--price` | Float | Market price | Override recommended limit price |
| `--force` | Boolean | False | Force fresh analysis, bypass cache |
| `--cache-hours` | Integer | 24 | Cache validity duration in hours |

**Workflow:**
1. Fetches AI consensus (uses 24-hour cache by default, unless `--force` specified)
2. Gets current market orderbook
3. Calculates divergence and determines trade direction
4. Sizes position proportionally to divergence
5. Displays detailed breakdown with risk warnings
6. Prompts for approval (unless `--auto-approve`)
7. Executes trade and updates position database
8. Stores decision for performance tracking

#### 3. Monitor Exits

Check open positions for exit opportunities when market converges to consensus:

```bash
# Monitor all positions (with approval prompts)
python -m openbet.cli monitor-exits

# Auto-execute all exits meeting criteria
python -m openbet.cli monitor-exits --auto-sell

# More aggressive exit (2% convergence threshold)
python -m openbet.cli monitor-exits --threshold 0.02

# More patient exit (0.5% convergence threshold)
python -m openbet.cli monitor-exits --threshold 0.005
```

**Output Example:**
```
Monitoring positions for exits (threshold: 1.0%)...

Exit Opportunities (2 positions)

┏━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━━━━┓
┃ Market ID            ┃ Side ┃ Quantity ┃ Current Price ┃ Consensus ┃ Divergence ┃ Expected P&L ┃
┡━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━━━━┩
│ KXPRESPERSON-28-MRUB │ YES  │ 24       │ $0.14         │ 14.2%     │ 0.2%       │ $1.92        │
│ KXMARKET-28-OPTION   │ NO   │ 16       │ $0.41         │ 41.5%     │ 0.5%       │ $0.80        │
└──────────────────────┴──────┴──────────┴───────────────┴───────────┴────────────┴──────────────┘

Exit KXPRESPERSON-28-MRUB?
Expected P&L: $1.92
Proceed with exit? [y/N]: y

Exiting KXPRESPERSON-28-MRUB...
✓ Exited successfully. P&L: $1.92

Exit KXMARKET-28-OPTION?
Expected P&L: $0.80
Proceed with exit? [y/N]: y

Exiting KXMARKET-28-OPTION...
✓ Exited successfully. P&L: $0.80
```

**Options:**

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--auto-sell` | Boolean | False | Automatically execute all exits without prompts |
| `--threshold` | Float | 0.01 | Maximum divergence for exit (e.g., 0.01 = 1%) |

**Workflow:**
1. Fetches all open positions from database
2. Gets current consensus and market prices
3. Calculates current divergence for each position
4. Identifies positions where market has converged to consensus
5. Displays exit opportunities with expected P&L
6. Prompts for approval per position (unless `--auto-sell`)
7. Executes sell orders and records realized P&L

#### 4. Trading History

View performance statistics and historical trading signals:

```bash
# Show last 20 trades
python -m openbet.cli trading-history

# Show last 50 trades
python -m openbet.cli trading-history --limit 50

# Filter by signal type
python -m openbet.cli trading-history --signal-type entry
python -m openbet.cli trading-history --signal-type exit

# Filter by decision
python -m openbet.cli trading-history --decision approved
python -m openbet.cli trading-history --decision rejected
```

**Output Example:**
```
Trading History

Recent Signals (20)

┏━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━┳━━━━━━┳━━━━━━━━━━━━┳━━━━━┳━━━━━━━━━━┳━━━━━━━━━━┓
┃ Time               ┃ Market               ┃ Type   ┃ Side ┃ Divergence ┃ Qty ┃ Decision ┃ Executed ┃
┡━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━╇━━━━━━╇━━━━━━━━━━━━╇━━━━━╇━━━━━━━━━━╇━━━━━━━━━━┩
│ 2026-02-03 18:30:45│ KXPRESPERSON-28-MRUB │ entry  │ YES  │ 8.5%       │ 24  │ approved │ ✓        │
│ 2026-02-03 15:22:10│ KXMARKET-28-OPTION   │ entry  │ NO   │ 6.2%       │ 16  │ approved │ ✓        │
│ 2026-02-03 10:15:33│ KXOTHER-28-TRADE     │ entry  │ YES  │ 5.3%       │ 12  │ rejected │ -        │
│ 2026-02-02 14:45:22│ KXPRESPERSON-28-MRUB │ exit   │ YES  │ 0.2%       │ 24  │ approved │ ✓        │
│ 2026-02-02 09:30:15│ KXMARKET-28-OPTION   │ exit   │ NO   │ 0.5%       │ 16  │ approved │ ✓        │
└────────────────────┴──────────────────────┴────────┴──────┴────────────┴─────┴──────────┴──────────┘

Performance Statistics

┏━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━┓
┃ Metric              ┃ Value  ┃
┡━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━┩
│ Total Signals       │ 47     │
│ Total Decisions     │ 45     │
│ Approved            │ 38     │
│ Rejected            │ 7      │
│ Approval Rate       │ 84.4%  │
│ Executed Trades     │ 38     │
│ Total Closed Trades │ 18     │
│ Wins                │ 14     │
│ Losses              │ 4      │
│ Win Rate            │ 77.8%  │
│ Total P&L           │ $24.56 │
│ Avg P&L per Trade   │ $1.36  │
└─────────────────────┴────────┘
```

**Options:**

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--limit` | Integer | 20 | Number of signals to display |
| `--signal-type` | Choice | all | Filter by type: `entry`, `exit`, or `all` |
| `--decision` | Choice | all | Filter by decision: `approved`, `rejected`, `ignored`, or `all` |

### Position Sizing Formula

The algorithm uses **proportional position sizing** based on divergence magnitude:

```
position_size = base_amount × (divergence / 0.05) ^ scaling_factor
```

**Parameters:**
- `base_amount`: Minimum contracts for 5% divergence (default: 10)
- `scaling_factor`: Aggressiveness multiplier (default: 1.5)
- `max_position`: Position cap (default: 100 contracts)

**Examples:**

| Divergence | Calculation | Position Size |
|------------|-------------|---------------|
| 5% | 10 × (0.05 / 0.05)^1.5 | 10 contracts |
| 10% | 10 × (0.10 / 0.05)^1.5 | 28 contracts |
| 15% | 10 × (0.15 / 0.05)^1.5 | 52 contracts |
| 20% | 10 × (0.20 / 0.05)^1.5 | 80 contracts |
| 30% | 10 × (0.30 / 0.05)^1.5 | 100 contracts (capped) |

### Risk Management

The algorithm includes multiple risk safeguards:

#### Built-in Filters
- **Liquidity Check**: Minimum liquidity threshold (default: 100)
- **Volume Check**: Minimum 24h volume (default: 50)
- **Position Cap**: Maximum contracts per trade (default: 100)
- **Spread Check**: Rejects markets with spreads > 10%
- **Status Validation**: Only trades "open" markets
- **User Approval**: Required for all executions (semi-automated)

#### Audit Trail
- All signals stored in `trading_signals` table
- All decisions recorded in `trade_decisions` table
- Full historical record for compliance and backtesting
- Links to original analysis via `analysis_id`

### Configuration

Customize trading parameters via CLI options or environment variables:

#### Via CLI Options
```bash
# Adjust entry threshold
python -m openbet.cli scan-opportunities --threshold 0.08  # 8% minimum

# Adjust exit threshold
python -m openbet.cli monitor-exits --threshold 0.005  # 0.5% convergence
```

#### Via Environment Variables
Add to your `.env` file:
```ini
# Trading Strategy Parameters (Optional)
OPENBET_ENTRY_THRESHOLD=0.05      # 5% minimum divergence for entry
OPENBET_EXIT_THRESHOLD=0.01       # 1% convergence for exit
OPENBET_BASE_POSITION=10          # Base position size
OPENBET_MAX_POSITION=100          # Maximum position cap
OPENBET_MIN_LIQUIDITY=100.0       # Minimum liquidity filter
OPENBET_MIN_VOLUME=50.0           # Minimum 24h volume filter
```

### Example Daily Workflow

Here's a typical daily trading workflow:

```bash
# Morning: Scan for new opportunities
python -m openbet.cli scan-opportunities --limit 5

# Review top opportunity in detail
python -m openbet.cli recommend-trade KXPRESPERSON-28-MRUB
# [Review analysis, approve if attractive]

# Afternoon: Check positions for exits
python -m openbet.cli monitor-exits
# [Exit positions that have converged]

# Evening: Review performance
python -m openbet.cli trading-history --limit 20

# Weekly: Review win rate and total P&L
python -m openbet.cli trading-history --signal-type exit --limit 100
```

### Strategy Performance Tips

1. **Conservative Entry (Recommended)**: Use 5%+ threshold to trade only high-conviction divergences
2. **Quick Exits**: Use 1% convergence threshold to capture profits before reversal
3. **Volume Matters**: Higher volume = better fills and less slippage
4. **Diversify**: Trade multiple markets to spread risk
5. **Track Performance**: Regularly review `trading-history` to identify patterns
6. **Adjust Thresholds**: Increase thresholds in volatile markets, decrease in stable markets

## Architecture

The project is organized into modular components:

- **`openbet/cli.py`**: Command-line interface with Click
- **`openbet/config.py`**: Configuration management from environment variables
- **`openbet/database/`**: SQLite database layer (models, repositories, connection)
- **`openbet/kalshi/`**: Kalshi API client and models
- **`openbet/llm/`**: LLM provider implementations (Claude, OpenAI, Grok, Gemini)
- **`openbet/analysis/`**: Analysis orchestration, context building, and consensus logic
- **`openbet/trading/`**: Trading algorithm (signals, sizing, risk management, strategy)
- **`openbet/utils/`**: Logging and helper utilities

### Trading Module Structure

The trading system is organized into focused components:

- **`trading/models.py`**: Pydantic models (TradingSignal, TradeDecision, RiskConfig)
- **`trading/signals.py`**: Entry/exit signal generation logic
- **`trading/sizing.py`**: Position sizing calculations (proportional to divergence)
- **`trading/risk.py`**: Risk filters (liquidity, volume, spread checks)
- **`trading/strategy.py`**: Main orchestrator that ties everything together

## Database Schema

### Markets Table
Stores tracked Kalshi markets with metadata including ticker, title, close time, status, and category.

### Positions Table
Tracks user positions for each market option with quantity, average price, current value, and unrealized P&L.

### Analysis Results Table
Stores LLM analysis results including individual provider responses (Claude, OpenAI, Grok, Gemini), consensus scores, market prices at analysis time, and links to historical analyses.

### Trading Signals Table
Records all entry and exit trading signals with:
- Consensus vs market probabilities (YES and NO)
- Divergence calculations
- Recommended action, quantity, and price
- Expected profit
- Market metrics (volume, liquidity, open interest)
- Risk warnings and filter results

### Trade Decisions Table
Tracks user decisions on trading signals with:
- Decision type (approved, rejected, ignored)
- Execution details (order ID, quantity, price, cost)
- Realized P&L for exits
- Links to positions and signals for complete audit trail

## LLM Analysis

The analysis system:
1. Builds comprehensive context (market details, prices, position, historical analysis, metrics)
2. Calls all configured LLM providers in parallel
3. Calculates consensus using iterative reasoning (two-round analysis with peer feedback)
4. Stores results with full context for future reference

### Consensus Method: Iterative Reasoning

**Advanced two-round analysis** where LLMs see anonymized peer reasoning and revise their predictions.

```bash
python -m openbet.cli analyze --market-id KXMARKET-ID
```

**How it works**:

**Round 1 - Initial Analysis**:
- All 4 LLMs (Claude, OpenAI, Grok, Gemini) analyze the market independently
- Each provides YES/NO confidence scores + detailed reasoning
- Results and reasoning are stored

**Round 2 - Peer Review & Revision**:
- Each LLM receives:
  - Anonymized peer analyses (as "Analyst A", "Analyst B", etc.)
  - Their own previous response for continuity
- Providers can revise their confidence based on peer insights
- **Anonymization reduces bias** - LLMs don't know which provider said what

**Final Consensus**:
- Calculate average from Round 2 revised confidence scores
- Track convergence metrics (how much each provider changed)

**Example Output**:

```
Analyzing market KXPRESPERSON-28-JVAN...

✓ Fresh analysis generated

Round 1: Initial Analyses
┏━━━━━━━━━━┳━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━┓
┃ Provider ┃ YES Confidence ┃ NO Confidence ┃
┡━━━━━━━━━━╇━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━┩
│ Claude   │ 70.0%          │ 30.0%         │
│ Openai   │ 65.0%          │ 35.0%         │
│ Grok     │ 80.0%          │ 20.0%         │
│ Gemini   │ 72.0%          │ 28.0%         │
└──────────┴────────────────┴───────────────┘

Round 2: Revised Analyses (after peer review)
┏━━━━━━━━━━┳━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━┳────────┓
┃ Provider ┃ YES Confidence ┃ NO Confidence ┃ Change ┃
┡━━━━━━━━━━╇━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━╇────────┩
│ Claude   │ 75.0%          │ 25.0%         │ +5.0%  │
│ Openai   │ 68.0%          │ 32.0%         │ +3.0%  │
│ Grok     │ 77.0%          │ 23.0%         │ -3.0%  │
│ Gemini   │ 74.0%          │ 26.0%         │ +2.0%  │
├──────────┼────────────────┼───────────────┼────────┤
│ CONSENSUS│ 73.5%          │ 26.5%         │        │
└──────────┴────────────────┴───────────────┴────────┘

Convergence: Average shift 3.25%, Max shift 5.0%

✓ Analysis complete
```

**When to use**:
- High-stakes decisions where accuracy is critical
- Markets where reasoning quality matters more than speed
- When you want to capture "wisdom of crowds" effect
- Complex markets that benefit from multiple perspectives

**Benefits**:
- **Higher accuracy**: LLMs can correct each other's blind spots
- **Transparency**: See how opinions evolved from Round 1 to Round 2
- **Reduced bias**: Anonymization prevents over-reliance on specific providers
- **Convergence insights**: Track consensus formation dynamics

**Performance**:
- **Latency**: ~2x simple average (two sequential rounds)
- **API Costs**: ~2x simple average (double LLM calls)
- **Token Usage**: Round 2 prompts are 2-3x longer (includes peer reasoning)

**Data Storage**:
- Both Round 1 and Round 2 responses stored in database metadata
- Convergence metrics tracked (average shift, max shift)
- Full audit trail of reasoning evolution

**Use Cases**:
```bash
# Analyze a specific market
python -m openbet.cli analyze --market-id KXELECTION-28-PRES

# Force fresh analysis (bypass cache)
python -m openbet.cli analyze --market-id KXMARKET-ID --force

# Analyze all markets
python -m openbet.cli analyze --all
```

**Trading Integration**:

Iterative reasoning works seamlessly with the trading algorithm:

```bash
# Scan opportunities using iterative reasoning
python -m openbet.cli scan-opportunities

# Get trade recommendations
python -m openbet.cli recommend-trade KXMARKET-ID
```

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

### Implemented ✓
- ✅ Risk management and position sizing
- ✅ Performance tracking and trade history
- ✅ Automated opportunity scanning
- ✅ Semi-automated trading with approval workflow
- ✅ Position monitoring and exit signals
- ✅ **Iterative reasoning consensus** - Multi-round LLM analysis with peer feedback

### Future Enhancements
- Automated heartbeat monitoring for continuous analysis
- Fully automated mode (no approval required)
- Advanced backtesting with historical price data
- Kelly Criterion position sizing
- Stop-loss automation
- Multi-market portfolio limits
- SMS/email alerts for signals
- Web UI dashboard with charts
- Machine learning model training on performance

## License

MIT License

## Disclaimer

This tool is for educational and research purposes. Betting involves financial risk. Use at your own discretion and ensure compliance with applicable laws and regulations.
