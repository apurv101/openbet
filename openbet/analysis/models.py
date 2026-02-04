"""Models for analysis results."""

from typing import Any, Dict, Optional

from pydantic import BaseModel


class ConsensusResult(BaseModel):
    """Consensus result from multiple LLM providers."""

    yes_confidence: float
    no_confidence: float
    method: str = "simple_average"
    provider_count: int
    provider_responses: Dict[str, Optional[Dict[str, Any]]]

    # Fields for iterative reasoning
    rounds_completed: Optional[int] = None
    round_1_responses: Optional[Dict[str, Any]] = None
    convergence_metrics: Optional[Dict[str, Any]] = None


class AnalysisResult(BaseModel):
    """Complete analysis result for a market."""

    market_id: str
    option: str
    analysis_id: int

    # Individual provider responses
    claude_response: Optional[Dict[str, Any]] = None
    openai_response: Optional[Dict[str, Any]] = None
    grok_response: Optional[Dict[str, Any]] = None

    # Market context at time of analysis
    yes_price: Optional[float] = None
    no_price: Optional[float] = None
    volume_24h: Optional[float] = None
    liquidity_depth: Optional[float] = None

    # Consensus results
    consensus_yes_confidence: float
    consensus_no_confidence: float
    consensus_method: str

    # Reference to previous analysis
    previous_analysis_id: Optional[int] = None
