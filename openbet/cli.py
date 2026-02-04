"""Command-line interface for Openbet."""

import json
import sys
from typing import Optional

import click
from rich.console import Console
from rich.table import Table

from openbet.database.repositories import (
    AnalysisRepository,
    MarketRepository,
    PositionRepository,
)
from openbet.kalshi.client import KalshiClient
from openbet.kalshi.exceptions import KalshiError
from openbet.kalshi.models import Market
from openbet.trading.models import RiskConfig

console = Console()


@click.group()
@click.option("--verbose", is_flag=True, help="Enable verbose logging")
def cli(verbose: bool):
    """Openbet - Automated betting analysis and execution on Kalshi markets."""
    if verbose:
        console.print("[dim]Verbose mode enabled[/dim]")


@cli.command("check-market")
@click.argument("market_id")
def check_market(market_id: str):
    """Check market details by market_id from Kalshi API.

    Args:
        market_id: Kalshi market ticker to check
    """
    try:
        console.print(f"[bold]Fetching market details for {market_id}...[/bold]")

        # Initialize Kalshi client
        client = KalshiClient()

        # Fetch market details
        market = client.get_market(market_id)

        # Fetch orderbook for current prices
        orderbook = client.get_orderbook(market_id)

        # Display market details
        console.print("\n[bold cyan]Market Details[/bold cyan]")
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Field", style="cyan")
        table.add_column("Value", style="white")

        table.add_row("Ticker", market.ticker)
        table.add_row("Title", market.title)

        # Add subtitle if available
        if market.subtitle:
            table.add_row("Subtitle", market.subtitle)

        # Add YES/NO subtitles if available
        if market.yes_sub_title:
            table.add_row("YES means", market.yes_sub_title)
        if market.no_sub_title:
            table.add_row("NO means", market.no_sub_title)

        table.add_row("Status", market.status or "N/A")
        table.add_row("Category", market.category or "N/A")

        # Add implied probability (chance) from market price
        if orderbook.yes_mid_price:
            implied_prob = orderbook.yes_mid_price * 100  # Convert to percentage
            table.add_row("Implied Chance (YES)", f"{implied_prob:.1f}%")

        # Add last price if available
        if market.last_price is not None:
            table.add_row("Last Price", f"${market.last_price:.2f}")

        table.add_row("Close Time", str(market.close_time) if market.close_time else "N/A")

        # Add expiration time if different from close time
        if market.expiration_time and market.expiration_time != market.close_time:
            table.add_row("Expiration Time", str(market.expiration_time))

        table.add_row("Volume (24h)", str(market.volume_24h) if market.volume_24h else "N/A")
        table.add_row("Open Interest", str(market.open_interest) if market.open_interest else "N/A")

        # Add liquidity if available
        if market.liquidity is not None:
            table.add_row("Liquidity", str(market.liquidity))

        # Add result if market is resolved
        if market.result:
            table.add_row("Result", market.result)

        # Add can_close_early flag
        if market.can_close_early is not None:
            table.add_row("Can Close Early", "Yes" if market.can_close_early else "No")

        console.print(table)

        # Display current prices
        console.print("\n[bold cyan]Current Prices[/bold cyan]")
        price_table = Table(show_header=True, header_style="bold magenta")
        price_table.add_column("Side", style="cyan")
        price_table.add_column("Best Bid", style="green")
        price_table.add_column("Best Ask", style="red")
        price_table.add_column("Mid Price", style="yellow")

        yes_bid = f"${orderbook.best_yes_bid:.2f}" if orderbook.best_yes_bid else "N/A"
        yes_ask = f"${orderbook.best_yes_ask:.2f}" if orderbook.best_yes_ask else "N/A"
        yes_mid = f"${orderbook.yes_mid_price:.2f}" if orderbook.yes_mid_price else "N/A"

        no_bid = f"${orderbook.best_no_bid:.2f}" if orderbook.best_no_bid else "N/A"
        no_ask = f"${orderbook.best_no_ask:.2f}" if orderbook.best_no_ask else "N/A"
        no_mid = f"${orderbook.no_mid_price:.2f}" if orderbook.no_mid_price else "N/A"

        price_table.add_row("YES", yes_bid, yes_ask, yes_mid)
        price_table.add_row("NO", no_bid, no_ask, no_mid)

        console.print(price_table)

        # Check if position exists in database
        market_repo = MarketRepository()
        position_repo = PositionRepository()

        if market_repo.exists(market_id):
            positions = position_repo.get_by_market(market_id)
            if positions:
                console.print("\n[bold cyan]Your Positions[/bold cyan]")
                pos_table = Table(show_header=True, header_style="bold magenta")
                pos_table.add_column("Option", style="cyan")
                pos_table.add_column("Side", style="yellow")
                pos_table.add_column("Quantity", style="white")
                pos_table.add_column("Avg Price", style="white")
                pos_table.add_column("Unrealized P&L", style="white")

                for pos in positions:
                    pnl = f"${pos['unrealized_pnl']:.2f}" if pos['unrealized_pnl'] else "N/A"
                    pos_table.add_row(
                        pos['option'],
                        pos['side'].upper(),
                        str(pos['quantity']),
                        f"${pos['avg_price']:.2f}",
                        pnl,
                    )

                console.print(pos_table)
            else:
                console.print("\n[dim]No positions found in database[/dim]")
        else:
            console.print("\n[dim]Market not tracked in database[/dim]")

        console.print(f"\n[green]✓[/green] Market details retrieved successfully")

    except KalshiError as e:
        console.print(f"[red]✗ Kalshi API error: {str(e)}[/red]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]✗ Error: {str(e)}[/red]")
        sys.exit(1)


