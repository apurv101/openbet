"""Main analysis orchestrator."""

import asyncio
from typing import Dict, List, Optional

from openbet.analysis.consensus import calculate_consensus
from openbet.analysis.context_builder import ContextBuilder
from openbet.analysis.models import AnalysisResult
from openbet.database.repositories import AnalysisRepository, MarketRepository
from openbet.kalshi.client import KalshiClient
from openbet.llm.manager import LLMManager


class Analyzer:
    """Main orchestrator for market analysis."""

    def __init__(
        self,
        use_claude: bool = True,
        use_openai: bool = True,
        use_grok: bool = True,
        use_gemini: bool = True,
        consensus_method: str = "simple_average",
    ):
        """Initialize analyzer.

        Args:
            use_claude: Enable Claude provider
            use_openai: Enable OpenAI provider
            use_grok: Enable Grok provider
            use_gemini: Enable Gemini provider
            consensus_method: Method for calculating consensus
        """
        self.context_builder = ContextBuilder()
        self.llm_manager = LLMManager(
            use_claude=use_claude,
            use_openai=use_openai,
            use_grok=use_grok,
            use_gemini=use_gemini,
        )
        self.analysis_repo = AnalysisRepository()
        self.market_repo = MarketRepository()
        self.kalshi_client = KalshiClient()
        self.consensus_method = consensus_method

    def analyze_market(
        self, market_id: str, option: Optional[str] = None
    ) -> Dict:
        """Analyze a market and store results.

        Args:
            market_id: Market ticker to analyze
            option: Specific option to analyze (optional)

        Returns:
            Dictionary with analysis results

        Raises:
            ValueError: If market not found
            Exception: If analysis fails
        """
        # Use asyncio.run to execute the async method
        return asyncio.run(self._analyze_market_async(market_id, option))

    async def _analyze_market_async(
        self, market_id: str, option: Optional[str] = None
    ) -> Dict:
        """Async implementation of market analysis.

        Args:
            market_id: Market ticker to analyze
            option: Specific option to analyze

        Returns:
            Dictionary with analysis results
        """
        # Validate market exists
        if not self.market_repo.exists(market_id):
            raise ValueError(
                f"Market {market_id} not found. Use 'add-market' command first."
            )

        # Build context
        context = self.context_builder.build_context(market_id, option)

        # Get current prices and market data
        orderbook = self.kalshi_client.get_orderbook(market_id)
        kalshi_market = self.kalshi_client.get_market(market_id)

        # Get previous analysis ID for historical chain
        previous_analysis = self.analysis_repo.get_latest_by_market(
            market_id, option
        )
        previous_analysis_id = (
            previous_analysis["id"] if previous_analysis else None
        )

        # Call all LLM providers
        responses = await self.llm_manager.analyze_with_all_providers(context)

        # Calculate consensus
        consensus = calculate_consensus(responses, method=self.consensus_method)

        # Store results in database
        option_key = option or market_id

        analysis_id = self.analysis_repo.create(
            market_id=market_id,
            option=option_key,
            claude_response=(
                consensus.provider_responses.get("claude")
                if "claude" in consensus.provider_responses
                else None
            ),
            openai_response=(
                consensus.provider_responses.get("openai")
                if "openai" in consensus.provider_responses
                else None
            ),
            grok_response=(
                consensus.provider_responses.get("grok")
                if "grok" in consensus.provider_responses
                else None
            ),
            gemini_response=(
                consensus.provider_responses.get("gemini")
                if "gemini" in consensus.provider_responses
                else None
            ),
            yes_price=orderbook.yes_mid_price,
            no_price=orderbook.no_mid_price,
            volume_24h=float(kalshi_market.volume_24h or 0),
            liquidity_depth=(
                float(kalshi_market.liquidity) if kalshi_market.liquidity else None
            ),
            consensus_yes_confidence=consensus.yes_confidence,
            consensus_no_confidence=consensus.no_confidence,
            consensus_method=consensus.method,
            previous_analysis_id=previous_analysis_id,
        )

        # Return analysis result
        return {
            "analysis_id": analysis_id,
            "market_id": market_id,
            "option": option_key,
            "claude_response": consensus.provider_responses.get("claude"),
            "openai_response": consensus.provider_responses.get("openai"),
            "grok_response": consensus.provider_responses.get("grok"),
            "gemini_response": consensus.provider_responses.get("gemini"),
            "yes_price": orderbook.yes_mid_price,
            "no_price": orderbook.no_mid_price,
            "volume_24h": kalshi_market.volume_24h,
            "liquidity_depth": kalshi_market.liquidity,
            "consensus_yes_confidence": consensus.yes_confidence,
            "consensus_no_confidence": consensus.no_confidence,
            "consensus_method": consensus.method,
            "provider_count": consensus.provider_count,
        }

    def analyze_all_markets(self) -> List[Dict]:
        """Analyze all markets in database.

        Returns:
            List of analysis results
        """
        markets = self.market_repo.get_all()
        results = []

        for market in markets:
            try:
                result = self.analyze_market(market["id"])
                results.append(result)
            except Exception as e:
                print(f"Error analyzing market {market['id']}: {e}")
                continue

        return results
