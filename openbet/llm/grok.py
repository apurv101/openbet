"""Grok (xAI) LLM provider implementation."""

import json
from typing import Optional

from openai import AsyncOpenAI

from openbet.config import get_settings
from openbet.llm.base import BaseLLMProvider
from openbet.llm.models import LLMAnalysisResponse, MarketContext


class GrokProvider(BaseLLMProvider):
    """Grok (xAI) provider for market analysis."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        """Initialize Grok provider.

        Args:
            api_key: xAI API key. If None, uses config value.
            model: Model to use. If None, uses config value.
        """
        settings = get_settings()
        api_key = api_key or settings.xai_api_key
        model = model or settings.default_llm_model_grok

        super().__init__(api_key, model)

        # xAI uses OpenAI-compatible API
        self.client = AsyncOpenAI(
            api_key=self.api_key,
            base_url="https://api.x.ai/v1",
        )

    async def analyze_market(self, context: MarketContext) -> LLMAnalysisResponse:
        """Analyze market using Grok.

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
                max_tokens=1024,
            )

            # Extract response text
            response_text = response.choices[0].message.content

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
                provider="grok",
            )

        except json.JSONDecodeError as e:
            raise Exception(f"Failed to parse Grok response as JSON: {str(e)}")
        except KeyError as e:
            raise Exception(f"Missing required field in Grok response: {str(e)}")
        except Exception as e:
            raise Exception(f"Grok API error: {str(e)}")

    async def analyze_custom_prompt(self, prompt: str) -> str:
        """Analyze with custom prompt, return raw text response.

        Args:
            prompt: Custom prompt string

        Returns:
            Raw response text from Grok

        Raises:
            Exception: If API call fails
        """
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=2048,
            )

            # Extract and return raw response text
            response_text = response.choices[0].message.content

            # Try to extract JSON from markdown code blocks if present
            if "```json" in response_text:
                json_start = response_text.find("```json") + 7
                json_end = response_text.find("```", json_start)
                return response_text[json_start:json_end].strip()
            elif "```" in response_text:
                json_start = response_text.find("```") + 3
                json_end = response_text.find("```", json_start)
                return response_text[json_start:json_end].strip()

            return response_text

        except Exception as e:
            raise Exception(f"Grok API error: {str(e)}")