@cli.command("add-market")
@click.argument("market_id")
def add_market(market_id: str):
    """Add market to database for tracking.

    Args:
        market_id: Kalshi market ticker to add
    """
    try:
        console.print(f"[bold]Adding market {market_id} to database...[/bold]")

        # Initialize clients and repositories
        client = KalshiClient()
        market_repo = MarketRepository()
        position_repo = PositionRepository()

        # Check if market already exists
        if market_repo.exists(market_id):
            console.print(f"[yellow]⚠[/yellow] Market {market_id} already exists in database")
            return

        # Fetch market details from Kalshi
        market = client.get_market(market_id)

        # Insert market into database
        market_repo.create(
            market_id=market.ticker,
            title=market.title,
            close_time=str(market.close_time) if market.close_time else None,
            status=market.status,
            category=market.category,
            min_tick_size=0.01,  # Default tick size
            max_tick_size=0.99,  # Default max tick size
            metadata={
                "subtitle": market.subtitle,
                "yes_sub_title": market.yes_sub_title,
                "no_sub_title": market.no_sub_title,
                "volume": market.volume,
                "open_interest": market.open_interest,
            },
        )

        console.print(f"[green]✓[/green] Market added to database")

        # Try to fetch and store current position if exists
        position = client.get_position(market_id)
        if position and position.position != 0:
            # Determine side based on position sign
            side = "yes" if position.position > 0 else "no"
            quantity = abs(position.position)
            avg_price = (
                position.total_cost / quantity if quantity > 0 else 0
            )

            position_repo.create_or_update(
                market_id=market_id,
                option=market_id,  # Using ticker as option for now
                side=side,
                quantity=quantity,
                avg_price=avg_price,
                metadata={"resting_orders": position.resting_order_count},
            )

            console.print(f"[green]✓[/green] Current position stored")

        # Display summary
        console.print("\n[bold cyan]Market Added Successfully[/bold cyan]")
        table = Table(show_header=False)
        table.add_column("Field", style="cyan")
        table.add_column("Value", style="white")

        table.add_row("Ticker", market.ticker)
        table.add_row("Title", market.title)
        table.add_row("Status", market.status or "N/A")
        table.add_row("Close Time", str(market.close_time) if market.close_time else "N/A")

        console.print(table)
        console.print("\n[green]✓[/green] Ready for analysis")

    except KalshiError as e:
        console.print(f"[red]✗ Kalshi API error: {str(e)}[/red]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]✗ Error: {str(e)}[/red]")
        sys.exit(1)


@cli.command("list-markets")
@click.option("--status", help="Filter by status (e.g., 'active', 'closed')")
def list_markets(status: Optional[str]):
    """List all markets tracked in the database.

    Args:
        status: Optional filter by market status
    """
    try:
        console.print("[bold]Fetching markets from database...[/bold]")

        market_repo = MarketRepository()
        markets = market_repo.get_all()

        # Filter by status if provided
        if status:
            markets = [m for m in markets if m.get('status') == status]

        if not markets:
            console.print("[yellow]No markets found in database[/yellow]")
            return

        console.print(f"\n[bold cyan]Found {len(markets)} market(s)[/bold cyan]\n")

        # Display markets in a table
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Ticker", style="cyan", width=30)
        table.add_column("Title", style="white", width=40)
        table.add_column("Status", style="green")
        table.add_column("Close Time", style="yellow", width=20)

        for market in markets:
            table.add_row(
                market['id'],
                market['title'][:37] + "..." if len(market['title']) > 40 else market['title'],
                market['status'] or "N/A",
                str(market['close_time'])[:19] if market['close_time'] else "N/A",
            )

        console.print(table)
        console.print(f"\n[green]✓[/green] Listed {len(markets)} market(s)")

    except Exception as e:
        console.print(f"[red]✗ Error: {str(e)}[/red]")
        sys.exit(1)


@cli.command("find-markets")
@click.argument("event_ticker")
@click.option("--add-all", is_flag=True, help="Add all found markets to database")
def find_markets(event_ticker: str, add_all: bool):
    """Find all markets for a given event/series ticker from Kalshi API.

    Args:
        event_ticker: Event/series ticker (e.g., KXFOXNEWSMENTION-26FEB04)
        add_all: If True, add all found markets to database
    """
    try:
        console.print(f"[bold]Searching for markets in series: {event_ticker}...[/bold]")

        # Initialize Kalshi client
        client = KalshiClient()

        # Convert to uppercase for API call
        event_ticker_upper = event_ticker.upper()

        # Query API for markets in this series
        params = {
            'event_ticker': event_ticker_upper,
            'limit': 50
        }
        data = client._make_request('GET', '/markets', params=params)
        markets = data.get('markets', [])

        if not markets:
            console.print(f"[yellow]No markets found for event ticker: {event_ticker}[/yellow]")
            return

        console.print(f"\n[bold cyan]Found {len(markets)} market(s) in series {event_ticker_upper}[/bold cyan]\n")

        # Display event title once at the top
        if markets:
            console.print(f"[dim]Event: {markets[0].get('title', 'N/A')}[/dim]\n")

        # Display markets in a table
        table = Table(show_header=True, header_style="bold magenta", show_lines=False)
        table.add_column("#", style="dim", width=2)
        table.add_column("Ticker", style="cyan", width=33)
        table.add_column("Option", style="white", width=18, no_wrap=False)
        table.add_column("Y-Bid", style="green", width=6)
        table.add_column("Y-Ask", style="yellow", width=6)
        table.add_column("N-Bid", style="green", width=6)
        table.add_column("N-Ask", style="yellow", width=6)
        table.add_column("Last", style="cyan", width=6)
        table.add_column("Vol", style="blue", width=7)
        table.add_column("OI", style="blue", width=7)

        for idx, market in enumerate(markets, 1):
            # Extract option name from yes_sub_title or ticker suffix
            option_name = market.get('yes_sub_title') or market.get('subtitle') or market['ticker'].split('-')[-1]

            # Get current prices if available
            yes_bid = "N/A"
            yes_ask = "N/A"
            no_bid = "N/A"
            no_ask = "N/A"
            try:
                orderbook_data = client._make_request('GET', f"/markets/{market['ticker']}/orderbook", params={'depth': 1})
                orderbook = orderbook_data.get('orderbook', {})

                yes_data = orderbook.get('yes', [])
                if yes_data and len(yes_data) > 0:
                    yes_ask = f"${yes_data[0][0] / 100:.2f}"

                no_data = orderbook.get('no', [])
                if no_data and len(no_data) > 0:
                    no_ask = f"${no_data[0][0] / 100:.2f}"
            except:
                pass

            # Get market data
            last_price = market.get('last_price')
            last_price_str = f"${last_price:.2f}" if last_price else "N/A"

            volume = market.get('volume', 0)
            volume_str = f"{volume:,}" if volume else "0"

            open_interest = market.get('open_interest', 0)
            oi_str = f"{open_interest:,}" if open_interest else "0"

            table.add_row(
                str(idx),
                market['ticker'],
                option_name,
                yes_bid,
                yes_ask,
                no_bid,
                no_ask,
                last_price_str,
                volume_str,
                oi_str,
            )

        console.print(table)

        # If add_all flag is set, add all markets to database
        if add_all:
            console.print(f"\n[bold]Adding {len(markets)} markets to database...[/bold]")
            market_repo = MarketRepository()
            added_count = 0
            skipped_count = 0

            for market in markets:
                if market_repo.exists(market['ticker']):
                    skipped_count += 1
                    continue

                try:
                    market_obj = Market(**market)
                    market_repo.create(
                        market_id=market_obj.ticker,
                        title=market_obj.title,
                        close_time=str(market_obj.close_time) if market_obj.close_time else None,
                        status=market_obj.status,
                        category=market_obj.category,
                        min_tick_size=0.01,
                        max_tick_size=0.99,
                        metadata={
                            "subtitle": market_obj.subtitle,
                            "yes_sub_title": market_obj.yes_sub_title,
                            "no_sub_title": market_obj.no_sub_title,
                            "volume": market_obj.volume,
                            "open_interest": market_obj.open_interest,
                        },
                    )
                    added_count += 1
                except Exception as e:
                    console.print(f"[yellow]⚠ Failed to add {market['ticker']}: {str(e)}[/yellow]")

            console.print(f"\n[green]✓[/green] Added {added_count} markets, skipped {skipped_count} (already in database)")

        console.print(f"\n[green]✓[/green] Search complete")

    except KalshiError as e:
        console.print(f"[red]✗ Kalshi API error: {str(e)}[/red]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]✗ Error: {str(e)}[/red]")
        import traceback
        traceback.print_exc()
        sys.exit(1)


