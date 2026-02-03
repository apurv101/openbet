"""Claude (Anthropic) LLM provider implementation."""

import json
from typing import Optional

from anthropic import AsyncAnthropic

from openbet.config import get_settings
from openbet.llm.base import BaseLLMProvider
from openbet.llm.models import LLMAnalysisResponse, MarketContext


class ClaudeProvider(BaseLLMProvider):
    """Claude provider for market analysis."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        """Initialize Claude provider.

        Args:
            api_key: Anthropic API key. If None, uses config value.
            model: Model to use. If None, uses config value.
        """
        settings = get_settings()
        api_key = api_key or settings.anthropic_api_key
        model = model or settings.default_llm_model_claude

        super().__init__(api_key, model)
        self.client = AsyncAnthropic(api_key=self.api_key)

    async def analyze_market(self, context: MarketContext) -> LLMAnalysisResponse:
        """Analyze market using Claude.

        Args:
            context: Market context information

        Returns:
            Analysis response with confidence scores

        Raises:
            Exception: If API call fails or response parsing fails
        """
        prompt = self._build_analysis_prompt(context)

        try:
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}],
            )

            # Extract response text
            response_text = response.content[0].text

            # Parse JSON response
            # Try to extract JSON from markdown code blocks if present
            if "```json" in response_text:
                json_start = response_text.find("```json") + 7
                json_end = response_text.find("```", json_start)
                response_text = response_text[json_start:json_end].strip()
            elif "```" in response_text:
                json_start = response_text.find("```") + 3
                json_end = response_text.find("```", json_start)
                response_text = response_text[json_start:json_end].strip()

            data = json.loads(response_text)

            return LLMAnalysisResponse(
                yes_confidence=float(data["yes_confidence"]),
                no_confidence=float(data["no_confidence"]),
                reasoning=data["reasoning"],
                provider="claude",
            )

        except json.JSONDecodeError as e:
            raise Exception(f"Failed to parse Claude response as JSON: {str(e)}")
        except KeyError as e:
            raise Exception(f"Missing required field in Claude response: {str(e)}")
        except Exception as e:
            raise Exception(f"Claude API error: {str(e)}")
