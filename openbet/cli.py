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
        table.add_row("Status", market.status or "N/A")
        table.add_row("Category", market.category or "N/A")
        table.add_row("Close Time", str(market.close_time) if market.close_time else "N/A")
        table.add_row("Volume (24h)", str(market.volume_24h) if market.volume_24h else "N/A")
        table.add_row("Open Interest", str(market.open_interest) if market.open_interest else "N/A")

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


@cli.command("analyze")
@click.option("--market-id", help="Specific market to analyze")
@click.option("--all", "analyze_all", is_flag=True, help="Analyze all markets in database")
@click.option("--option", help="Specific option to analyze within market")
def analyze(market_id: Optional[str], analyze_all: bool, option: Optional[str]):
    """Run LLM analysis on market(s) and store results.

    Calls multiple LLM providers (Claude, OpenAI, Grok) to analyze market options
    and calculates consensus confidence scores.
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
            # Get all markets from database
            market_repo = MarketRepository()
            markets = market_repo.get_all()

            if not markets:
                console.print("[yellow]No markets in database to analyze[/yellow]")
                return

            console.print(f"Found {len(markets)} markets to analyze\n")

            for market in markets:
                console.print(f"[cyan]Analyzing {market['id']}...[/cyan]")
                result = analyzer.analyze_market(market['id'], option)
                _display_analysis_result(result)
                console.print()
        else:
            console.print(f"[bold]Analyzing market {market_id}...[/bold]")
            result = analyzer.analyze_market(market_id, option)
            _display_analysis_result(result)

        console.print("\n[green]✓[/green] Analysis complete and stored in database")

    except Exception as e:
        console.print(f"[red]✗ Error: {str(e)}[/red]")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def _display_analysis_result(result: dict):
    """Display analysis result in a formatted table."""
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