@cli.command("screen-markets")
@click.option("--tracked", is_flag=True, help="Screen only tracked markets from database")
@click.option("--status", default="", help="Filter by market status on API (e.g., 'open', leave empty for all)")
@click.option("--min-liquidity", type=float, help="Minimum liquidity threshold")
@click.option("--min-volume", type=float, help="Minimum 24h volume threshold")
@click.option("--min-open-interest", type=int, help="Minimum open interest threshold")
@click.option("--sort-by", type=click.Choice(["quality", "liquidity", "volume", "open-interest", "close-time"]),
              default="quality", help="Sort order for results")
@click.option("--passed-only", is_flag=True, help="Show only markets that pass all filters")
@click.option("--limit", type=int, default=50, help="Maximum markets to screen (default: 50)")
@click.option("--event-ticker", help="Filter by event/series ticker")
def screen_markets(
    tracked: bool,
    status: str,
    min_liquidity: Optional[float],
    min_volume: Optional[float],
    min_open_interest: Optional[int],
    sort_by: str,
    passed_only: bool,
    limit: int,
    event_ticker: Optional[str],
):
    """Screen markets by liquidity, volume, and open interest thresholds.

    Pre-filter markets before running expensive LLM analysis to identify
    high-quality trading opportunities with sufficient liquidity.
    """
    try:
        # Load thresholds (CLI args or defaults from RiskConfig)
        risk_config = RiskConfig()
        thresholds = {
            'min_liquidity': min_liquidity if min_liquidity is not None else risk_config.min_liquidity,
            'min_volume_24h': min_volume if min_volume is not None else risk_config.min_volume_24h,
            'min_open_interest': min_open_interest if min_open_interest is not None else 100,
            'allowed_statuses': ["open", "active"]  # Accept both open and active markets
        }

        # Fetch markets
        markets = []
        if tracked:
            console.print("[yellow]⚠[/yellow] Note: Fetching live data for tracked markets (this may take a moment)\n")
            market_repo = MarketRepository()
            db_markets = market_repo.get_all()

            if not db_markets:
                console.print("[yellow]No tracked markets found in database[/yellow]")
                return

            client = KalshiClient()
            for db_market in db_markets:
                try:
                    market = client.get_market(db_market['id'])
                    markets.append(market)
                except Exception as e:
                    console.print(f"[yellow]⚠ Failed to fetch {db_market['id']}: {str(e)}[/yellow]")
        else:
            # Get from API
            client = KalshiClient()
            params = {'limit': limit}
            if status:  # Only add status filter if explicitly provided
                params['status'] = status
            if event_ticker:
                params['event_ticker'] = event_ticker.upper()

            data = client._make_request('GET', '/markets', params=params)
            markets_data = data.get('markets', [])
            markets = [Market(**m) for m in markets_data]

        if not markets:
            console.print("[yellow]No markets found matching criteria[/yellow]")
            return

        # Screen each market
        results = []
        for market in markets:
            passed = True
            failures = []

            liquidity = market.liquidity or 0
            volume_24h = market.volume_24h or 0
            open_interest = market.open_interest or 0

            # Check thresholds
            if liquidity < thresholds['min_liquidity']:
                passed = False
                failures.append(f"Low liquidity ({liquidity:.0f} < {thresholds['min_liquidity']:.0f})")

            if volume_24h < thresholds['min_volume_24h']:
                passed = False
                failures.append(f"Low volume ({volume_24h:.0f} < {thresholds['min_volume_24h']:.0f})")

            if open_interest < thresholds['min_open_interest']:
                passed = False
                failures.append(f"Low open interest ({open_interest} < {thresholds['min_open_interest']})")

            if market.status not in thresholds['allowed_statuses']:
                passed = False
                failures.append(f"Status: {market.status}")

            # Calculate quality score (for sorting)
            quality_score = 0.0
            if thresholds['min_liquidity'] > 0:
                quality_score += (liquidity / thresholds['min_liquidity']) * 0.4
            if thresholds['min_volume_24h'] > 0:
                quality_score += (volume_24h / thresholds['min_volume_24h']) * 0.3
            if thresholds['min_open_interest'] > 0:
                quality_score += (open_interest / thresholds['min_open_interest']) * 0.3

            results.append({
                'market': market,
                'passed': passed,
                'failures': failures,
                'quality_score': quality_score,
                'liquidity': liquidity,
                'volume_24h': volume_24h,
                'open_interest': open_interest,
            })

        # Filter if --passed-only
        if passed_only:
            results = [r for r in results if r['passed']]
            if not results:
                console.print("[yellow]No markets passed all filters. Try lowering thresholds.[/yellow]")
                return

        # Sort results
        from datetime import datetime
        sort_keys = {
            'quality': lambda r: r['quality_score'],
            'liquidity': lambda r: r['liquidity'],
            'volume': lambda r: r['volume_24h'],
            'open-interest': lambda r: r['open_interest'],
            'close-time': lambda r: r['market'].close_time or datetime.max,
        }
        results.sort(key=sort_keys[sort_by], reverse=True)

        # Display header
        console.print(f"\n[bold]Screening {len(results)} market(s)[/bold]")
        console.print(f"[dim]Thresholds: Liquidity ≥ {thresholds['min_liquidity']:.0f}, "
                      f"Volume ≥ {thresholds['min_volume_24h']:.0f}, "
                      f"Open Interest ≥ {thresholds['min_open_interest']}[/dim]\n")

        # Build Rich table
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Status", style="white", width=6)
        table.add_column("Ticker", style="cyan", width=30)
        table.add_column("Liquidity", style="blue", justify="right", width=10)
        table.add_column("Volume 24h", style="blue", justify="right", width=11)
        table.add_column("Open Int.", style="blue", justify="right", width=10)
        table.add_column("Quality", style="yellow", justify="right", width=8)
        table.add_column("Issues", style="red", width=40)

        passed_count = 0
        failed_count = 0

        for result in results:
            market = result['market']

            # Status indicator
            if result['passed']:
                status_icon = "[green]✓[/green]"
                passed_count += 1
            else:
                status_icon = "[red]✗[/red]"
                failed_count += 1

            # Color-code metrics based on pass/fail
            liquidity_str = f"{result['liquidity']:,.0f}"
            if result['liquidity'] < thresholds['min_liquidity']:
                liquidity_str = f"[red]{liquidity_str}[/red]"

            volume_str = f"{result['volume_24h']:,.0f}"
            if result['volume_24h'] < thresholds['min_volume_24h']:
                volume_str = f"[red]{volume_str}[/red]"

            oi_str = f"{result['open_interest']:,}"
            if result['open_interest'] < thresholds['min_open_interest']:
                oi_str = f"[red]{oi_str}[/red]"

            quality_str = f"{result['quality_score']:.2f}"

            # Issues summary
            issues_str = "; ".join(result['failures']) if result['failures'] else "—"
            if len(issues_str) > 40:
                issues_str = issues_str[:37] + "..."

            table.add_row(
                status_icon,
                market.ticker,
                liquidity_str,
                volume_str,
                oi_str,
                quality_str,
                issues_str,
            )

        console.print(table)

        # Summary
        console.print(f"\n[bold cyan]Summary[/bold cyan]")
        console.print(f"[green]✓[/green] Passed: {passed_count}/{len(results)}")
        console.print(f"[red]✗[/red] Failed: {failed_count}/{len(results)}")

        if passed_count > 0:
            console.print(f"\n[dim]Next: Run 'openbet analyze --market-id <TICKER>' for markets that passed[/dim]")

    except KalshiError as e:
        console.print(f"[red]✗ Kalshi API error: {str(e)}[/red]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]✗ Error: {str(e)}[/red]")
        import traceback
        traceback.print_exc()
        sys.exit(1)


