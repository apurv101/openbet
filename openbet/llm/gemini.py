"""Gemini (Google) LLM provider implementation."""

import json
from typing import Optional

from google import genai

from openbet.config import get_settings
from openbet.llm.base import BaseLLMProvider
from openbet.llm.models import LLMAnalysisResponse, MarketContext


class GeminiProvider(BaseLLMProvider):
    """Gemini (Google) provider for market analysis."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        """Initialize Gemini provider.

        Args:
            api_key: Google API key. If None, uses config value.
            model: Model to use. If None, uses config value.
        """
        settings = get_settings()
        api_key = api_key or settings.google_api_key
        model = model or settings.default_llm_model_gemini

        super().__init__(api_key, model)

        # Configure the API
        self.client = genai.Client(api_key=self.api_key)

    async def analyze_market(self, context: MarketContext) -> LLMAnalysisResponse:
        """Analyze market using Gemini.

        Args:
            context: Market context information

        Returns:
            Analysis response with confidence scores

        Raises:
            Exception: If API call fails or response parsing fails
        """
        prompt = self._build_analysis_prompt(context)

        try:
            # Gemini API is synchronous, but we're in an async context
            # We'll call it directly since it's fast enough
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt
            )

            # Extract response text
            response_text = response.text

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
                provider="gemini",
            )

        except json.JSONDecodeError as e:
            raise Exception(f"Failed to parse Gemini response as JSON: {str(e)}")
        except KeyError as e:
            raise Exception(f"Missing required field in Gemini response: {str(e)}")
        except Exception as e:
            raise Exception(f"Gemini API error: {str(e)}")
