"""Kalshi API client for market data and order execution."""

import base64
import time
from typing import Any, Dict, List, Optional

import requests
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from openbet.config import get_settings
from openbet.kalshi.exceptions import (
    KalshiAPIError,
    KalshiAuthenticationError,
    KalshiMarketNotFoundError,
    KalshiOrderError,
    KalshiRateLimitError,
)
from openbet.kalshi.models import (
    Event,
    GetEventsResponse,
    GetMarketsResponse,
    Market,
    Order,
    OrderRequest,
    Orderbook,
    Position,
)


class KalshiClient:
    """Client for interacting with Kalshi API."""

    def __init__(self, api_key: Optional[str] = None, api_secret: Optional[str] = None):
        """Initialize Kalshi client.

        Args:
            api_key: Kalshi API key. If None, uses config value.
            api_secret: Kalshi API secret (RSA private key in PEM format). If None, uses config value.
        """
        settings = get_settings()
        self.api_key = api_key or settings.kalshi_api_key
        self.api_secret = api_secret or settings.kalshi_api_secret
        self.base_url = settings.kalshi_base_url

        self.session = self._create_session()
        self.private_key = self._load_private_key()

    def _create_session(self) -> requests.Session:
        """Create requests session with retry logic."""
        session = requests.Session()

        # Configure retry strategy
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS", "POST", "DELETE"],
        )

        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        return session

    def _load_private_key(self):
        """Load RSA private key from PEM-formatted string.

        Returns:
            RSA private key object

        Raises:
            KalshiAuthenticationError: If key cannot be loaded
        """
        try:
            # Handle case where key might have escaped newlines
            key_string = self.api_secret.replace("\\n", "\n")
            key_bytes = key_string.encode("utf-8")

            private_key = serialization.load_pem_private_key(
                key_bytes, password=None, backend=default_backend()
            )
            return private_key
        except Exception as e:
            raise KalshiAuthenticationError(
                f"Failed to load RSA private key: {str(e)}"
            )

    def _create_signature(self, timestamp: str, method: str, path: str) -> str:
        """Create RSA-PSS signature for API request.

        Args:
            timestamp: Request timestamp in milliseconds
            method: HTTP method (GET, POST, etc.)
            path: API endpoint path without query parameters

        Returns:
            Base64-encoded signature string
        """
        # Remove query parameters from path
        path_without_query = path.split("?")[0]

        # Create message to sign: timestamp + method + path
        message = f"{timestamp}{method}{path_without_query}".encode("utf-8")

        # Sign using RSA-PSS with SHA256
        signature = self.private_key.sign(
            message,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.DIGEST_LENGTH,
            ),
            hashes.SHA256(),
        )

        # Return base64-encoded signature
        return base64.b64encode(signature).decode("utf-8")

    def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Make authenticated API request with RSA-PSS signature.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            params: Query parameters
            json_data: JSON body data

        Returns:
            Response data as dictionary

        Raises:
            KalshiAPIError: If request fails
            KalshiRateLimitError: If rate limited
        """
        # Generate timestamp in milliseconds
        timestamp = str(int(time.time() * 1000))

        # Create signature
        signature = self._create_signature(timestamp, method, endpoint)

        # Set authentication headers
        headers = {
            "KALSHI-ACCESS-KEY": self.api_key,
            "KALSHI-ACCESS-SIGNATURE": signature,
            "KALSHI-ACCESS-TIMESTAMP": timestamp,
        }

        url = f"{self.base_url}{endpoint}"

        try:
            response = self.session.request(
                method=method,
                url=url,
                headers=headers,
                params=params,
                json=json_data,
                timeout=10,
            )

            if response.status_code == 429:
                raise KalshiRateLimitError("Rate limit exceeded")

            response.raise_for_status()
            return response.json()

        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code if e.response else None
            try:
                error_data = e.response.json() if e.response else {}
            except:
                error_data = {}

            if status_code == 404:
                raise KalshiMarketNotFoundError(f"Resource not found: {endpoint}")

            raise KalshiAPIError(
                f"API request failed: {str(e)}",
                status_code=status_code,
                response_data=error_data,
            )

        except requests.exceptions.RequestException as e:
            raise KalshiAPIError(f"Request failed: {str(e)}")

    def get_market(self, market_id: str) -> Market:
        """Get market details by ticker.

        Args:
            market_id: Market ticker

        Returns:
            Market object with details
        """
        data = self._make_request("GET", f"/markets/{market_id}")
        market_data = data.get("market", data)
        return Market(**market_data)

    def get_markets(
        self,
        limit: int = 100,
        cursor: Optional[str] = None,
        status: Optional[str] = None,
        series_ticker: Optional[str] = None,
    ) -> List[Market]:
        """Get list of markets with optional filters.

        Args:
            limit: Number of markets to return
            cursor: Pagination cursor
            status: Filter by status (e.g., "open", "closed")
            series_ticker: Filter by series ticker

        Returns:
            List of Market objects
        """
        params = {"limit": limit}
        if cursor:
            params["cursor"] = cursor
        if status:
            params["status"] = status
        if series_ticker:
            params["series_ticker"] = series_ticker

        data = self._make_request("GET", "/markets", params=params)
        markets_data = data.get("markets", [])
        return [Market(**market) for market in markets_data]

    def get_orderbook(self, market_id: str, depth: int = 5) -> Orderbook:
        """Get market orderbook.

        Args:
            market_id: Market ticker
            depth: Number of price levels to fetch

        Returns:
            Orderbook object
        """
        params = {"depth": depth}
        data = self._make_request("GET", f"/markets/{market_id}/orderbook", params=params)

        orderbook_data = data.get("orderbook", {})

        # Handle empty/null orderbook responses
        yes_data = orderbook_data.get("yes")
        no_data = orderbook_data.get("no")

        # Parse orderbook entries (handle null/empty cases)
        yes_bids = []
        yes_asks = []
        no_bids = []
        no_asks = []

        # The API returns a simple list of [price_cents, quantity] pairs
        # These are asks (offers to sell) - prices at which you can buy
        if yes_data and isinstance(yes_data, list):
            yes_asks = [
                {"price": item[0] / 100, "quantity": item[1]}
                for item in yes_data if isinstance(item, list) and len(item) >= 2
            ]

        if no_data and isinstance(no_data, list):
            no_asks = [
                {"price": item[0] / 100, "quantity": item[1]}
                for item in no_data if isinstance(item, list) and len(item) >= 2
            ]

        return Orderbook(
            yes_bids=yes_bids,
            yes_asks=yes_asks,
            no_bids=no_bids,
            no_asks=no_asks,
        )

    def get_position(self, market_id: str) -> Optional[Position]:
        """Get user's current position in a market.

        Args:
            market_id: Market ticker

        Returns:
            Position object or None if no position
        """
        try:
            data = self._make_request("GET", f"/portfolio/positions/{market_id}")
            position_data = data.get("position", data)
            return Position(**position_data)
        except KalshiMarketNotFoundError:
            return None

    def get_all_positions(self) -> List[Position]:
        """Get all user positions.

        Returns:
            List of Position objects
        """
        data = self._make_request("GET", "/portfolio/positions")
        positions_data = data.get("positions", [])
        return [Position(**pos) for pos in positions_data]

    def place_order(
        self,
        ticker: str,
        side: str,
        action: str,
        count: int,
        yes_price: Optional[float] = None,
        no_price: Optional[float] = None,
        order_type: str = "limit",
    ) -> Order:
        """Place an order on a market.

        Args:
            ticker: Market ticker
            side: "yes" or "no"
            action: "buy" or "sell"
            count: Number of contracts
            yes_price: Yes price in dollars (converted to cents)
            no_price: No price in dollars (converted to cents)
            order_type: "limit" or "market"

        Returns:
            Order object with placement details

        Raises:
            KalshiOrderError: If order placement fails
        """
        order_request = OrderRequest(
            ticker=ticker,
            side=side.lower(),
            action=action.lower(),
            count=count,
            type=order_type,
            yes_price=int(yes_price * 100) if yes_price else None,
            no_price=int(no_price * 100) if no_price else None,
        )

        try:
            data = self._make_request(
                "POST", "/portfolio/orders", json_data=order_request.model_dump(exclude_none=True)
            )
            order_data = data.get("order", data)
            return Order(**order_data)

        except KalshiAPIError as e:
            raise KalshiOrderError(f"Order placement failed: {str(e)}")

    def get_market_history(
        self,
        market_id: str,
        limit: int = 100,
        min_ts: Optional[int] = None,
        max_ts: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Get historical trades for a market.

        Args:
            market_id: Market ticker
            limit: Number of trades to fetch
            min_ts: Minimum timestamp (seconds)
            max_ts: Maximum timestamp (seconds)

        Returns:
            List of trade data dictionaries
        """
        params = {"limit": limit}
        if min_ts:
            params["min_ts"] = min_ts
        if max_ts:
            params["max_ts"] = max_ts

        data = self._make_request("GET", f"/markets/{market_id}/history", params=params)
        return data.get("history", [])

    def cancel_order(self, order_id: str) -> None:
        """Cancel an existing order.

        Args:
            order_id: Order ID to cancel
        """
        try:
            self._make_request("DELETE", f"/portfolio/orders/{order_id}")
        except KalshiAPIError as e:
            raise KalshiOrderError(f"Order cancellation failed: {str(e)}")

    def get_events(
        self,
        limit: int = 200,
        cursor: Optional[str] = None,
        status: Optional[str] = None,
        series_ticker: Optional[str] = None,
        with_nested_markets: bool = False,
    ) -> List[Event]:
        """Get list of events with optional filters.

        Endpoint: GET /events
        Docs: https://docs.kalshi.com/typescript-sdk/api/EventsApi#getevents

        Args:
            limit: Number of events to return (max 200)
            cursor: Pagination cursor
            status: Filter by status (e.g., "open", "closed")
            series_ticker: Filter by series ticker
            with_nested_markets: Include nested market data

        Returns:
            List of Event objects

        Rate limiting: Conservative approach with 0.5s delay
        """
        params = {"limit": min(limit, 200)}  # API max is 200
        if cursor:
            params["cursor"] = cursor
        if status:
            params["status"] = status
        if series_ticker:
            params["series_ticker"] = series_ticker
        if with_nested_markets:
            params["with_nested_markets"] = "true"

        # Conservative rate limiting: add 0.5s delay between calls
        time.sleep(0.5)

        data = self._make_request("GET", "/events", params=params)
        events_data = data.get("events", [])
        return [Event(**event) for event in events_data]

    def get_events_with_cursor(
        self,
        limit: int = 200,
        cursor: Optional[str] = None,
        status: Optional[str] = None,
        series_ticker: Optional[str] = None,
        with_nested_markets: bool = False,
    ) -> GetEventsResponse:
        """Get list of events with cursor for pagination.

        Args:
            limit: Number of events to return (max 200)
            cursor: Pagination cursor from previous response
            status: Filter by status (valid: unopened, open, closed, settled)
            series_ticker: Filter by series ticker
            with_nested_markets: Include nested market data

        Returns:
            GetEventsResponse with events and cursor

        Raises:
            ValueError: If status parameter is invalid
        """
        # Validate status parameter
        valid_statuses = {"unopened", "open", "closed", "settled"}
        if status and status not in valid_statuses:
            raise ValueError(
                f"Invalid status '{status}'. Must be one of: {', '.join(sorted(valid_statuses))}"
            )

        params = {"limit": min(limit, 200)}
        if cursor:
            params["cursor"] = cursor
        if status:
            params["status"] = status
        if series_ticker:
            params["series_ticker"] = series_ticker
        if with_nested_markets:
            params["with_nested_markets"] = "true"

        time.sleep(0.5)  # Conservative rate limiting

        data = self._make_request("GET", "/events", params=params)

        # Extract cursor from response
        cursor_value = data.get("cursor")
        if cursor_value == "":  # Empty string means no more pages
            cursor_value = None

        return GetEventsResponse(
            events=[Event(**event) for event in data.get("events", [])],
            cursor=cursor_value
        )

    def get_markets_with_cursor(
        self,
        limit: int = 100,
        cursor: Optional[str] = None,
        status: Optional[str] = None,
        series_ticker: Optional[str] = None,
    ) -> GetMarketsResponse:
        """Get list of markets with cursor for pagination.

        Args:
            limit: Number of markets to return (max 200)
            cursor: Pagination cursor from previous response
            status: Filter by status (valid: unopened, open, closed, settled)
            series_ticker: Filter by series ticker

        Returns:
            GetMarketsResponse with markets and cursor

        Raises:
            ValueError: If status parameter is invalid
        """
        valid_statuses = {"unopened", "open", "closed", "settled"}
        if status and status not in valid_statuses:
            raise ValueError(
                f"Invalid status '{status}'. Must be one of: {', '.join(sorted(valid_statuses))}"
            )

        params = {"limit": limit}
        if cursor:
            params["cursor"] = cursor
        if status:
            params["status"] = status
        if series_ticker:
            params["series_ticker"] = series_ticker

        data = self._make_request("GET", "/markets", params=params)

        cursor_value = data.get("cursor")
        if cursor_value == "":
            cursor_value = None

        return GetMarketsResponse(
            markets=[Market(**market) for market in data.get("markets", [])],
            cursor=cursor_value
        )

    def get_event(self, event_ticker: str) -> Event:
        """Get single event details.

        Args:
            event_ticker: Event ticker to fetch

        Returns:
            Event object with details

        Rate limiting: Conservative 0.3s delay
        """
        time.sleep(0.3)  # Conservative rate limiting
        data = self._make_request("GET", f"/events/{event_ticker}")
        event_data = data.get("event", data)
        return Event(**event_data)