@cli.command("analyze")
@click.option("--market-id", help="Specific market to analyze")
@click.option("--all", "analyze_all", is_flag=True, help="Analyze all markets in database")
@click.option("--option", help="Specific option to analyze within market")
@click.option("--force", is_flag=True, help="Force fresh analysis, bypass cache")
@click.option("--cache-hours", type=int, default=24, help="Cache validity in hours (default: 24)")
def analyze(
    market_id: Optional[str],
    analyze_all: bool,
    option: Optional[str],
    force: bool,
    cache_hours: int,
):
    """Run LLM analysis on market(s) and store results.

    Calls multiple LLM providers (Claude, OpenAI, Grok, Gemini) to analyze market options
    using iterative reasoning consensus (two-round analysis with peer feedback).

    By default, returns cached analysis if less than 24 hours old.
    Use --force to bypass cache and run fresh analysis.
    """
    try:
        # Import here to avoid circular dependencies
        from openbet.analysis.analyzer import Analyzer

        analyzer = Analyzer()

        if not market_id and not analyze_all:
            console.print("[red]✗ Must specify either --market-id or --all[/red]")
            sys.exit(1)

        if market_id and analyze_all:
            console.print("[red]✗ Cannot specify both --market-id and --all[/red]")
            sys.exit(1)

        if analyze_all:
            console.print("[bold]Analyzing all tracked markets...[/bold]")
            if force:
                console.print("[dim]Force mode: bypassing cache for all markets[/dim]")
            # Get all markets from database
            market_repo = MarketRepository()
            markets = market_repo.get_all()

            if not markets:
                console.print("[yellow]No markets in database to analyze[/yellow]")
                return

            console.print(f"Found {len(markets)} markets to analyze\n")

            for market in markets:
                console.print(f"[cyan]Analyzing {market['id']}...[/cyan]")
                result = analyzer.analyze_market(
                    market['id'], option, force=force, cache_hours=cache_hours
                )
                _display_analysis_result(result)
                console.print()
        else:
            console.print(f"[bold]Analyzing market {market_id}...[/bold]")

            # Check if market exists, show message if it will be auto-added
            market_repo = MarketRepository()
            if not market_repo.exists(market_id):
                console.print(f"[dim]Market not in database, fetching from Kalshi...[/dim]")

            if force:
                console.print("[dim]Force mode: bypassing cache[/dim]")

            result = analyzer.analyze_market(
                market_id, option, force=force, cache_hours=cache_hours
            )
            _display_analysis_result(result)

        console.print("\n[green]✓[/green] Analysis complete")

    except Exception as e:
        console.print(f"[red]✗ Error: {str(e)}[/red]")
        import traceback
        traceback.print_exc()
        sys.exit(1)


