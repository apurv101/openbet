"""Helper script to test Kalshi API connection and retrieve market tickers."""

import sys
from typing import List

from openbet.kalshi.client import KalshiClient
from openbet.kalshi.exceptions import (
    KalshiAPIError,
    KalshiAuthenticationError,
    KalshiError,
)
from openbet.kalshi.models import Market


def main():
    """Test Kalshi API connection and list available markets."""
    print("=" * 60)
    print("Kalshi API Connection Test")
    print("=" * 60)
    print()

    try:
        # Initialize Kalshi client (loads credentials from .env)
        print("Initializing Kalshi client...")
        client = KalshiClient()
        print("Client initialized successfully")
        print()

        # Test authentication by fetching markets
        print("Attempting to authenticate and fetch markets...")
        markets: List[Market] = client.get_markets(limit=10, status="open")
        print()

        # Success!
        print("=" * 60)
        print("SUCCESS: Connected to Kalshi API!")
        print("=" * 60)
        print()
        print(f"Found {len(markets)} open markets:")
        print()

        # Display markets in a formatted table
        print(f"{'#':<4} {'Ticker':<30} {'Title'}")
        print("-" * 80)
        for idx, market in enumerate(markets, 1):
            # Truncate title if too long
            title = market.title if len(market.title) <= 45 else market.title[:42] + "..."
            print(f"{idx:<4} {market.ticker:<30} {title}")

        print()
        print("=" * 60)
        print("Next Steps:")
        print("=" * 60)
        print("Test the CLI command with one of the tickers above:")
        print(f"  python -m openbet.cli check-market {markets[0].ticker}")
        print()

        return 0

    except KalshiAuthenticationError as e:
        print()
        print("=" * 60)
        print("AUTHENTICATION FAILED")
        print("=" * 60)
        print(f"Error: {e}")
        print()
        print("Possible causes:")
        print("  1. Invalid API key or secret in .env file")
        print("  2. RSA private key format is not compatible")
        print("  3. Kalshi API expects a different authentication method")
        print()
        print("Please verify:")
        print("  - KALSHI_API_KEY in .env is correct")
        print("  - KALSHI_API_SECRET in .env is correct")
        print("  - KALSHI_BASE_URL is set to: https://api.kalshi.com/v2")
        print()
        return 1

    except KalshiAPIError as e:
        print()
        print("=" * 60)
        print("API ERROR")
        print("=" * 60)
        print(f"Error: {e}")
        print()
        print("Possible causes:")
        print("  1. Kalshi API is experiencing issues")
        print("  2. Rate limit exceeded")
        print("  3. Invalid API endpoint or version")
        print()
        print(f"Check Kalshi API status or try again later")
        print()
        return 1

    except KalshiError as e:
        print()
        print("=" * 60)
        print("KALSHI ERROR")
        print("=" * 60)
        print(f"Error: {e}")
        print()
        return 1

    except ConnectionError as e:
        print()
        print("=" * 60)
        print("CONNECTION ERROR")
        print("=" * 60)
        print(f"Error: {e}")
        print()
        print("Possible causes:")
        print("  1. No internet connection")
        print("  2. Kalshi API is unreachable")
        print("  3. Incorrect KALSHI_BASE_URL")
        print()
        print("Please verify your network connection and KALSHI_BASE_URL in .env")
        print()
        return 1

    except Exception as e:
        print()
        print("=" * 60)
        print("UNEXPECTED ERROR")
        print("=" * 60)
        print(f"Error type: {type(e).__name__}")
        print(f"Error message: {e}")
        print()
        print("This is an unexpected error. Please check:")
        print("  1. .env file format is correct")
        print("  2. All required dependencies are installed")
        print("  3. Python version compatibility")
        print()
        return 1


if __name__ == "__main__":
    sys.exit(main())
