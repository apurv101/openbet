"""Base interface for LLM providers."""

from abc import ABC, abstractmethod
from typing import Dict, Any

from openbet.llm.models import LLMAnalysisResponse, MarketContext


class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers."""

    def __init__(self, api_key: str, model: str):
        """Initialize provider with API key and model name.

        Args:
            api_key: API key for the provider
            model: Model identifier to use
        """
        self.api_key = api_key
        self.model = model

    @abstractmethod
    async def analyze_market(self, context: MarketContext) -> LLMAnalysisResponse:
        """Analyze a market and return confidence scores.

        Args:
            context: Market context information

        Returns:
            Analysis response with confidence scores and reasoning

        Raises:
            Exception: If analysis fails
        """
        pass

    def _build_analysis_prompt(self, context: MarketContext) -> str:
        """Build prompt for market analysis.

        Args:
            context: Market context information

        Returns:
            Formatted prompt string
        """
        # Check if this is an iterative analysis (Round 2)
        if "peer_analyses" in context.metadata and "own_previous_response" in context.metadata:
            return self._build_iterative_analysis_prompt(
                context,
                context.metadata["peer_analyses"],
                context.metadata["own_previous_response"]
            )

        # Regular analysis prompt (Round 1)
        prompt = f"""You are an expert betting analyst. Analyze the following prediction market and provide confidence scores for YES and NO outcomes.

{context.to_prompt_text()}

Based on the above information, provide:
1. Your confidence score for YES (0.0 to 1.0)
2. Your confidence score for NO (0.0 to 1.0)
3. Your reasoning for these confidence scores

Consider:
- Current market prices and sentiment
- Any historical analysis trends
- Market metrics like volume and liquidity
- Time remaining until market close
- Current position (if any) and its implications

Respond in JSON format:
{{
    "yes_confidence": <float between 0 and 1>,
    "no_confidence": <float between 0 and 1>,
    "reasoning": "<your detailed reasoning>"
}}
"""
        return prompt

    def _build_iterative_analysis_prompt(
        self,
        context: MarketContext,
        peer_analyses: list[Dict[str, Any]],
        own_previous_response: Dict[str, Any]
    ) -> str:
        """Build prompt for iterative analysis with peer feedback.

        Args:
            context: Market context information
            peer_analyses: List of anonymized peer analyses from Round 1
                         Each dict has keys: analyst_id, yes_confidence, no_confidence, reasoning
            own_previous_response: Own Round 1 response with keys: yes_confidence, no_confidence, reasoning

        Returns:
            Formatted prompt string for Round 2 analysis
        """
        # Format peer analyses
        peer_sections = []
        for peer in peer_analyses:
            peer_section = f"""{peer['analyst_id']}: YES {peer['yes_confidence']*100:.1f}%, NO {peer['no_confidence']*100:.1f}%
Reasoning: {peer['reasoning']}
"""
            peer_sections.append(peer_section)

        peer_text = "\n".join(peer_sections)

        prompt = f"""You are an expert betting analyst. You previously analyzed this market along with other AI analysts.
Now you have the opportunity to revise your analysis after reviewing their reasoning.

{context.to_prompt_text()}

PEER ANALYSES FROM ROUND 1:
{peer_text}

YOUR PREVIOUS ANALYSIS:
YES {own_previous_response['yes_confidence']*100:.1f}%, NO {own_previous_response['no_confidence']*100:.1f}%
Reasoning: {own_previous_response['reasoning']}

After considering the other analysts' perspectives, provide your revised confidence scores.

Consider:
- What insights from other analyses are compelling?
- Where do you disagree with the consensus and why?
- Should you adjust your confidence based on new perspectives?
- Current market prices and sentiment
- Market metrics like volume and liquidity
- Time remaining until market close

Respond in JSON format:
{{
    "yes_confidence": <float between 0 and 1>,
    "no_confidence": <float between 0 and 1>,
    "reasoning": "<your revised reasoning, explaining any changes or why you maintained your position>"
}}
"""
        return prompt
