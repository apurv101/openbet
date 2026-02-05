# Arbitrage Detection System - Technical Documentation

**Version:** 1.0
**Date:** February 2026
**System:** OpenBet Dependency-Based Arbitrage Detection

---

## Table of Contents

1. [Overview](#overview)
2. [Core Algorithms](#core-algorithms)
3. [System Architecture](#system-architecture)
4. [Workflow](#workflow)
5. [Implementation Details](#implementation-details)
6. [API Reference](#api-reference)
7. [Usage Examples](#usage-examples)
8. [Performance & Optimization](#performance--optimization)

---

## Overview

### What is Dependency-Based Arbitrage?

Traditional arbitrage detection looks at individual markets in isolation. **Dependency-based arbitrage** recognizes that some prediction markets are logically related, creating opportunities that simple price analysis misses.

**Example:**
- Market A: "Will Trump win Pennsylvania?" - YES: $0.48, NO: $0.52
- Market B: "Will Republicans win PA by 5+ points?" - YES: $0.32, NO: $0.68

Both markets sum to $1.00 individually (no obvious arbitrage). However, there's a logical dependency: **if Republicans win by 5+ points, Trump MUST win Pennsylvania**.

This constraint means one outcome combination is impossible:
- ✗ **Invalid:** "Trump loses" + "GOP wins by 5+"

By constructing a portfolio that covers only the 3 valid outcomes, you can guarantee profit regardless of which outcome occurs.

### System Objectives

1. **Discover Dependencies:** Use AI to identify logical relationships between Kalshi events
2. **Detect Arbitrage:** Use Integer Programming to find guaranteed profit opportunities
3. **Human Verification:** Address the 81.45% LLM accuracy limitation
4. **Safe Execution:** Conservative rate limiting and position sizing

---

## Core Algorithms

### Algorithm 1: Marginal Polytope & Integer Programming

**Purpose:** Detect arbitrage in dependent markets by finding the minimum cost portfolio that guarantees profit across all valid outcomes.

#### What Problem Does It Solve?

**Problem**: Some prediction markets are logically dependent on each other, creating arbitrage opportunities that simple price-checking misses.

**Real-World Example**:
- Market A: "Will Trump win Pennsylvania?" - YES: $0.48, NO: $0.52 (sums to $1.00 ✓)
- Market B: "Will Republicans win PA by 5+ points?" - YES: $0.32, NO: $0.68 (sums to $1.00 ✓)

Both markets look fine individually. But there's a **logical dependency**:
- **If Republicans win by 5+ points, Trump MUST win Pennsylvania**

This constraint means certain outcome combinations are impossible:
- ✓ Valid: "Trump wins" + "GOP wins by 5+"
- ✓ Valid: "Trump wins" + "GOP doesn't win by 5+"
- ✓ Valid: "Trump loses" + "GOP doesn't win by 5+"
- ✗ **Invalid**: "Trump loses" + "GOP wins by 5+" (logically impossible)

**The Arbitrage**:
If the market prices assume 4 independent outcomes but only 3 are valid, you can construct a portfolio that guarantees profit across all valid outcomes.

#### Mathematical Foundation

For markets with `n` conditions, there are `2^n` possible price combinations but only `n` valid outcomes (exactly one condition must be TRUE).

**Marginal Polytope**: The set of all arbitrage-free price vectors.

Define valid outcomes as:
```
Z = {z ∈ {0,1}^n : A^T × z ≥ b}
```

Where:
- **z** = Binary vector (0 or 1 for each condition)
- **A^T × z ≥ b** = Linear constraints representing logical dependencies
- **p** = Current market prices (probability vector)

**Example** (Duke vs Cornell, 7 win outcomes each = 14 conditions):
```
Constraints:
1. sum(z_duke[0..6]) = 1  (Duke gets exactly one outcome)
2. sum(z_cornell[0..6]) = 1  (Cornell gets exactly one outcome)
3. z_duke[5] + z_duke[6] + z_cornell[5] + z_cornell[6] ≤ 1
   (Both can't win 5+ games since they'd meet in semifinals)
```

#### Why Integer Programming?

- **Without IP**: Must check 2^14 = 16,384 combinations
- **With IP**: 3 linear constraints replace 16,384 checks
- **Scalability**: For 63 games, IP handles 9.2 quintillion combinations efficiently

#### Arbitrage Condition

```
min cost = min(p · z) for all z ∈ Z

If min cost < 1.0:
    Arbitrage exists!
    Expected profit = 1.0 - min cost
```

#### Integer Program Formulation

```python
Variables:
    z[i] ∈ {0, 1}  # Binary variable for each outcome

Constraints:
    sum(z_event_a) = 1      # Exactly one outcome per event
    sum(z_event_b) = 1
    A^T × z ≥ b             # Logical dependency constraints

Objective:
    minimize sum(price[i] × z[i])
```

**Constraint Type Examples:**

1. **Implication:** `z_a[i] => z_b[j]` becomes `z_a[i] <= z_b[j]`
2. **Mutual Exclusion:** `z_a[i] ∧ z_b[j] = FALSE` becomes `z_a[i] + z_b[j] <= 1`
3. **Conjunction:** `z_a[i] ∧ z_b[j]` requires both true

#### Detection Algorithm

```python
def detect_dependency_arbitrage(market_a, market_b):
    # 1. Use LLM to identify logical constraints
    constraints = llm_extract_constraints(market_a, market_b)

    # 2. Build integer program
    #    Variables: z[i] for each condition (binary)
    #    Constraints: logical dependencies
    #    Objective: minimize sum(prices * z)

    # 3. Solve IP
    min_cost = solve_ip(constraints, prices)

    # 4. Check for arbitrage
    if min_cost < 1.0:  # Guaranteed profit
        return True, (1.0 - min_cost)  # arbitrage exists, profit amount
    else:
        return False, 0
```

#### Key Insight

Research using **DeepSeek-R1-Distill-Qwen-32B** to extract logical constraints from market descriptions achieved 81.45% accuracy. Combined with Gurobi IP solver for validation and quantification, this approach detected $40M+ in arbitrage opportunities on Polymarket.

**Our Implementation**: We use multi-provider LLM consensus (Claude, OpenAI, Grok, Gemini) with two-round iterative reasoning to improve constraint extraction accuracy beyond single-model approaches.

#### Computational Complexity

- Without constraints: O(2^n) - exponential in number of conditions
- With IP: O(n^3) - polynomial time with modern solvers
- Real-world: Duke vs Cornell solved in <100ms for 16,384 combinations

---

### Algorithm 2: AI-Based Dependency Detection

**Purpose:** Use multi-provider LLM consensus to identify logical dependencies between events.

#### Two-Round Iterative Reasoning

**Round 1: Independent Analysis**
Each LLM provider analyzes the event pair independently:

```json
{
    "dependency_score": 0.85,
    "is_dependent": true,
    "dependency_type": "implication",
    "constraints": [
        {
            "constraint_type": "implication",
            "description": "If B occurs, A must occur",
            "confidence": 0.9
        }
    ],
    "reasoning": "Event B is a stronger condition that implies A..."
}
```

**Round 2: Peer Review**
Providers see anonymized peer responses and revise:

```
Your Analysis: dependency_score = 0.85
Analyst A: dependency_score = 0.75 (identified different constraint)
Analyst B: dependency_score = 0.90 (agrees with your reasoning)
Analyst C: dependency_score = 0.80 (mutual exclusion not implication)

Revised Analysis: dependency_score = 0.82
```

#### Consensus Calculation

```python
def calculate_consensus(round2_responses):
    # Average scores from Round 2
    avg_score = mean([r.dependency_score for r in round2_responses])

    # Majority vote on dependency type
    consensus_type = mode([r.dependency_type for r in round2_responses])

    # Aggregate unique constraints
    all_constraints = deduplicate([
        c for r in round2_responses for c in r.constraints
    ])

    # Calculate convergence
    convergence = mean([
        abs(r2.score - r1.score)
        for r1, r2 in zip(round1, round2)
    ])

    return ConsensusResult(
        dependency_score=avg_score,
        dependency_type=consensus_type,
        constraints=all_constraints,
        convergence_metrics={"avg_shift": convergence}
    )
```

#### Accuracy Considerations

- **81.45% Base Accuracy:** DeepSeek-R1-Distill-Qwen-32B benchmark
- **Improved with Consensus:** Multi-provider voting reduces errors
- **Human Verification Required:** All detected dependencies need review before trading

---

## System Architecture

### Component Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     USER INTERFACE (CLI)                     │
├─────────────────────────────────────────────────────────────┤
│  get-events  │  detect-dependencies  │  check-arbitrage    │
│  list-deps   │  verify-dependency    │  review-arbitrage   │
└──────────────┬──────────────────────┬───────────────────────┘
               │                      │
               ▼                      ▼
┌──────────────────────┐    ┌────────────────────────┐
│   Kalshi API Client  │    │   LLM Manager          │
│   - Get Events       │    │   - Claude             │
│   - Get Markets      │    │   - OpenAI             │
│   - Get Orderbook    │    │   - Grok               │
│   - Rate Limiting    │    │   - Gemini             │
└──────────┬───────────┘    └────────┬───────────────┘
           │                         │
           ▼                         ▼
┌──────────────────────┐    ┌────────────────────────┐
│  Event Repository    │    │  Dependency Detector   │
│  - Store Events      │    │  - Build Context       │
│  - Query by Category │    │  - Run Consensus       │
│  - Filter by Status  │    │  - Extract Constraints │
└──────────┬───────────┘    └────────┬───────────────┘
           │                         │
           ▼                         ▼
┌──────────────────────┐    ┌────────────────────────┐
│ Dependency Repo      │    │  IP Solver (PuLP)      │
│ - Store Dependencies │    │  - Build IP Model      │
│ - Track Verification │    │  - Solve Constraints   │
│ - Query Unverified   │    │  - Detect Arbitrage    │
└──────────┬───────────┘    └────────┬───────────────┘
           │                         │
           ▼                         ▼
┌──────────────────────────────────────────────────┐
│           SQLite Database (data/openbet.db)       │
│  - events                                         │
│  - event_dependencies                             │
│  - arbitrage_opportunities                        │
└───────────────────────────────────────────────────┘
```

### Data Flow

1. **Event Discovery:** Kalshi API → Events Table
2. **Dependency Detection:** Events → LLM Consensus → Dependencies Table
3. **Market Fetching:** Kalshi API → Current Prices
4. **Arbitrage Detection:** Dependencies + Prices → IP Solver → Opportunities Table
5. **Human Review:** CLI → Verify/Reject → Update Status
6. **Execution:** Approved Opportunities → Trading System

---

## Workflow

### Phase 1: Event Collection

**Objective:** Fetch and store all Kalshi events for analysis.

```bash
# Fetch all open events from Kalshi
openbet get-events --save --status=open
```

**What Happens:**
1. API calls to `GET /events` with 0.5s rate limiting
2. Pagination through all results (200 per page)
3. UPSERT into `events` table (idempotent)
4. Returns total count of stored events

**Database Schema:**
```sql
CREATE TABLE events (
    event_ticker TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    category TEXT,
    series_ticker TEXT,
    status TEXT,
    -- ... metadata fields
)
```

**Conservative Rate Limiting:**
- 0.5s delay between API calls
- Respects Kalshi's rate limits
- Prevents API bans

---

### Phase 2: Dependency Detection

**Objective:** Identify logical relationships between events using AI consensus.

```bash
# Analyze all event pairs within same category
openbet detect-dependencies --limit=100

# Analyze specific category
openbet detect-dependencies --category=Politics --limit=50

# Analyze all pairs (comprehensive but slow)
openbet detect-dependencies --all-pairs --limit=200
```

**What Happens:**

1. **Load Events from Database**
   ```python
   events = event_repo.get_all(category=category, status="open")
   ```

2. **Generate Event Pairs**
   ```python
   # By default: same-category pairs only
   pairs = []
   for cat, events in group_by_category(events):
       for i, event_a in enumerate(events):
           for event_b in events[i+1:]:
               pairs.append((event_a, event_b))
   ```

3. **For Each Pair:**

   a. **Check if already analyzed** (skip if exists)

   b. **Build Dependency Context**
   ```python
   context = DependencyContext(
       event_a_ticker=event_a['event_ticker'],
       event_a_title=event_a['title'],
       event_b_ticker=event_b['event_ticker'],
       event_b_title=event_b['title'],
       same_series=(event_a['series'] == event_b['series'])
   )
   ```

   c. **Round 1: Independent LLM Analysis**
   ```python
   tasks = {
       provider: analyze(provider, prompt_round1)
       for provider in ['claude', 'openai', 'grok', 'gemini']
   }
   round1_responses = await asyncio.gather(*tasks)
   ```

   d. **Round 2: Iterative Reasoning with Peer Feedback**
   ```python
   for provider, own_response in round1_responses:
       peers = [r for p, r in round1_responses if p != provider]
       prompt_round2 = build_iterative_prompt(context, peers, own_response)
       round2_responses[provider] = await analyze(provider, prompt_round2)
   ```

   e. **Calculate Consensus**
   ```python
   consensus = calculate_consensus(round2_responses)
   # Returns: dependency_score, is_dependent, constraints
   ```

   f. **Save to Database**
   ```python
   dep_repo.create(
       event_a_ticker=event_a['event_ticker'],
       event_b_ticker=event_b['event_ticker'],
       dependency_score=consensus.dependency_score,
       constraints=consensus.constraints,
       llm_responses=consensus.provider_responses,
       round_1_responses=round1_responses,
       round_2_responses=round2_responses
   )
   ```

4. **Report Results**
   ```
   ✓ Dependency detected: PRES-PA-TRUMP × PRES-PA-GOP-MARGIN (score: 0.82)
   ✓ Dependency detected: NBA-FINALS-2026 × NBA-WEST-CHAMP (score: 0.91)

   Analysis complete!
   Dependencies detected: 12/100
   ```

**Database Schema:**
```sql
CREATE TABLE event_dependencies (
    id INTEGER PRIMARY KEY,
    event_a_ticker TEXT NOT NULL,
    event_b_ticker TEXT NOT NULL,
    dependency_type TEXT NOT NULL,  -- 'implication', 'mutual_exclusion', etc.
    dependency_score REAL NOT NULL,
    constraints_json TEXT NOT NULL,
    llm_responses_json TEXT NOT NULL,
    consensus_method TEXT NOT NULL,
    round_1_responses TEXT,
    round_2_responses TEXT,
    convergence_metrics TEXT,
    human_verified BOOLEAN DEFAULT FALSE,
    -- ... timestamps
)
```

---

### Phase 3: Human Verification

**Objective:** Review AI-detected dependencies (81.45% accuracy requires human oversight).

```bash
# List all unverified dependencies
openbet list-dependencies --unverified-only

# Review specific dependency interactively
openbet verify-dependency 5

# Approve with notes
openbet verify-dependency 5 --approve --notes="Clear implication relationship"

# Reject with reason
openbet verify-dependency 5 --reject --notes="Events are actually independent"
```

**What Happens:**

1. **Display Dependency Details**
   ```
   Dependency #5

   Event A: Will Trump win Pennsylvania?
   Event B: Will Republicans win PA by 5+ points?

   Dependency Score: 0.82
   Type: implication

   Detected Constraints:
     1. [implication] If B occurs, A must occur (confidence: 0.90)
     2. [conjunction] Both cannot be false together (confidence: 0.75)

   Provider Consensus:
     • claude: implication (score: 0.85)
     • openai: implication (score: 0.78)
     • grok: implication (score: 0.82)
     • gemini: causal (score: 0.83)
   ```

2. **Human Decision**
   - **Approve:** Sets `human_verified = TRUE`, enables arbitrage detection
   - **Reject:** Sets `human_verified = FALSE`, excludes from arbitrage checks
   - **Notes:** Stored for future reference and model improvement

3. **Update Database**
   ```python
   dep_repo.mark_verified(
       dependency_id=5,
       verified=True,
       notes="Clear implication: GOP +5 margin implies Trump win"
   )
   ```

**Why This Matters:**
- LLM accuracy is 81.45% (1 in 5 could be wrong)
- False positives could lead to bad trades
- Human verification creates a safety layer
- Notes help improve future prompts

---

### Phase 4: Arbitrage Detection

**Objective:** Use Integer Programming to find guaranteed profit opportunities.

```bash
# Check all verified dependencies
openbet check-arbitrage --all

# Check specific dependency
openbet check-arbitrage --dependency-id=5
```

**What Happens:**

1. **Load Verified Dependencies**
   ```python
   deps = [d for d in dep_repo.get_all() if d['human_verified']]
   ```

2. **For Each Dependency:**

   a. **Fetch Markets for Both Events**
   ```python
   markets_a = kalshi_client.get_markets(series_ticker=event_a_ticker)
   markets_b = kalshi_client.get_markets(series_ticker=event_b_ticker)
   ```

   b. **Get Current Prices**
   ```python
   current_prices = {}
   for market in markets_a + markets_b:
       orderbook = kalshi_client.get_orderbook(market.ticker)
       current_prices[f"{market.ticker}_yes"] = orderbook.yes_mid_price
       current_prices[f"{market.ticker}_no"] = orderbook.no_mid_price
   ```

   c. **Parse Constraints from Dependency**
   ```python
   constraints = [Constraint(**c) for c in dep['constraints_json']]
   ```

   d. **Build Integer Program**
   ```python
   from pulp import LpProblem, LpVariable, LpMinimize, lpSum

   prob = LpProblem("ArbitrageDetection", LpMinimize)

   # Binary variables for each outcome
   z_a = [LpVariable(f"z_a_{i}", cat='Binary') for i in range(len(markets_a))]
   z_b = [LpVariable(f"z_b_{i}", cat='Binary') for i in range(len(markets_b))]

   # Exactly one outcome per event
   prob += lpSum(z_a) == 1
   prob += lpSum(z_b) == 1

   # Apply logical constraints
   for constraint in constraints:
       if constraint.type == "implication":
           prob += z_a[i] <= z_b[j]  # A implies B
       # ... more constraint types

   # Minimize cost
   costs = []
   for i, market in enumerate(markets_a):
       costs.append(current_prices[f"{market.ticker}_yes"] * z_a[i])
   for i, market in enumerate(markets_b):
       costs.append(current_prices[f"{market.ticker}_yes"] * z_b[i])

   prob += lpSum(costs)
   ```

   e. **Solve IP**
   ```python
   prob.solve()
   min_cost = value(prob.objective)
   ```

   f. **Check for Arbitrage**
   ```python
   if min_cost < 1.0:
       profit = 1.0 - min_cost

       # Extract optimal portfolio
       optimal_portfolio = {
           var.name: var.value()
           for var in prob.variables()
           if var.value() == 1.0
       }

       # Save opportunity
       arb_repo.create(
           dependency_id=dep['id'],
           event_a_ticker=event_a_ticker,
           event_b_ticker=event_b_ticker,
           min_cost=min_cost,
           expected_profit=profit,
           optimal_portfolio=optimal_portfolio,
           market_ids=[m.ticker for m in markets_a + markets_b],
           current_prices=current_prices,
           constraints=dep['constraints_json']
       )
   ```

3. **Report Results**
   ```
   Analyzing: PRES-PA-TRUMP × PRES-PA-GOP-MARGIN
   ✓ ARBITRAGE DETECTED!
     Min cost: $0.9523
     Expected profit: $0.0477

   Check complete!
   Arbitrage opportunities: 3

   Review with: openbet list-arbitrage
   ```

**Database Schema:**
```sql
CREATE TABLE arbitrage_opportunities (
    id INTEGER PRIMARY KEY,
    dependency_id INTEGER NOT NULL,
    event_a_ticker TEXT NOT NULL,
    event_b_ticker TEXT NOT NULL,
    min_cost REAL NOT NULL,
    expected_profit REAL NOT NULL,
    optimal_portfolio_json TEXT NOT NULL,
    market_ids_json TEXT NOT NULL,
    current_prices_json TEXT NOT NULL,
    constraints_json TEXT NOT NULL,
    status TEXT DEFAULT 'detected',  -- 'detected', 'verified', 'rejected', 'executed'
    human_verified BOOLEAN DEFAULT FALSE,
    -- ... timestamps
)
```

---

### Phase 5: Opportunity Review & Execution

**Objective:** Review detected arbitrage before trading.

```bash
# List all opportunities
openbet list-arbitrage --status=detected

# Review specific opportunity
openbet review-arbitrage 12

# Approve for trading
openbet review-arbitrage 12 --approve --notes="Verified prices and liquidity"

# Reject opportunity
openbet review-arbitrage 12 --reject --notes="Insufficient liquidity"
```

**What Happens:**

1. **Display Opportunity Details**
   ```
   Arbitrage Opportunity #12

   Event A: Will Trump win Pennsylvania?
   Event B: Will Republicans win PA by 5+ points?

   Expected Profit: $0.0477
   Minimum Cost: $0.9523
   ROI: 5.01%

   Optimal Portfolio:
     • z_a_0: 1.0 (Trump YES)
     • z_b_1: 1.0 (GOP +5 NO)

   Current Market Prices:
     • PRES-PA-TRUMP_yes: $0.4800
     • PRES-PA-TRUMP_no: $0.5200
     • PRES-PA-GOP-MARGIN_yes: $0.3200
     • PRES-PA-GOP-MARGIN_no: $0.6800
   ```

2. **Human Decision**
   - **Approve:** Sets status='verified', ready for execution
   - **Reject:** Sets status='rejected', excluded from trading
   - **Skip:** Leave status='detected', review later

3. **Execution (Manual or Automated)**
   ```python
   # After approval, execute trades
   for position in optimal_portfolio:
       kalshi_client.place_order(
           ticker=market_ticker,
           side='yes' if 'yes' in position else 'no',
           action='buy',
           count=quantity,
           price=current_price
       )
   ```

---

## Implementation Details

### Technology Stack

**Language:** Python 3.10+

**Key Dependencies:**
- `pulp>=2.7.0` - Integer Programming solver (open-source)
- `pydantic>=2.0.0` - Data validation and models
- `anthropic`, `openai`, `google-genai` - LLM providers
- `requests>=2.31.0`, `httpx>=0.26.0` - HTTP clients
- `cryptography>=41.0.0` - Kalshi RSA-PSS authentication
- `rich>=13.0.0` - CLI display and formatting
- `aiosqlite>=0.19.0` - Async SQLite support

**Database:** SQLite (single-file, zero-config)

**API Integration:** Kalshi API v2

---

### Rate Limiting Strategy

**Conservative Approach (Prevents API Bans):**

```python
class KalshiClient:
    def __init__(self):
        self._request_times = deque(maxlen=100)
        self._min_request_interval = 0.5  # 500ms between requests

    def _make_request(self, method, endpoint, ...):
        # Wait if last request was too recent
        if self._request_times:
            time_since_last = time.time() - self._request_times[-1]
            if time_since_last < self._min_request_interval:
                time.sleep(self._min_request_interval - time_since_last)

        self._request_times.append(time.time())

        # Make request with retry logic
        return self.session.request(...)
```

**Rate Limits:**
- **get_events():** 0.5s delay (120 requests/minute)
- **get_event():** 0.3s delay (200 requests/minute)
- **get_markets():** 0.5s delay
- **get_orderbook():** 0.5s delay

**Retry Strategy:**
- Total retries: 3
- Backoff factor: 1 (exponential: 1s, 2s, 4s)
- Status codes: 429 (rate limit), 500, 502, 503, 504

---

### Error Handling

**Levels of Error Handling:**

1. **API Level** (kalshi/client.py)
   ```python
   try:
       response = self.session.request(...)
   except requests.HTTPError as e:
       if e.response.status_code == 429:
           raise KalshiRateLimitError("Rate limit exceeded")
       elif e.response.status_code == 404:
           raise KalshiMarketNotFoundError(f"Resource not found: {endpoint}")
       else:
           raise KalshiAPIError(f"API request failed: {str(e)}")
   ```

2. **LLM Provider Level** (arbitrage/dependency_detector.py)
   ```python
   async def _analyze_with_provider(self, provider_name, prompt):
       try:
           response = await provider.analyze_custom_prompt(prompt)
           return DependencyAnalysisResponse(**json.loads(response))
       except Exception as e:
           logger.error(f"Error with {provider_name}: {e}")
           return None  # Graceful degradation
   ```

3. **Workflow Level** (CLI commands)
   ```python
   try:
       result = await detector.analyze_dependency(event_a, event_b)
       dep_repo.create(...)
   except ValueError as e:
       console.print(f"[red]Error:[/red] {e}")
       continue  # Skip this pair, continue with others
   except Exception as e:
       console.print(f"[red]Unexpected error:[/red] {e}")
       import traceback
       traceback.print_exc()
   ```

**Graceful Degradation:**
- If one LLM provider fails, others continue
- If one event pair fails, others continue
- If IP solver times out, opportunity is skipped (not crashed)

---

### Performance Optimization

**Database Indexing:**
```sql
-- Query dependencies by event
CREATE INDEX idx_event_deps_a ON event_dependencies(event_a_ticker);
CREATE INDEX idx_event_deps_b ON event_dependencies(event_b_ticker);

-- Filter unverified dependencies
CREATE INDEX idx_event_deps_verified ON event_dependencies(human_verified);

-- Sort arbitrage by profit
CREATE INDEX idx_arbitrage_profit ON arbitrage_opportunities(expected_profit DESC);
```

**Async LLM Calls:**
```python
# Parallel analysis from all providers (saves 4x time)
tasks = {
    name: analyze_with_provider(name, prompt)
    for name in ['claude', 'openai', 'grok', 'gemini']
}
results = await asyncio.gather(*tasks.values())
```

**Caching:**
- Events fetched once per session
- Dependencies checked before re-analysis
- Market prices cached for batch arbitrage checks

---

## API Reference

### CLI Commands

#### Event Management

```bash
# Fetch and save all open events
openbet get-events --save --status=open

# Filter by category
openbet get-events --save --category=Politics

# Filter by series
openbet get-events --save --series=PRES-2024
```

#### Dependency Detection

```bash
# Analyze same-category pairs (default)
openbet detect-dependencies --limit=100

# Analyze all pairs (comprehensive)
openbet detect-dependencies --all-pairs --limit=200

# Specific category
openbet detect-dependencies --category=Politics

# List detected dependencies
openbet list-dependencies

# List unverified only
openbet list-dependencies --unverified-only
```

#### Human Verification

```bash
# Interactive verification
openbet verify-dependency <ID>

# Direct approval
openbet verify-dependency <ID> --approve --notes="Clear relationship"

# Direct rejection
openbet verify-dependency <ID> --reject --notes="False positive"
```

#### Arbitrage Detection

```bash
# Check all verified dependencies
openbet check-arbitrage --all

# Check specific dependency
openbet check-arbitrage --dependency-id=5

# List opportunities
openbet list-arbitrage

# Filter by status
openbet list-arbitrage --status=detected

# Filter by minimum profit
openbet list-arbitrage --min-profit=0.05
```

#### Opportunity Review

```bash
# Interactive review
openbet review-arbitrage <ID>

# Direct approval
openbet review-arbitrage <ID> --approve --notes="Verified liquidity"

# Direct rejection
openbet review-arbitrage <ID> --reject --notes="Insufficient liquidity"
```

### Python API

#### Event Repository

```python
from openbet.database.repositories import EventRepository

repo = EventRepository()

# Create or update event
repo.create_or_update(
    event_ticker="PRES-PA-2024",
    title="Pennsylvania Presidential Election",
    category="Politics",
    status="open"
)

# Get event
event = repo.get("PRES-PA-2024")

# Get all events with filters
events = repo.get_all(category="Politics", status="open")

# Check existence
exists = repo.exists("PRES-PA-2024")
```

#### Dependency Detector

```python
from openbet.arbitrage.dependency_detector import DependencyDetector

detector = DependencyDetector()

# Analyze dependency
result = await detector.analyze_dependency(event_a, event_b)

# Access results
if result.is_dependent:
    print(f"Dependency score: {result.dependency_score}")
    print(f"Type: {result.dependency_type}")
    for constraint in result.constraints:
        print(f"  {constraint.description}")
```

#### IP Solver

```python
from openbet.arbitrage.ip_solver import IPArbitrageSolver

solver = IPArbitrageSolver()

# Detect arbitrage
result = solver.detect_arbitrage(
    event_a_markets=markets_a,
    event_b_markets=markets_b,
    constraints=constraints,
    current_prices=current_prices
)

if result:
    print(f"Min cost: ${result['min_cost']:.4f}")
    print(f"Expected profit: ${result['expected_profit']:.4f}")
    print(f"Optimal portfolio: {result['optimal_portfolio']}")
```

---

## Usage Examples

### Example 1: Complete Workflow

```bash
# Step 1: Fetch all open events
openbet get-events --save --status=open
# Output: ✓ Saved 156 events to database

# Step 2: Detect dependencies in Politics category
openbet detect-dependencies --category=Politics --limit=50
# Output: Dependencies detected: 5/50

# Step 3: Review unverified dependencies
openbet list-dependencies --unverified-only
#   ID  Event A              Event B                  Score  Type
#   1   PRES-PA-TRUMP       PRES-PA-GOP-MARGIN        0.82  implication
#   2   PRES-FL-TRUMP       PRES-FL-GOP-MARGIN        0.79  implication
#   ...

# Step 4: Verify dependencies
openbet verify-dependency 1 --approve --notes="Clear implication"
openbet verify-dependency 2 --approve --notes="Same pattern as #1"

# Step 5: Check for arbitrage
openbet check-arbitrage --all
# Output: ✓ ARBITRAGE DETECTED!
#         Min cost: $0.9523
#         Expected profit: $0.0477

# Step 6: Review opportunities
openbet list-arbitrage --status=detected
#   ID  Events                          Profit    Min Cost  Status
#   1   PRES-PA-TRUMP × PRES-PA-GOP...  $0.0477  $0.9523   detected

# Step 7: Approve for trading
openbet review-arbitrage 1 --approve --notes="Verified prices and liquidity"

# Step 8: View approved opportunities
openbet list-arbitrage --status=verified
```

### Example 2: Programmatic Usage

```python
import asyncio
from openbet.kalshi.client import KalshiClient
from openbet.database.repositories import EventRepository, EventDependencyRepository
from openbet.arbitrage.dependency_detector import DependencyDetector

async def find_arbitrage():
    # Initialize components
    client = KalshiClient()
    event_repo = EventRepository()
    dep_repo = EventDependencyRepository()
    detector = DependencyDetector()

    # Fetch all open events with pagination
    all_events = []
    cursor = None

    while True:
        response = client.get_events_with_cursor(status="open", limit=200, cursor=cursor)
        all_events.extend(response.events)
        if not response.has_more_pages:
            break
        cursor = response.cursor

    for event in all_events:
        event_repo.create_or_update(
            event_ticker=event.event_ticker,
            title=event.title,
            category=event.category,
            status=event.status,
            metadata=event.model_dump()
        )

    # Detect dependencies
    politics_events = event_repo.get_all(category="Politics")

    for i, event_a in enumerate(politics_events):
        for event_b in politics_events[i+1:]:
            # Check if already analyzed
            existing = dep_repo.get_by_event_pair(
                event_a['event_ticker'],
                event_b['event_ticker']
            )
            if existing:
                continue

            # Analyze dependency
            result = await detector.analyze_dependency(event_a, event_b)

            # Save if dependent
            if result.is_dependent:
                dep_repo.create(
                    event_a_ticker=event_a['event_ticker'],
                    event_b_ticker=event_b['event_ticker'],
                    dependency_type=result.dependency_type,
                    dependency_score=result.dependency_score,
                    constraints={'constraints': [c.model_dump() for c in result.constraints]},
                    llm_responses=result.provider_responses,
                    consensus_method=result.consensus_method
                )

    print("Dependency detection complete!")

# Run
asyncio.run(find_arbitrage())
```

---

## Performance & Optimization

### Expected Performance

**Event Fetching:**
- 200 events per API call
- 0.5s delay between calls
- ~1000 events in 150 seconds

**Dependency Detection:**
- 100 event pairs = 800 LLM calls (4 providers × 2 rounds × 100 pairs)
- Parallel execution: ~30-60 seconds per pair
- Total: ~50-100 minutes for 100 pairs

**Arbitrage Detection:**
- IP solve time: < 1 second for simple dependencies
- IP solve time: 10-30 seconds for complex multi-market dependencies
- ~10 dependencies checked in 1-5 minutes

### Optimization Strategies

1. **Parallel LLM Calls**
   ```python
   # Don't do this (sequential, 4x slower):
   for provider in providers:
       result = await analyze(provider, prompt)

   # Do this (parallel, 4x faster):
   tasks = [analyze(p, prompt) for p in providers]
   results = await asyncio.gather(*tasks)
   ```

2. **Smart Pairing**
   ```python
   # Don't analyze all pairs (O(n²)):
   for event_a in events:
       for event_b in events:
           # 1000 events = 1,000,000 pairs!

   # Do analyze same-category pairs only:
   by_category = group_by_category(events)
   for cat, cat_events in by_category.items():
       for i, event_a in enumerate(cat_events):
           for event_b in cat_events[i+1:]:
               # 1000 events in 10 categories = ~50,000 pairs
   ```

3. **Caching**
   ```python
   # Check before re-analyzing
   existing = dep_repo.get_by_event_pair(event_a, event_b)
   if existing:
       continue  # Skip already analyzed pairs
   ```

4. **Batch Arbitrage Checks**
   ```python
   # Don't fetch markets individually:
   for dep in dependencies:
       markets_a = client.get_markets(dep.event_a_ticker)
       markets_b = client.get_markets(dep.event_b_ticker)

   # Do batch fetch:
   all_event_tickers = unique([d.event_a_ticker, d.event_b_ticker]
                              for d in dependencies)
   markets_cache = {
       ticker: client.get_markets(ticker)
       for ticker in all_event_tickers
   }
   ```

### Scalability Limits

**Current Bottlenecks:**
1. **LLM API Latency:** 2-5 seconds per provider per call
2. **Kalshi Rate Limits:** ~2 requests/second
3. **IP Solver:** 10-30 seconds for complex dependencies

**Scaling Solutions:**
1. Use Gurobi (commercial solver) instead of PuLP for 10-100x faster IP solving
2. Implement async batching for Kalshi API calls
3. Add distributed task queue (Celery) for parallel LLM analysis
4. Cache event/market data with TTL to reduce API calls

---

## Appendix

### Glossary

**Arbitrage:** Guaranteed profit from simultaneous transactions in different markets

**Dependency:** Logical relationship between events (implication, mutual exclusion, etc.)

**Event:** High-level Kalshi grouping (e.g., "Pennsylvania Election 2024")

**Market:** Specific tradable contract (e.g., "PRES-PA-TRUMP-YES")

**Marginal Polytope:** Set of all arbitrage-free price vectors

**Integer Programming (IP):** Mathematical optimization with binary decision variables

**UPSERT:** Database operation that inserts or updates if exists

**VWAP:** Volume-Weighted Average Price (for execution analysis)

### References

1. **Research Paper:** "Arbitraging Prediction Markets" (source of algorithms)
2. **Kalshi API Docs:** https://docs.kalshi.com/
3. **PuLP Documentation:** https://coin-or.github.io/pulp/
4. **Implementation Plan:** `ARBITRAGE_ALGORITHMS_PLAN.md`

### Troubleshooting

**Problem:** "ModuleNotFoundError: No module named 'pydantic_settings'"
- **Solution:** Run `pip install -r requirements.txt`

**Problem:** "KalshiAuthenticationError: Failed to load RSA private key"
- **Solution:** Check `.env` file has correct `KALSHI_API_SECRET` in PEM format

**Problem:** "Rate limit exceeded"
- **Solution:** System already has 0.5s delays; check if multiple instances running

**Problem:** "No dependencies detected"
- **Solution:** Try broader criteria with `--all-pairs` or different category

**Problem:** "IP solver timeout"
- **Solution:** Constraint set too complex; consider upgrading to Gurobi

---

**End of Documentation**

For questions or contributions, please refer to the main project repository.
