"""AI-based dependency detection using multi-provider LLM consensus."""

import asyncio
import json
from typing import Dict, List, Optional

from openbet.arbitrage.models import (
    Constraint,
    ConsensusResult,
    DependencyAnalysisResponse,
    DependencyContext,
    MinimalDependencyContext,
    ScreeningResult,
)
from openbet.llm.manager import LLMManager


class DependencyDetector:
    """Detects logical dependencies between events using LLM consensus."""

    def __init__(self, llm_manager: Optional[LLMManager] = None):
        """Initialize detector with LLM manager."""
        self.llm_manager = llm_manager or LLMManager()

    def _build_dependency_prompt(self, context: DependencyContext) -> str:
        """Build Round 1 prompt for dependency detection."""

        prompt = f"""You are an expert in prediction markets and logical reasoning.
Analyze if these two events are logically dependent.

{context.to_prompt_text()}

Two events are DEPENDENT if:
1. One event causally influences the other (causal dependency)
2. They are mutually exclusive (cannot both happen)
3. One event implies the other (logical implication)
4. They share underlying factors that correlate outcomes

Respond in JSON format:
{{
    "dependency_score": <0.0 to 1.0>,
    "is_dependent": <true/false>,
    "dependency_type": "causal|correlated|inverse|independent",
    "constraints": [
        {{
            "constraint_type": "implication|mutual_exclusion|conjunction",
            "description": "Clear explanation",
            "formal_expression": "A => B or A ∧ B = FALSE",
            "confidence": <0.0 to 1.0>
        }}
    ],
    "reasoning": "Detailed explanation of your analysis"
}}

Guidelines:
- dependency_score: 0.0 = completely independent, 1.0 = strongly dependent
- Only include is_dependent=true if dependency_score >= 0.5
- constraints: List ALL logical constraints you can identify
- Be conservative - only flag clear dependencies, not weak correlations
"""
        return prompt

    def _build_iterative_prompt(
        self,
        context: DependencyContext,
        peer_analyses: List[Dict],
        own_previous: Dict
    ) -> str:
        """Build Round 2 prompt with peer feedback."""

        peer_text = "\n\n".join([
            f"Analyst {chr(65+i)}:\n"
            f"- Dependency: {p['is_dependent']} (score: {p['dependency_score']:.2f})\n"
            f"- Type: {p['dependency_type']}\n"
            f"- Reasoning: {p['reasoning']}"
            for i, p in enumerate(peer_analyses)
        ])

        prompt = f"""You previously analyzed these events for dependencies.
Now review other analysts' perspectives and revise if needed.

{context.to_prompt_text()}

PEER ANALYSES:
{peer_text}

YOUR PREVIOUS ANALYSIS:
- Dependency: {own_previous['is_dependent']} (score: {own_previous['dependency_score']:.2f})
- Type: {own_previous['dependency_type']}
- Reasoning: {own_previous['reasoning']}

After considering peer feedback, provide your revised analysis.

Questions to consider:
- Did any analyst identify constraints you missed?
- Are there disagreements on dependency type? Which is most accurate?
- Should you adjust your confidence based on consensus or divergence?

IMPORTANT: Respond in this EXACT JSON format:
{{
    "dependency_score": <0.0 to 1.0>,
    "is_dependent": <true/false>,
    "dependency_type": "causal|correlated|inverse|independent",
    "constraints": [
        {{
            "constraint_type": "implication|mutual_exclusion|conjunction",
            "description": "Clear explanation",
            "formal_expression": "A => B or A ∧ B = FALSE",
            "confidence": <0.0 to 1.0>
        }}
    ],
    "reasoning": "Detailed explanation of your revised analysis"
}}
"""
        return prompt

    async def _analyze_with_provider(
        self,
        provider_name: str,
        prompt: str
    ) -> Optional[DependencyAnalysisResponse]:
        """Analyze with single provider."""
        try:
            provider = self.llm_manager.providers.get(provider_name)
            if not provider:
                return None

            # Call provider's custom prompt analysis
            response_text = await provider.analyze_custom_prompt(prompt)

            # Parse JSON response
            data = json.loads(response_text)

            # Convert to structured response
            return DependencyAnalysisResponse(
                dependency_score=data["dependency_score"],
                is_dependent=data["is_dependent"],
                dependency_type=data["dependency_type"],
                constraints=[Constraint(**c) for c in data["constraints"]],
                reasoning=data["reasoning"],
                provider=provider_name
            )

        except KeyError as e:
            print(f"Error with {provider_name}: Missing field {e} in response. LLM may not be following JSON format.")
            return None
        except json.JSONDecodeError as e:
            print(f"Error with {provider_name}: Invalid JSON response - {e}")
            return None
        except Exception as e:
            error_msg = str(e)
            # Provide helpful hints for common errors
            if "401" in error_msg or "API key" in error_msg:
                print(f"Error with {provider_name}: Authentication failed. Check your API key in .env")
            elif "429" in error_msg:
                print(f"Error with {provider_name}: Rate limit exceeded. Wait and try again.")
            else:
                print(f"Error with {provider_name}: {e}")
            return None

    async def analyze_dependency(
        self,
        event_a: Dict,
        event_b: Dict
    ) -> ConsensusResult:
        """Analyze dependency using two-round LLM consensus.

        Follows existing analysis pattern:
        - Round 1: All providers analyze independently
        - Round 2: Providers see peer feedback and revise
        - Calculate consensus from Round 2 results
        """

        # Build context
        context = DependencyContext(
            event_a_ticker=event_a["event_ticker"],
            event_a_title=event_a["title"],
            event_a_category=event_a.get("category"),
            event_b_ticker=event_b["event_ticker"],
            event_b_title=event_b["title"],
            event_b_category=event_b.get("category"),
            same_series=(event_a.get("series_ticker") == event_b.get("series_ticker"))
        )

        # Round 1: Independent analysis
        prompt_r1 = self._build_dependency_prompt(context)

        tasks = [
            self._analyze_with_provider(name, prompt_r1)
            for name in self.llm_manager.providers.keys()
        ]

        round1_results = await asyncio.gather(*tasks)

        # Map results back to provider names
        round1_responses = dict(zip(
            self.llm_manager.providers.keys(),
            round1_results
        ))

        # Filter successful responses
        valid_r1 = {
            name: resp for name, resp in round1_responses.items()
            if resp is not None
        }

        # Show Round 1 results
        failed_r1 = [name for name, resp in round1_responses.items() if resp is None]
        if failed_r1:
            print(f"  Round 1 failures: {', '.join(failed_r1)}")
        if valid_r1:
            print(f"  Round 1 successes: {', '.join(valid_r1.keys())}")

        if not valid_r1:
            raise ValueError(
                f"All providers failed in Round 1. Check API keys in .env:\n"
                f"  Failed: {', '.join(failed_r1)}\n"
                f"  Hint: Verify OPENAI_API_KEY, ANTHROPIC_API_KEY, GROK_API_KEY, GEMINI_API_KEY"
            )

        # Round 2: With peer feedback
        round2_responses = {}

        for provider_name, own_response in valid_r1.items():
            # Get peer responses (exclude self)
            peers = [
                resp.model_dump() for name, resp in valid_r1.items()
                if name != provider_name
            ]

            # Build iterative prompt
            prompt_r2 = self._build_iterative_prompt(
                context,
                peers,
                own_response.model_dump()
            )

            # Analyze with peer feedback
            round2_responses[provider_name] = await self._analyze_with_provider(
                provider_name,
                prompt_r2
            )

        # Filter Round 2 successes
        valid_r2 = {
            name: resp for name, resp in round2_responses.items()
            if resp is not None
        }

        # Show Round 2 results
        failed_r2 = [name for name in valid_r1.keys() if name not in valid_r2]
        if failed_r2:
            print(f"  Round 2 failures: {', '.join(failed_r2)}")
        if valid_r2:
            print(f"  Round 2 successes: {', '.join(valid_r2.keys())}")

        # Check if we have any valid Round 2 responses
        if not valid_r2:
            raise ValueError(
                f"All providers failed in Round 2. \n"
                f"  Round 1 succeeded: {', '.join(valid_r1.keys())}\n"
                f"  Round 2 failed: {', '.join(failed_r2)}\n"
                f"  This may indicate API rate limits or transient errors. Try again in a moment."
            )

        # Calculate consensus from Round 2
        scores = [r.dependency_score for r in valid_r2.values()]
        avg_score = sum(scores) / len(scores)

        # Aggregate constraints (unique by description)
        all_constraints = []
        seen_descriptions = set()

        for resp in valid_r2.values():
            for constraint in resp.constraints:
                if constraint.description not in seen_descriptions:
                    all_constraints.append(constraint)
                    seen_descriptions.add(constraint.description)

        # Determine consensus dependency type (majority vote)
        types = [r.dependency_type for r in valid_r2.values()]
        consensus_type = max(set(types), key=types.count) if types else "independent"

        # Calculate convergence metrics
        shifts = []
        for name in valid_r2.keys():
            if name in valid_r1:
                shift = abs(valid_r2[name].dependency_score - valid_r1[name].dependency_score)
                shifts.append(shift)

        convergence_metrics = {
            "avg_score_shift": sum(shifts) / len(shifts) if shifts else 0,
            "max_score_shift": max(shifts) if shifts else 0
        }

        return ConsensusResult(
            dependency_score=avg_score,
            is_dependent=avg_score >= 0.5,
            dependency_type=consensus_type,
            constraints=all_constraints,
            provider_count=len(valid_r2),
            provider_responses={
                name: resp.model_dump() for name, resp in valid_r2.items()
            },
            consensus_method="iterative_reasoning",
            rounds_completed=2,
            round_1_responses={
                name: resp.model_dump() for name, resp in valid_r1.items()
            },
            convergence_metrics=convergence_metrics
        )

    def _build_fast_screening_prompt(self, context: MinimalDependencyContext) -> str:
        """Build simplified prompt for fast title-only screening."""
        return f"""You are analyzing whether two prediction market events are likely dependent.

{context.to_prompt_text()}

Two events are DEPENDENT if one's outcome makes the other more or less likely.

Analyze based on TITLES ONLY and respond in JSON:
{{
    "dependency_score": <0.0 to 1.0>,
    "is_dependent": <true/false>,
    "dependency_type": "<causal|correlated|independent>",
    "constraints": [],
    "reasoning": "<brief explanation>"
}}

Be concise. Focus on obvious dependencies."""

    async def screen_dependency_fast(
        self,
        event_a: Dict,
        event_b: Dict,
    ) -> ScreeningResult:
        """Fast single-provider, title-only screening.

        Uses only event titles and a single LLM call with Grok.
        Much faster than full consensus analysis.

        Args:
            event_a: Event dictionary with 'event_ticker' and 'title'
            event_b: Event dictionary with 'event_ticker' and 'title'

        Returns:
            ScreeningResult with dependency assessment
        """
        # 1. Build minimal context (titles only)
        context = MinimalDependencyContext(
            event_a_ticker=event_a["event_ticker"],
            event_a_title=event_a["title"],
            event_b_ticker=event_b["event_ticker"],
            event_b_title=event_b["title"],
        )

        # 2. Build simplified prompt
        prompt = self._build_fast_screening_prompt(context)

        # 3. Call only Grok provider (single round)
        try:
            provider = self.llm_manager.providers.get("grok")
            if not provider:
                raise ValueError("Grok provider not available")

            response_text = await provider.analyze_custom_prompt(prompt)

            # Parse JSON response
            data = json.loads(response_text)

            return ScreeningResult(
                dependency_score=data["dependency_score"],
                is_dependent=data["is_dependent"],
                dependency_type=data["dependency_type"],
                reasoning=data["reasoning"],
                provider="grok",
                mode="fast_screening"
            )
        except Exception as e:
            # Return low-confidence result on failure
            return ScreeningResult(
                dependency_score=0.0,
                is_dependent=False,
                dependency_type="unknown",
                reasoning=f"Screening failed: {str(e)}",
                provider="grok",
                mode="fast_screening"
            )
