"""Consensus calculation logic for combining LLM provider outputs."""

from typing import Dict, List, Optional, TYPE_CHECKING

from openbet.analysis.models import ConsensusResult
from openbet.llm.models import LLMAnalysisResponse, MarketContext

if TYPE_CHECKING:
    from openbet.llm.manager import LLMManager


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


async def calculate_iterative_reasoning_consensus(
    round1_responses: Dict[str, Optional[LLMAnalysisResponse]],
    llm_manager: "LLMManager",
    context: MarketContext
) -> ConsensusResult:
    """Calculate consensus using iterative reasoning (two-round analysis).

    Args:
        round1_responses: Dictionary mapping provider names to their Round 1 responses
        llm_manager: LLM manager instance to call providers for Round 2
        context: Market context information

    Returns:
        Consensus result with Round 2 averaged confidence scores and both rounds stored

    Raises:
        ValueError: If no valid responses available in either round
    """
    # Filter successful Round 1 responses
    valid_round1 = {
        name: resp for name, resp in round1_responses.items() if resp is not None
    }

    if not valid_round1:
        raise ValueError("No valid responses from Round 1")

    # Call providers with peer feedback for Round 2
    round2_responses = await llm_manager.analyze_with_peer_feedback(
        context, round1_responses
    )

    # Filter successful Round 2 responses
    valid_round2 = {
        name: resp for name, resp in round2_responses.items() if resp is not None
    }

    # If no Round 2 responses, fall back to Round 1
    if not valid_round2:
        print("Warning: All Round 2 analyses failed, using Round 1 results")
        valid_round2 = valid_round1
        round2_responses = round1_responses

    # Calculate averages from Round 2
    yes_scores = [resp.yes_confidence for resp in valid_round2.values()]
    no_scores = [resp.no_confidence for resp in valid_round2.values()]

    yes_average = sum(yes_scores) / len(yes_scores)
    no_average = sum(no_scores) / len(no_scores)

    # Calculate convergence metrics
    convergence_metrics = {}
    yes_shifts = []
    no_shifts = []

    for name in valid_round2.keys():
        if name in valid_round1:
            r1_yes = valid_round1[name].yes_confidence
            r2_yes = valid_round2[name].yes_confidence
            r1_no = valid_round1[name].no_confidence
            r2_no = valid_round2[name].no_confidence

            yes_shift = r2_yes - r1_yes
            no_shift = r2_no - r1_no

            yes_shifts.append(yes_shift)
            no_shifts.append(no_shift)

    if yes_shifts:
        convergence_metrics["avg_yes_shift"] = sum(yes_shifts) / len(yes_shifts)
        convergence_metrics["avg_no_shift"] = sum(no_shifts) / len(no_shifts)
        convergence_metrics["max_yes_shift"] = max(abs(s) for s in yes_shifts)
        convergence_metrics["max_no_shift"] = max(abs(s) for s in no_shifts)

    # Store both rounds
    round_1_responses = {
        name: resp.model_dump() if resp else None
        for name, resp in round1_responses.items()
    }

    # Convert Round 2 responses to dictionaries for storage
    provider_responses = {
        name: resp.model_dump() if resp else None
        for name, resp in round2_responses.items()
    }

    return ConsensusResult(
        yes_confidence=yes_average,
        no_confidence=no_average,
        method="iterative_reasoning",
        provider_count=len(valid_round2),
        provider_responses=provider_responses,
        rounds_completed=2,
        round_1_responses=round_1_responses,
        convergence_metrics=convergence_metrics,
    )


async def calculate_consensus(
    responses: Dict[str, Optional[LLMAnalysisResponse]],
    method: str = "simple_average",
    weights: Optional[Dict[str, float]] = None,
    llm_manager: Optional["LLMManager"] = None,
    context: Optional[MarketContext] = None,
) -> ConsensusResult:
    """Calculate consensus using specified method.

    Args:
        responses: Dictionary mapping provider names to their responses
        method: Consensus method ("simple_average", "weighted_average", or "iterative_reasoning")
        weights: Weights for weighted average (required if method is "weighted_average")
        llm_manager: LLM manager instance (required if method is "iterative_reasoning")
        context: Market context (required if method is "iterative_reasoning")

    Returns:
        Consensus result

    Raises:
        ValueError: If invalid method or missing required parameters
    """
    if method == "simple_average":
        return calculate_simple_average_consensus(responses)
    elif method == "weighted_average":
        if weights is None:
            raise ValueError("Weights required for weighted_average method")
        return calculate_weighted_average_consensus(responses, weights)
    elif method == "iterative_reasoning":
        if llm_manager is None or context is None:
            raise ValueError("llm_manager and context required for iterative_reasoning method")
        return await calculate_iterative_reasoning_consensus(responses, llm_manager, context)
    else:
        raise ValueError(f"Unknown consensus method: {method}")