@cli.command("analyze-series")
@click.argument("event_ticker")
@click.option("--force", is_flag=True, help="Force fresh analysis, bypass cache")
@click.option("--cache-hours", type=int, default=24, help="Cache validity in hours (default: 24)")
@click.option("--add-markets", is_flag=True, help="Add markets to database if not already tracked")
def analyze_series(
    event_ticker: str,
    force: bool,
    cache_hours: int,
    add_markets: bool,
):
    """Find and analyze all markets in a series one by one.

    Args:
        event_ticker: Event/series ticker (e.g., KXTRUMPMEET-26FEB)
        force: Force fresh analysis bypassing cache
        cache_hours: Cache validity in hours (default: 24)
        add_markets: Add markets to database if not already tracked
    """
    try:
        from openbet.analysis.analyzer import Analyzer

        console.print(f"[bold]Finding markets in series: {event_ticker}...[/bold]")

        # Initialize Kalshi client and analyzer
        client = KalshiClient()
        analyzer = Analyzer()
        market_repo = MarketRepository()

        # Convert to uppercase for API call
        event_ticker_upper = event_ticker.upper()

        # Query API for markets in this series
        params = {
            'event_ticker': event_ticker_upper,
            'limit': 50
        }
        data = client._make_request('GET', '/markets', params=params)
        markets = data.get('markets', [])

        if not markets:
            console.print(f"[yellow]No markets found for event ticker: {event_ticker}[/yellow]")
            return

        console.print(f"\n[bold cyan]Found {len(markets)} market(s) in series {event_ticker_upper}[/bold cyan]")

        if force:
            console.print("[dim]Force mode: bypassing cache for all markets[/dim]")

        # Add markets to database if requested
        if add_markets:
            console.print(f"\n[bold]Adding markets to database...[/bold]")
            added_count = 0
            skipped_count = 0

            for market in markets:
                if market_repo.exists(market['ticker']):
                    skipped_count += 1
                    continue

                try:
                    market_obj = Market(**market)
                    market_repo.create(
                        market_id=market_obj.ticker,
                        title=market_obj.title,
                        close_time=str(market_obj.close_time) if market_obj.close_time else None,
                        status=market_obj.status,
                        category=market_obj.category,
                        min_tick_size=0.01,
                        max_tick_size=0.99,
                        metadata={
                            "subtitle": market_obj.subtitle,
                            "yes_sub_title": market_obj.yes_sub_title,
                            "no_sub_title": market_obj.no_sub_title,
                            "volume": market_obj.volume,
                            "open_interest": market_obj.open_interest,
                        },
                    )
                    added_count += 1
                except Exception as e:
                    console.print(f"[yellow]⚠ Failed to add {market['ticker']}: {str(e)}[/yellow]")

            console.print(f"[green]✓[/green] Added {added_count} markets, skipped {skipped_count} (already in database)")

        # Analyze each market one by one
        console.print(f"\n[bold]Analyzing {len(markets)} markets...[/bold]\n")

        success_count = 0
        error_count = 0

        for idx, market in enumerate(markets, 1):
            market_id = market['ticker']
            option_name = market.get('yes_sub_title') or market.get('subtitle') or market_id.split('-')[-1]

            console.print(f"[cyan]{idx}/{len(markets)}[/cyan] Analyzing {market_id} ({option_name})...")

            try:
                result = analyzer.analyze_market(
                    market_id, option=None, force=force, cache_hours=cache_hours
                )
                _display_analysis_result(result)
                success_count += 1
                console.print()
            except Exception as e:
                console.print(f"[red]✗ Error analyzing {market_id}: {str(e)}[/red]\n")
                error_count += 1
                continue

        # Summary
        console.print(f"[bold cyan]Analysis Complete[/bold cyan]")
        console.print(f"[green]✓[/green] Successfully analyzed: {success_count}/{len(markets)}")
        if error_count > 0:
            console.print(f"[red]✗[/red] Failed: {error_count}/{len(markets)}")

    except KalshiError as e:
        console.print(f"[red]✗ Kalshi API error: {str(e)}[/red]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]✗ Error: {str(e)}[/red]")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def _display_analysis_result(result: dict):
    """Display analysis result in a formatted table."""
    # Show cache status if applicable
    if result.get("from_cache"):
        timestamp = result.get("analysis_timestamp", "unknown")
        console.print(f"\n[yellow]ℹ[/yellow] Using cached analysis from {timestamp}")
    else:
        console.print("\n[green]✓[/green] Fresh analysis generated")

    # Check if this is iterative reasoning
    is_iterative = result.get("consensus_method") == "iterative_reasoning"

    if is_iterative and result.get("round_1_responses"):
        # Display both rounds for iterative reasoning
        console.print("\n[bold cyan]Round 1: Initial Analyses[/bold cyan]")

        table1 = Table(show_header=True, header_style="bold magenta")
        table1.add_column("Provider", style="cyan")
        table1.add_column("YES Confidence", style="green")
        table1.add_column("NO Confidence", style="red")

        round1_responses = result.get("round_1_responses", {})
        for provider in ["claude", "openai", "grok", "gemini"]:
            response = round1_responses.get(provider)
            if response:
                if isinstance(response, str):
                    response = json.loads(response)
                yes_conf = response.get("yes_confidence", 0)
                no_conf = response.get("no_confidence", 0)
                table1.add_row(
                    provider.capitalize(),
                    f"{yes_conf:.1%}",
                    f"{no_conf:.1%}",
                )

        console.print(table1)

        # Display Round 1 reasoning
        console.print("\n[bold yellow]Round 1 Reasoning:[/bold yellow]")
        for provider in ["claude", "openai", "grok", "gemini"]:
            response = round1_responses.get(provider)
            if response:
                if isinstance(response, str):
                    response = json.loads(response)
                reasoning = response.get("reasoning", "No reasoning provided")
                console.print(f"\n[cyan]{provider.capitalize()}:[/cyan]")
                console.print(f"[dim]{reasoning}[/dim]")

        # Display Round 2 with changes
        console.print("\n[bold cyan]Round 2: Revised Analyses (after peer review)[/bold cyan]")

        table2 = Table(show_header=True, header_style="bold magenta")
        table2.add_column("Provider", style="cyan")
        table2.add_column("YES Confidence", style="green")
        table2.add_column("NO Confidence", style="red")
        table2.add_column("Change", style="yellow")

        for provider in ["claude", "openai", "grok", "gemini"]:
            response_r2 = result.get(f"{provider}_response")
            response_r1 = round1_responses.get(provider)

            if response_r2:
                if isinstance(response_r2, str):
                    response_r2 = json.loads(response_r2)
                yes_conf_r2 = response_r2.get("yes_confidence", 0)
                no_conf_r2 = response_r2.get("no_confidence", 0)

                # Calculate change from Round 1
                change_str = ""
                if response_r1:
                    if isinstance(response_r1, str):
                        response_r1 = json.loads(response_r1)
                    yes_conf_r1 = response_r1.get("yes_confidence", 0)
                    change = yes_conf_r2 - yes_conf_r1
                    change_str = f"{change:+.1%}" if change != 0 else "—"

                table2.add_row(
                    provider.capitalize(),
                    f"{yes_conf_r2:.1%}",
                    f"{no_conf_r2:.1%}",
                    change_str,
                )

        # Add consensus row
        table2.add_row(
            "[bold]CONSENSUS[/bold]",
            f"[bold]{result.get('consensus_yes_confidence', 0):.1%}[/bold]",
            f"[bold]{result.get('consensus_no_confidence', 0):.1%}[/bold]",
            "",
        )

        console.print(table2)

        # Display Round 2 reasoning
        console.print("\n[bold yellow]Round 2 Revised Reasoning:[/bold yellow]")
        for provider in ["claude", "openai", "grok", "gemini"]:
            response_r2 = result.get(f"{provider}_response")
            if response_r2:
                if isinstance(response_r2, str):
                    response_r2 = json.loads(response_r2)
                reasoning = response_r2.get("reasoning", "No reasoning provided")
                console.print(f"\n[cyan]{provider.capitalize()}:[/cyan]")
                console.print(f"[dim]{reasoning}[/dim]")

        # Show convergence metrics
        if result.get("convergence_metrics"):
            metrics = result["convergence_metrics"]
            console.print(f"\n[dim]Convergence: Average shift {metrics.get('avg_yes_shift', 0):.1%}, Max shift {metrics.get('max_yes_shift', 0):.1%}[/dim]")
    else:
        # Standard display for simple/weighted average
        console.print("\n[bold cyan]Analysis Results[/bold cyan]")

        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Provider", style="cyan")
        table.add_column("YES Confidence", style="green")
        table.add_column("NO Confidence", style="red")

        # Display individual provider results
        for provider in ["claude", "openai", "grok", "gemini"]:
            response = result.get(f"{provider}_response")
            if response:
                if isinstance(response, str):
                    response = json.loads(response)
                yes_conf = response.get("yes_confidence", 0)
                no_conf = response.get("no_confidence", 0)
                table.add_row(
                    provider.capitalize(),
                    f"{yes_conf:.1%}",
                    f"{no_conf:.1%}",
                )

        # Add consensus row
        table.add_row(
            "[bold]CONSENSUS[/bold]",
            f"[bold]{result.get('consensus_yes_confidence', 0):.1%}[/bold]",
            f"[bold]{result.get('consensus_no_confidence', 0):.1%}[/bold]",
        )

        console.print(table)

        # Display reasoning for standard analysis
        console.print("\n[bold yellow]Provider Reasoning:[/bold yellow]")
        for provider in ["claude", "openai", "grok", "gemini"]:
            response = result.get(f"{provider}_response")
            if response:
                if isinstance(response, str):
                    response = json.loads(response)
                reasoning = response.get("reasoning", "No reasoning provided")
                console.print(f"\n[cyan]{provider.capitalize()}:[/cyan]")
                console.print(f"[dim]{reasoning}[/dim]")


