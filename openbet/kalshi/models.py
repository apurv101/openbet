"""Pydantic models for Kalshi API data structures."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class MarketOption(BaseModel):
    """A single option within a market."""

    ticker: str
    title: Optional[str] = None


class Market(BaseModel):
    """Kalshi market details."""

    ticker: str = Field(..., alias="ticker")
    event_ticker: Optional[str] = None
    title: str
    subtitle: Optional[str] = None
    open_time: Optional[datetime] = None
    close_time: Optional[datetime] = None
    expiration_time: Optional[datetime] = None
    status: Optional[str] = None
    category: Optional[str] = None
    yes_sub_title: Optional[str] = None
    no_sub_title: Optional[str] = None
    ranged_group_id: Optional[str] = None
    strike_type: Optional[str] = None
    floor_strike: Optional[float] = None
    cap_strike: Optional[float] = None
    last_price: Optional[float] = None
    previous_yes_bid: Optional[float] = None
    previous_yes_ask: Optional[float] = None
    previous_price: Optional[float] = None
    volume: Optional[int] = None
    volume_24h: Optional[int] = None
    liquidity: Optional[int] = None
    open_interest: Optional[int] = None
    result: Optional[str] = None
    can_close_early: Optional[bool] = None
    expected_expiration_time: Optional[datetime] = None

    class Config:
        populate_by_name = True


class OrderbookEntry(BaseModel):
    """A single entry in the orderbook."""

    price: float
    quantity: int


class Orderbook(BaseModel):
    """Market orderbook with bids and asks."""

    yes_bids: List[OrderbookEntry] = Field(default_factory=list)
    yes_asks: List[OrderbookEntry] = Field(default_factory=list)
    no_bids: List[OrderbookEntry] = Field(default_factory=list)
    no_asks: List[OrderbookEntry] = Field(default_factory=list)

    @property
    def best_yes_bid(self) -> Optional[float]:
        """Get best yes bid price."""
        return self.yes_bids[0].price if self.yes_bids else None

    @property
    def best_yes_ask(self) -> Optional[float]:
        """Get best yes ask price."""
        return self.yes_asks[0].price if self.yes_asks else None

    @property
    def best_no_bid(self) -> Optional[float]:
        """Get best no bid price."""
        return self.no_bids[0].price if self.no_bids else None

    @property
    def best_no_ask(self) -> Optional[float]:
        """Get best no ask price."""
        return self.no_asks[0].price if self.no_asks else None

    @property
    def yes_mid_price(self) -> Optional[float]:
        """Calculate yes mid price."""
        bid = self.best_yes_bid
        ask = self.best_yes_ask
        if bid and ask:
            return (bid + ask) / 2
        return bid or ask

    @property
    def no_mid_price(self) -> Optional[float]:
        """Calculate no mid price."""
        bid = self.best_no_bid
        ask = self.best_no_ask
        if bid and ask:
            return (bid + ask) / 2
        return bid or ask


class Position(BaseModel):
    """User position in a market."""

    market_ticker: str
    position: int
    resting_order_count: int
    total_cost: float


class Order(BaseModel):
    """Order details for placement or response."""

    order_id: Optional[str] = None
    ticker: str
    client_order_id: Optional[str] = None
    side: str  # "yes" or "no"
    action: str  # "buy" or "sell"
    count: int
    type: str = "limit"  # "limit" or "market"
    yes_price: Optional[int] = None  # in cents
    no_price: Optional[int] = None  # in cents
    expiration_ts: Optional[int] = None
    sell_position_floor: Optional[int] = None
    buy_max_cost: Optional[int] = None
    status: Optional[str] = None
    created_time: Optional[datetime] = None

    class Config:
        populate_by_name = True


class OrderRequest(BaseModel):
    """Request to place an order."""

    ticker: str
    client_order_id: Optional[str] = None
    side: str  # "yes" or "no"
    action: str  # "buy" or "sell"
    count: int
    type: str = "limit"
    yes_price: Optional[int] = None  # in cents
    no_price: Optional[int] = None  # in cents


class Event(BaseModel):
    """Kalshi event details."""

    event_ticker: str = Field(..., alias="event_ticker")
    title: str
    category: Optional[str] = None
    series_ticker: Optional[str] = None
    sub_title: Optional[str] = None
    mutually_exclusive: Optional[bool] = None
    status: Optional[str] = None
    strike_date: Optional[datetime] = None

    class Config:
        populate_by_name = True


class GetEventsResponse(BaseModel):
    """Response from GET /events endpoint with pagination."""

    events: List[Event]
    cursor: Optional[str] = None

    @property
    def has_more_pages(self) -> bool:
        """Check if there are more pages to fetch."""
        return bool(self.cursor)


class GetMarketsResponse(BaseModel):
    """Response from GET /markets endpoint with pagination."""

    markets: List[Market]
    cursor: Optional[str] = None

    @property
    def has_more_pages(self) -> bool:
        """Check if there are more pages to fetch."""
        return bool(self.cursor)
