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

            # Check if response was blocked by safety filters
            if hasattr(response, 'prompt_feedback') and response.prompt_feedback:
                if hasattr(response.prompt_feedback, 'block_reason'):
                    raise Exception(f"Gemini blocked response due to safety filters: {response.prompt_feedback.block_reason}")

            # Check if we have candidates
            if not hasattr(response, 'candidates') or not response.candidates:
                raise Exception(f"Gemini returned no candidates. Response: {response}")

            # Check if first candidate was blocked
            candidate = response.candidates[0]
            if hasattr(candidate, 'finish_reason') and candidate.finish_reason:
                # Check for safety or other blocks
                if 'SAFETY' in str(candidate.finish_reason):
                    raise Exception(f"Gemini candidate blocked by safety: {candidate.finish_reason}")

            # Extract response text
            response_text = response.text

            # Debug: Check if response is empty
            if not response_text or not response_text.strip():
                raise Exception(f"Gemini returned empty response. Full response object: {response}")

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

            # Debug: Log what we're trying to parse
            if not response_text.strip():
                raise Exception(f"Response text became empty after markdown extraction. Original: {response.text[:200]}")

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

    async def analyze_custom_prompt(self, prompt: str) -> str:
        """Analyze with custom prompt, return raw text response.

        Args:
            prompt: Custom prompt string

        Returns:
            Raw response text from Gemini

        Raises:
            Exception: If API call fails
        """
        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt
            )

            # Check if response was blocked by safety filters
            if hasattr(response, 'prompt_feedback') and response.prompt_feedback:
                if hasattr(response.prompt_feedback, 'block_reason'):
                    raise Exception(f"Gemini blocked response: {response.prompt_feedback.block_reason}")

            # Check if we have candidates
            if not hasattr(response, 'candidates') or not response.candidates:
                raise Exception(f"Gemini returned no candidates")

            # Check if first candidate was blocked
            candidate = response.candidates[0]
            if hasattr(candidate, 'finish_reason') and 'SAFETY' in str(candidate.finish_reason):
                raise Exception(f"Gemini candidate blocked: {candidate.finish_reason}")

            # Extract and return raw response text
            response_text = response.text

            if not response_text or not response_text.strip():
                raise Exception(f"Gemini returned empty response")

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
            raise Exception(f"Gemini API error: {str(e)}")