@cli.command("place-bet")
@click.argument("market_id")
@click.option("--option", required=True, help="Which option to bet on")
@click.option(
    "--side",
    type=click.Choice(["yes", "no"], case_sensitive=False),
    required=True,
    help="Side to bet on",
)
@click.option("--quantity", type=int, required=True, help="Number of contracts")
@click.option("--price", type=float, help="Limit price (optional, uses market price if not set)")
@click.option("--use-analysis", is_flag=True, help="Show latest analysis before placing")
def place_bet(
    market_id: str,
    option: str,
    side: str,
    quantity: int,
    price: Optional[float],
    use_analysis: bool,
):
    """Place bet on Kalshi using stored analysis.

    Args:
        market_id: Market ticker to bet on
        option: Option within market to bet on
        side: "yes" or "no"
        quantity: Number of contracts to buy
        price: Limit price (optional)
        use_analysis: Show analysis before placing
    """
    try:
        console.print(f"[bold]Preparing to place bet on {market_id}...[/bold]")

        # Show latest analysis if requested
        if use_analysis:
            analysis_repo = AnalysisRepository()
            latest_analysis = analysis_repo.get_latest_by_market(market_id, option)

            if latest_analysis:
                console.print("\n[bold cyan]Latest Analysis[/bold cyan]")
                console.print(
                    f"Consensus YES: {latest_analysis['consensus_yes_confidence']:.1%}"
                )
                console.print(
                    f"Consensus NO: {latest_analysis['consensus_no_confidence']:.1%}"
                )
                console.print(
                    f"Analysis Time: {latest_analysis['analysis_timestamp']}\n"
                )
            else:
                console.print("\n[yellow]⚠ No analysis found for this market[/yellow]\n")

        # Get current market price
        client = KalshiClient()
        orderbook = client.get_orderbook(market_id)

        if side.lower() == "yes":
            market_price = orderbook.best_yes_ask or orderbook.yes_mid_price
        else:
            market_price = orderbook.best_no_ask or orderbook.no_mid_price

        bet_price = price if price else market_price

        if bet_price is None:
            console.print("[red]✗ Could not determine bet price[/red]")
            sys.exit(1)

        # Display order details
        console.print("[bold cyan]Order Details[/bold cyan]")
        table = Table(show_header=False)
        table.add_column("Field", style="cyan")
        table.add_column("Value", style="white")

        table.add_row("Market", market_id)
        table.add_row("Option", option)
        table.add_row("Side", side.upper())
        table.add_row("Quantity", str(quantity))
        table.add_row("Price", f"${bet_price:.2f}")
        table.add_row("Total Cost", f"${bet_price * quantity:.2f}")

        console.print(table)

        # Confirm with user
        if not click.confirm("\nProceed with bet placement?"):
            console.print("[yellow]Bet cancelled[/yellow]")
            return

        # Place order
        console.print("\n[bold]Placing order...[/bold]")

        order = client.place_order(
            ticker=market_id,
            side=side.lower(),
            action="buy",
            count=quantity,
            yes_price=bet_price if side.lower() == "yes" else None,
            no_price=bet_price if side.lower() == "no" else None,
        )

        console.print(f"[green]✓ Order placed successfully![/green]")
        console.print(f"Order ID: {order.order_id}")

        # Update position in database
        position_repo = PositionRepository()
        position_repo.create_or_update(
            market_id=market_id,
            option=option,
            side=side.lower(),
            quantity=quantity,
            avg_price=bet_price,
            metadata={"order_id": order.order_id},
        )

        console.print("[green]✓ Position updated in database[/green]")

    except KalshiError as e:
        console.print(f"[red]✗ Kalshi API error: {str(e)}[/red]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]✗ Error: {str(e)}[/red]")
        sys.exit(1)


@cli.command("scan-opportunities")
@click.option("--market-id", help="Scan specific market (default: all tracked)")
@click.option("--threshold", type=float, default=0.05, help="Minimum divergence threshold (default: 0.05)")
@click.option("--limit", type=int, default=10, help="Max opportunities to show (default: 10)")
@click.option("--force", is_flag=True, help="Force fresh analysis bypassing cache")
def scan_opportunities(market_id: Optional[str], threshold: float, limit: int, force: bool):
    """Scan for trading opportunities based on consensus vs market divergence."""
    from openbet.trading.strategy import TradingStrategy

    try:
        console.print(f"[bold]Scanning for opportunities (threshold: {threshold:.1%})...[/bold]\n")

        # Initialize strategy
        strategy = TradingStrategy(entry_threshold=threshold)

        # Scan for opportunities
        market_ids = [market_id] if market_id else None
        opportunities = strategy.scan_for_opportunities(
            market_ids=market_ids,
            force_analysis=force,
        )

        if not opportunities:
            console.print("[yellow]No opportunities found meeting criteria[/yellow]")
            return

        # Limit results
        opportunities = opportunities[:limit]

        # Display opportunities table
        console.print(f"[bold cyan]Trading Opportunities ({len(opportunities)} found)[/bold cyan]\n")

        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Market ID", style="cyan")
        table.add_column("Side", style="yellow")
        table.add_column("Divergence", style="green")
        table.add_column("Consensus", style="white")
        table.add_column("Market", style="white")
        table.add_column("Qty", style="blue")
        table.add_column("Price", style="white")
        table.add_column("Expected $", style="green")
        table.add_column("Warnings", style="red")

        for signal in opportunities:
            side_str = signal.selected_side.upper() if signal.selected_side else "N/A"
            divergence_str = f"{signal.divergence_magnitude:.1%}"

            if signal.selected_side == "yes":
                consensus_str = f"{signal.consensus_yes_prob:.1%}"
                market_str = f"{signal.market_yes_prob:.1%}"
            else:
                consensus_str = f"{signal.consensus_no_prob:.1%}"
                market_str = f"{signal.market_no_prob:.1%}"

            price_str = f"${signal.recommended_price:.2f}"
            profit_str = f"${signal.expected_profit:.2f}"
            warnings_str = f"{len(signal.risk_warnings)}" if signal.risk_warnings else "-"

            table.add_row(
                signal.market_id,
                side_str,
                divergence_str,
                consensus_str,
                market_str,
                str(signal.recommended_quantity),
                price_str,
                profit_str,
                warnings_str,
            )

        console.print(table)

        console.print(f"\n[dim]Use 'recommend-trade <MARKET_ID>' to analyze a specific opportunity[/dim]")

    except Exception as e:
        console.print(f"[red]✗ Error: {str(e)}[/red]")
        sys.exit(1)


