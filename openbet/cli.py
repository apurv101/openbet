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
    and calculates consensus confidence scores.

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


def _display_analysis_result(result: dict):
    """Display analysis result in a formatted table."""
    # Show cache status if applicable
    if result.get("from_cache"):
        timestamp = result.get("analysis_timestamp", "unknown")
        console.print(f"\n[yellow]ℹ[/yellow] Using cached analysis from {timestamp}")
    else:
        console.print("\n[green]✓[/green] Fresh analysis generated")

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


if __name__ == "__main__":
    cli()
