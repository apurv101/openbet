"""Pydantic models for arbitrage analysis."""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class DependencyContext(BaseModel):
    """Context for dependency detection analysis."""

    event_a_ticker: str
    event_a_title: str
    event_a_category: Optional[str] = None

    event_b_ticker: str
    event_b_title: str
    event_b_category: Optional[str] = None

    temporal_distance_days: Optional[float] = None
    same_series: bool = False
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def to_prompt_text(self) -> str:
        """Convert to prompt-friendly text."""
        text = f"Event A: {self.event_a_title} ({self.event_a_ticker})\n"
        if self.event_a_category:
            text += f"Category: {self.event_a_category}\n"

        text += f"\nEvent B: {self.event_b_title} ({self.event_b_ticker})\n"
        if self.event_b_category:
            text += f"Category: {self.event_b_category}\n"

        if self.same_series:
            text += "\nNote: Both events are in the same series.\n"

        return text


class MinimalDependencyContext(BaseModel):
    """Minimal context for fast screening - titles only."""

    event_a_ticker: str
    event_a_title: str
    event_b_ticker: str
    event_b_title: str

    def to_prompt_text(self) -> str:
        """Convert to prompt-friendly text."""
        return (
            f"Event A: {self.event_a_title} ({self.event_a_ticker})\n"
            f"Event B: {self.event_b_title} ({self.event_b_ticker})"
        )


class ScreeningResult(BaseModel):
    """Result from fast single-provider screening."""

    dependency_score: float = Field(..., ge=0.0, le=1.0)
    is_dependent: bool
    dependency_type: str
    reasoning: str
    provider: str = "grok"
    mode: str = "fast_screening"


class Constraint(BaseModel):
    """A single logical constraint between events."""

    constraint_type: str  # "implication", "mutual_exclusion", "conjunction"
    description: str
    formal_expression: Optional[str] = None
    confidence: float = Field(..., ge=0.0, le=1.0)


class DependencyAnalysisResponse(BaseModel):
    """Structured response from LLM for dependency detection."""

    dependency_score: float = Field(..., ge=0.0, le=1.0)
    is_dependent: bool
    dependency_type: str  # "causal", "correlated", "inverse", "independent"
    constraints: List[Constraint]
    reasoning: str
    provider: Optional[str] = None


class ConsensusResult(BaseModel):
    """Consensus from multiple LLM providers."""

    dependency_score: float
    is_dependent: bool
    dependency_type: str
    constraints: List[Constraint]
    provider_count: int
    provider_responses: Dict[str, Any]
    consensus_method: str
    rounds_completed: int
    round_1_responses: Optional[Dict[str, Any]] = None
    convergence_metrics: Optional[Dict[str, Any]] = None