@cli.command("recommend-trade")
@click.argument("market_id")
@click.option("--quantity", type=int, help="Override recommended quantity")
@click.option("--price", type=float, help="Override recommended price")
@click.option("--force", is_flag=True, help="Force fresh analysis, bypass cache")
@click.option("--cache-hours", type=int, default=24, help="Cache validity in hours (default: 24)")
def recommend_trade(
    market_id: str,
    quantity: Optional[int],
    price: Optional[float],
    force: bool,
    cache_hours: int,
):
    """Analyze market and display trade recommendations for manual execution."""
    from openbet.trading.strategy import TradingStrategy

    try:
        console.print(f"[bold]Analyzing {market_id}...[/bold]\n")

        if force:
            console.print("[dim]Force mode: bypassing cache[/dim]\n")

        # Initialize strategy
        strategy = TradingStrategy()

        # Generate signal
        signal = strategy.signal_generator.generate_entry_signal(
            market_id=market_id,
            option="yes",
            force_analysis=force,
            cache_hours=cache_hours,
        )

        if not signal:
            console.print("[yellow]No trading opportunity found for this market[/yellow]")
            console.print("[dim]The divergence may be below the threshold (5%) or filters failed[/dim]")
            return

        # Display detailed analysis
        console.print("[bold cyan]Market Analysis[/bold cyan]\n")

        # Market details table
        details_table = Table(show_header=True, header_style="bold magenta")
        details_table.add_column("Metric", style="cyan")
        details_table.add_column("Value", style="white")

        details_table.add_row("Market ID", signal.market_id)
        details_table.add_row("Signal Type", signal.signal_type.upper())
        details_table.add_row("Timestamp", signal.signal_timestamp.strftime("%Y-%m-%d %H:%M:%S"))

        console.print(details_table)

        # Consensus vs Market table
        console.print("\n[bold cyan]Consensus vs Market[/bold cyan]\n")

        comparison_table = Table(show_header=True, header_style="bold magenta")
        comparison_table.add_column("Side", style="cyan")
        comparison_table.add_column("Consensus", style="green")
        comparison_table.add_column("Market", style="yellow")
        comparison_table.add_column("Divergence", style="red")

        comparison_table.add_row(
            "YES",
            f"{signal.consensus_yes_prob:.1%}",
            f"{signal.market_yes_prob:.1%}",
            f"{signal.divergence_yes:.1%}",
        )
        comparison_table.add_row(
            "NO",
            f"{signal.consensus_no_prob:.1%}",
            f"{signal.market_no_prob:.1%}",
            f"{signal.divergence_no:.1%}",
        )

        console.print(comparison_table)

        # Recommendation
        console.print("\n[bold cyan]Recommendation[/bold cyan]\n")

        rec_table = Table(show_header=True, header_style="bold magenta")
        rec_table.add_column("Field", style="cyan")
        rec_table.add_column("Value", style="white")

        rec_table.add_row("Action", signal.recommended_action.upper())
        rec_table.add_row("Side", signal.selected_side.upper() if signal.selected_side else "N/A")
        rec_table.add_row("Quantity", str(quantity or signal.recommended_quantity))
        rec_table.add_row("Price", f"${price or signal.recommended_price:.2f}")
        rec_table.add_row("Expected Profit", f"${signal.expected_profit:.2f}")
        rec_table.add_row("Divergence", f"{signal.divergence_magnitude:.1%}")

        console.print(rec_table)

        # Risk warnings
        if signal.risk_warnings:
            console.print("\n[bold yellow]Risk Warnings[/bold yellow]")
            for warning in signal.risk_warnings:
                console.print(f"  [yellow]⚠[/yellow]  {warning}")

        if not signal.passed_filters:
            console.print("\n[red]✗ Signal did not pass risk filters[/red]")

        # Display manual trading instructions
        console.print("\n[bold green]═══════════════════════════════════════════════════════[/bold green]")
        console.print("[bold green]MANUAL TRADE RECOMMENDATION[/bold green]")
        console.print("[bold green]═══════════════════════════════════════════════════════[/bold green]")
        console.print(f"\n[bold cyan]Market:[/bold cyan] {signal.market_id}")
        console.print(f"[bold cyan]Action:[/bold cyan] {signal.recommended_action.upper()}")
        console.print(f"[bold cyan]Side:[/bold cyan] {signal.selected_side.upper() if signal.selected_side else 'N/A'}")
        console.print(f"[bold cyan]Quantity:[/bold cyan] {quantity or signal.recommended_quantity} contracts")
        console.print(f"[bold cyan]Price:[/bold cyan] ${price or signal.recommended_price:.2f}")
        console.print(f"[bold cyan]Total Cost:[/bold cyan] ${(quantity or signal.recommended_quantity) * (price or signal.recommended_price):.2f}")
        console.print("\n[dim]Navigate to Kalshi platform and manually place this trade[/dim]")
        console.print("[bold green]═══════════════════════════════════════════════════════[/bold green]")

    except Exception as e:
        console.print(f"[red]✗ Error: {str(e)}[/red]")
        import traceback
        traceback.print_exc()
        sys.exit(1)


