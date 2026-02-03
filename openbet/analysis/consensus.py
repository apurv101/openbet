"""Consensus calculation logic for combining LLM provider outputs."""

from typing import Dict, List, Optional

from openbet.analysis.models import ConsensusResult
from openbet.llm.models import LLMAnalysisResponse


def calculate_simple_average_consensus(
    responses: Dict[str, Optional[LLMAnalysisResponse]]
) -> ConsensusResult:
    """Calculate consensus using simple average of confidence scores.

    Args:
        responses: Dictionary mapping provider names to their responses
                  (None if provider failed)

    Returns:
        Consensus result with averaged confidence scores

    Raises:
        ValueError: If no valid responses available
    """
    # Filter out failed responses
    valid_responses = {
        name: resp for name, resp in responses.items() if resp is not None
    }

    if not valid_responses:
        raise ValueError("No valid responses from LLM providers")

    # Calculate averages
    yes_scores = [resp.yes_confidence for resp in valid_responses.values()]
    no_scores = [resp.no_confidence for resp in valid_responses.values()]

    yes_average = sum(yes_scores) / len(yes_scores)
    no_average = sum(no_scores) / len(no_scores)

    # Convert responses to dictionaries for storage
    provider_responses = {
        name: resp.model_dump() if resp else None
        for name, resp in responses.items()
    }

    return ConsensusResult(
        yes_confidence=yes_average,
        no_confidence=no_average,
        method="simple_average",
        provider_count=len(valid_responses),
        provider_responses=provider_responses,
    )


def calculate_weighted_average_consensus(
    responses: Dict[str, Optional[LLMAnalysisResponse]],
    weights: Dict[str, float],
) -> ConsensusResult:
    """Calculate consensus using weighted average of confidence scores.

    Args:
        responses: Dictionary mapping provider names to their responses
        weights: Dictionary mapping provider names to their weights

    Returns:
        Consensus result with weighted averaged confidence scores

    Raises:
        ValueError: If no valid responses or invalid weights
    """
    # Filter out failed responses
    valid_responses = {
        name: resp for name, resp in responses.items() if resp is not None
    }

    if not valid_responses:
        raise ValueError("No valid responses from LLM providers")

    # Calculate weighted averages
    total_weight = sum(weights.get(name, 1.0) for name in valid_responses.keys())

    if total_weight == 0:
        raise ValueError("Total weight is zero")

    yes_weighted = sum(
        resp.yes_confidence * weights.get(name, 1.0)
        for name, resp in valid_responses.items()
    )
    no_weighted = sum(
        resp.no_confidence * weights.get(name, 1.0)
        for name, resp in valid_responses.items()
    )

    yes_average = yes_weighted / total_weight
    no_average = no_weighted / total_weight

    # Convert responses to dictionaries for storage
    provider_responses = {
        name: resp.model_dump() if resp else None
        for name, resp in responses.items()
    }

    return ConsensusResult(
        yes_confidence=yes_average,
        no_confidence=no_average,
        method="weighted_average",
        provider_count=len(valid_responses),
        provider_responses=provider_responses,
    )


def calculate_consensus(
    responses: Dict[str, Optional[LLMAnalysisResponse]],
    method: str = "simple_average",
    weights: Optional[Dict[str, float]] = None,
) -> ConsensusResult:
    """Calculate consensus using specified method.

    Args:
        responses: Dictionary mapping provider names to their responses
        method: Consensus method ("simple_average" or "weighted_average")
        weights: Weights for weighted average (required if method is "weighted_average")

    Returns:
        Consensus result

    Raises:
        ValueError: If invalid method or missing weights
    """
    if method == "simple_average":
        return calculate_simple_average_consensus(responses)
    elif method == "weighted_average":
        if weights is None:
            raise ValueError("Weights required for weighted_average method")
        return calculate_weighted_average_consensus(responses, weights)
    else:
        raise ValueError(f"Unknown consensus method: {method}")
