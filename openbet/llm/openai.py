"""OpenAI LLM provider implementation."""

import json
from typing import Optional

from openai import AsyncOpenAI

from openbet.config import get_settings
from openbet.llm.base import BaseLLMProvider
from openbet.llm.models import LLMAnalysisResponse, MarketContext


class OpenAIProvider(BaseLLMProvider):
    """OpenAI provider for market analysis."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        """Initialize OpenAI provider.

        Args:
            api_key: OpenAI API key. If None, uses config value.
            model: Model to use. If None, uses config value.
        """
        settings = get_settings()
        api_key = api_key or settings.openai_api_key
        model = model or settings.default_llm_model_openai

        super().__init__(api_key, model)
        self.client = AsyncOpenAI(api_key=self.api_key)

    async def analyze_market(self, context: MarketContext) -> LLMAnalysisResponse:
        """Analyze market using OpenAI.

        Args:
            context: Market context information

        Returns:
            Analysis response with confidence scores

        Raises:
            Exception: If API call fails or response parsing fails
        """
        prompt = self._build_analysis_prompt(context)

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                max_completion_tokens=1024,
            )

            # Extract response text
            message = response.choices[0].message

            # Check for refusal
            if hasattr(message, 'refusal') and message.refusal:
                raise Exception(f"OpenAI refused to respond: {message.refusal}")

            response_text = message.content

            if not response_text:
                raise Exception(f"OpenAI returned empty response. Full response: {response}")

            # Parse JSON response
            data = json.loads(response_text)

            return LLMAnalysisResponse(
                yes_confidence=float(data["yes_confidence"]),
                no_confidence=float(data["no_confidence"]),
                reasoning=data["reasoning"],
                provider="openai",
            )

        except json.JSONDecodeError as e:
            raise Exception(f"Failed to parse OpenAI response as JSON: {str(e)}")
        except KeyError as e:
            raise Exception(f"Missing required field in OpenAI response: {str(e)}")
        except Exception as e:
            raise Exception(f"OpenAI API error: {str(e)}")