@cli.command("monitor-exits")
@click.option("--auto-sell", is_flag=True, help="Auto-execute exits meeting criteria")
@click.option("--threshold", type=float, default=0.01, help="Convergence threshold (default: 0.01)")
def monitor_exits(auto_sell: bool, threshold: float):
    """Monitor open positions for exit opportunities."""
    from openbet.trading.strategy import TradingStrategy

    try:
        console.print(f"[bold]Monitoring positions for exits (threshold: {threshold:.1%})...[/bold]\n")

        # Initialize strategy
        strategy = TradingStrategy(exit_threshold=threshold)

        # Get exit signals
        exit_signals = strategy.monitor_exits(force_analysis=False)

        if not exit_signals:
            console.print("[yellow]No positions ready to exit[/yellow]")
            return

        # Display exit opportunities
        console.print(f"[bold cyan]Exit Opportunities ({len(exit_signals)} positions)[/bold cyan]\n")

        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Market ID", style="cyan")
        table.add_column("Side", style="yellow")
        table.add_column("Quantity", style="blue")
        table.add_column("Current Price", style="white")
        table.add_column("Consensus", style="green")
        table.add_column("Divergence", style="white")
        table.add_column("Expected P&L", style="green")

        for signal in exit_signals:
            side_str = signal.selected_side.upper() if signal.selected_side else "N/A"

            if signal.selected_side == "yes":
                current_price = signal.market_yes_prob
                consensus = signal.consensus_yes_prob
            else:
                current_price = signal.market_no_prob
                consensus = signal.consensus_no_prob

            profit_style = "green" if signal.expected_profit > 0 else "red"

            table.add_row(
                signal.market_id,
                side_str,
                str(signal.recommended_quantity),
                f"${current_price:.2f}",
                f"{consensus:.1%}",
                f"{signal.divergence_magnitude:.1%}",
                f"[{profit_style}]${signal.expected_profit:.2f}[/{profit_style}]",
            )

        console.print(table)

        # Execute exits if auto-sell is enabled
        if auto_sell:
            console.print("\n[bold]Auto-sell enabled - executing exits...[/bold]")
            for signal in exit_signals:
                console.print(f"\nExiting {signal.market_id}...")
                decision = strategy.execute_signal(signal, user_approved=True)
                if decision.executed:
                    console.print(f"[green]✓ Exited successfully. P&L: ${decision.realized_pnl:.2f}[/green]")
                else:
                    console.print(f"[red]✗ Exit failed[/red]")
        else:
            # Prompt for each exit
            for signal in exit_signals:
                console.print(f"\n[bold]Exit {signal.market_id}?[/bold]")
                console.print(f"Expected P&L: ${signal.expected_profit:.2f}")

                if click.confirm("Proceed with exit?"):
                    decision = strategy.execute_signal(signal, user_approved=True)
                    if decision.executed:
                        console.print(f"[green]✓ Exited successfully. P&L: ${decision.realized_pnl:.2f}[/green]")
                    else:
                        console.print(f"[red]✗ Exit failed[/red]")
                else:
                    console.print("[yellow]Exit skipped[/yellow]")
                    strategy.execute_signal(signal, user_approved=False, user_notes="User skipped exit")

    except Exception as e:
        console.print(f"[red]✗ Error: {str(e)}[/red]")
        import traceback
        traceback.print_exc()
        sys.exit(1)


@cli.command("trading-history")
@click.option("--limit", type=int, default=20, help="Number of records to display (default: 20)")
@click.option("--signal-type", type=click.Choice(["entry", "exit", "all"]), default="all", help="Filter by signal type")
@click.option("--decision", type=click.Choice(["approved", "rejected", "ignored", "all"]), default="all", help="Filter by decision")
def trading_history(limit: int, signal_type: str, decision: str):
    """Display trading signal history and performance statistics."""
    from openbet.trading.strategy import TradingStrategy

    try:
        console.print("[bold]Trading History[/bold]\n")

        # Initialize strategy
        strategy = TradingStrategy()

        # Get signal history
        signal_filter = None if signal_type == "all" else signal_type
        signals = strategy.get_signal_history(limit=limit, signal_type=signal_filter)

        # Get decision history
        decision_filter = None if decision == "all" else decision
        decisions_dict = {}

        # Build decisions lookup
        all_decisions = strategy.get_decision_history(limit=1000)
        for dec in all_decisions:
            decisions_dict[dec.get("signal_id")] = dec

        # Display signals with decisions
        console.print(f"[bold cyan]Recent Signals ({len(signals)})[/bold cyan]\n")

        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Time", style="cyan")
        table.add_column("Market", style="white")
        table.add_column("Type", style="yellow")
        table.add_column("Side", style="blue")
        table.add_column("Divergence", style="green")
        table.add_column("Qty", style="white")
        table.add_column("Decision", style="white")
        table.add_column("Executed", style="white")

        for sig in signals:
            sig_id = sig.get("id")
            dec = decisions_dict.get(sig_id)

            timestamp = sig.get("signal_timestamp", "N/A")
            if isinstance(timestamp, str) and "T" in timestamp:
                timestamp = timestamp.split("T")[0] + " " + timestamp.split("T")[1].split(".")[0]

            decision_str = dec.get("decision", "pending") if dec else "pending"
            executed_str = "✓" if dec and dec.get("executed") else "-"

            if decision_filter and decision_str != decision_filter:
                continue

            table.add_row(
                str(timestamp)[:19],
                sig.get("market_id", "N/A")[:20],
                sig.get("signal_type", "N/A"),
                (sig.get("selected_side") or "N/A").upper(),
                f"{sig.get('divergence_magnitude', 0.0):.1%}",
                str(sig.get("recommended_quantity", 0)),
                decision_str,
                executed_str,
            )

        console.print(table)

        # Display performance statistics
        console.print("\n[bold cyan]Performance Statistics[/bold cyan]\n")

        stats = strategy.get_performance_stats()

        stats_table = Table(show_header=True, header_style="bold magenta")
        stats_table.add_column("Metric", style="cyan")
        stats_table.add_column("Value", style="white")

        stats_table.add_row("Total Signals", str(stats["total_signals"]))
        stats_table.add_row("Total Decisions", str(stats["total_decisions"]))
        stats_table.add_row("Approved", str(stats["approved"]))
        stats_table.add_row("Rejected", str(stats["rejected"]))
        stats_table.add_row("Approval Rate", f"{stats['approval_rate']:.1%}")
        stats_table.add_row("Executed Trades", str(stats["executed"]))
        stats_table.add_row("Total Closed Trades", str(stats["total_trades"]))
        stats_table.add_row("Wins", str(stats["wins"]))
        stats_table.add_row("Losses", str(stats["losses"]))
        stats_table.add_row("Win Rate", f"{stats['win_rate']:.1%}")

        pnl_style = "green" if stats["total_pnl"] >= 0 else "red"
        stats_table.add_row("Total P&L", f"[{pnl_style}]${stats['total_pnl']:.2f}[/{pnl_style}]")
        stats_table.add_row("Avg P&L per Trade", f"${stats['avg_pnl_per_trade']:.2f}")

        console.print(stats_table)

    except Exception as e:
        console.print(f"[red]✗ Error: {str(e)}[/red]")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    cli()
