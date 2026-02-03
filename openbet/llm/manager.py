"""LLM provider manager for orchestrating multiple providers."""

import asyncio
from typing import Dict, List, Optional

from openbet.llm.claude import ClaudeProvider
from openbet.llm.gemini import GeminiProvider
from openbet.llm.grok import GrokProvider
from openbet.llm.models import LLMAnalysisResponse, MarketContext
from openbet.llm.openai import OpenAIProvider


class LLMManager:
    """Manages multiple LLM providers for market analysis."""

    def __init__(
        self,
        use_claude: bool = True,
        use_openai: bool = True,
        use_grok: bool = True,
        use_gemini: bool = True,
    ):
        """Initialize LLM manager.

        Args:
            use_claude: Enable Claude provider
            use_openai: Enable OpenAI provider
            use_grok: Enable Grok provider
            use_gemini: Enable Gemini provider
        """
        self.providers = {}

        if use_claude:
            try:
                self.providers["claude"] = ClaudeProvider()
            except Exception as e:
                print(f"Warning: Failed to initialize Claude provider: {e}")

        if use_openai:
            try:
                self.providers["openai"] = OpenAIProvider()
            except Exception as e:
                print(f"Warning: Failed to initialize OpenAI provider: {e}")

        if use_grok:
            try:
                self.providers["grok"] = GrokProvider()
            except Exception as e:
                print(f"Warning: Failed to initialize Grok provider: {e}")

        if use_gemini:
            try:
                self.providers["gemini"] = GeminiProvider()
            except Exception as e:
                print(f"Warning: Failed to initialize Gemini provider: {e}")

        if not self.providers:
            raise Exception("No LLM providers available")

    def get_available_providers(self) -> List[str]:
        """Get list of available provider names.

        Returns:
            List of provider names
        """
        return list(self.providers.keys())

    async def analyze_with_all_providers(
        self, context: MarketContext
    ) -> Dict[str, Optional[LLMAnalysisResponse]]:
        """Analyze market with all available providers in parallel.

        Args:
            context: Market context information

        Returns:
            Dictionary mapping provider names to their responses
            (None if provider failed)
        """
        tasks = {}
        for name, provider in self.providers.items():
            tasks[name] = asyncio.create_task(self._safe_analyze(name, provider, context))

        # Wait for all tasks to complete
        results = await asyncio.gather(*tasks.values())

        # Map results back to provider names
        return dict(zip(tasks.keys(), results))

    async def _safe_analyze(
        self, name: str, provider, context: MarketContext
    ) -> Optional[LLMAnalysisResponse]:
        """Safely analyze market with a provider, catching exceptions.

        Args:
            name: Provider name
            provider: Provider instance
            context: Market context

        Returns:
            Analysis response or None if failed
        """
        try:
            return await provider.analyze_market(context)
        except Exception as e:
            print(f"Warning: {name} provider failed: {e}")
            return None

    async def analyze_with_provider(
        self, provider_name: str, context: MarketContext
    ) -> LLMAnalysisResponse:
        """Analyze market with a specific provider.

        Args:
            provider_name: Name of provider to use
            context: Market context information

        Returns:
            Analysis response

        Raises:
            ValueError: If provider not found
            Exception: If analysis fails
        """
        if provider_name not in self.providers:
            raise ValueError(f"Provider '{provider_name}' not available")

        provider = self.providers[provider_name]
        return await provider.analyze_market(context)
