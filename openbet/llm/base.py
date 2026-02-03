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
