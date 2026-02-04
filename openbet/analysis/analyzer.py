"""Main analysis orchestrator."""

import asyncio
from datetime import datetime, timedelta
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

    def _is_analysis_fresh(
        self, analysis: Optional[Dict], cache_hours: int = 24
    ) -> bool:
        """Check if analysis is fresh (within cache_hours).

        Args:
            analysis: Analysis dictionary with analysis_timestamp
            cache_hours: Number of hours to consider analysis fresh

        Returns:
            True if analysis is fresh, False otherwise
        """
        if not analysis or "analysis_timestamp" not in analysis:
            return False

        timestamp_str = analysis["analysis_timestamp"]
        try:
            # Parse timestamp - handle different formats
            if "T" in timestamp_str:
                analysis_time = datetime.fromisoformat(
                    timestamp_str.replace("Z", "+00:00")
                )
            else:
                analysis_time = datetime.strptime(
                    timestamp_str, "%Y-%m-%d %H:%M:%S"
                )

            # Make timezone-naive for comparison
            if analysis_time.tzinfo is not None:
                analysis_time = analysis_time.replace(tzinfo=None)

            age = datetime.utcnow() - analysis_time
            return age < timedelta(hours=cache_hours)
        except (ValueError, AttributeError):
            return False

    def analyze_market(
        self,
        market_id: str,
        option: Optional[str] = None,
        force: bool = False,
        cache_hours: int = 24,
    ) -> Dict:
        """Analyze a market and store results.

        Args:
            market_id: Market ticker to analyze
            option: Specific option to analyze (optional)
            force: If True, bypass cache and run fresh analysis
            cache_hours: Number of hours to cache results (default: 24)

        Returns:
            Dictionary with analysis results

        Raises:
            ValueError: If market not found
            Exception: If analysis fails
        """
        # Check for cached analysis unless force=True
        if not force:
            latest_analysis = self.analysis_repo.get_latest_by_market(
                market_id, option
            )
            if self._is_analysis_fresh(latest_analysis, cache_hours):
                # Return cached result with flag indicating it's from cache
                latest_analysis["from_cache"] = True
                return latest_analysis

        # Use asyncio.run to execute the async method
        result = asyncio.run(self._analyze_market_async(market_id, option))
        result["from_cache"] = False
        return result

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
        # Auto-add market if it doesn't exist
        if not self.market_repo.exists(market_id):
            # Fetch market from Kalshi and add to database
            try:
                kalshi_market = self.kalshi_client.get_market(market_id)
                self.market_repo.create(
                    market_id=kalshi_market.ticker,
                    title=kalshi_market.title,
                    close_time=str(kalshi_market.close_time) if kalshi_market.close_time else None,
                    status=kalshi_market.status,
                    category=kalshi_market.category,
                    min_tick_size=0.01,
                    max_tick_size=0.99,
                    metadata={
                        "subtitle": kalshi_market.subtitle,
                        "yes_sub_title": kalshi_market.yes_sub_title,
                        "no_sub_title": kalshi_market.no_sub_title,
                        "volume": kalshi_market.volume,
                        "open_interest": kalshi_market.open_interest,
                    },
                )
            except Exception as e:
                raise ValueError(
                    f"Market {market_id} not found on Kalshi: {str(e)}"
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
        consensus = await calculate_consensus(
            responses,
            method=self.consensus_method,
            llm_manager=self.llm_manager,
            context=context
        )

        # Store results in database
        option_key = option or market_id

        # Prepare metadata for iterative reasoning
        metadata = None
        if consensus.method == "iterative_reasoning":
            metadata = {
                "iterative_rounds": {
                    "round_1": consensus.round_1_responses,
                    "round_2": consensus.provider_responses,
                    "convergence_metrics": consensus.convergence_metrics,
                    "rounds_completed": consensus.rounds_completed
                }
            }

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
            metadata=metadata,
        )

        # Return analysis result
        result = {
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

        # Add iterative reasoning fields if applicable
        if consensus.method == "iterative_reasoning":
            result["rounds_completed"] = consensus.rounds_completed
            result["round_1_responses"] = consensus.round_1_responses
            result["convergence_metrics"] = consensus.convergence_metrics

        return result

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
