"""
Fallback Gemini Model
========================
Wraps ADK's Gemini model to automatically retry against a different Gemini
model when the current one is unavailable - overloaded, rate-limited,
deprecated, or over quota. Google retires/renames Gemini models fairly
often and free-tier quota is per-model, so trying several models in order
both survives model deprecation AND spreads load across separate quota
pools instead of hammering one model's limit.
"""

from google.adk.models.google_llm import Gemini
from google.genai import errors as genai_errors

DEFAULT_FALLBACK_MODELS = [
    "gemini-3.6-flash",
    "gemini-3.5-flash",
    "gemini-3.7-flash",
    "gemini-flash-latest",
]


class FallbackGemini(Gemini):
    """Drop-in replacement for a plain model-name string. Tries each model
    in `models` in order; on ANY Gemini API error (overload, rate limit,
    quota, deprecated model, etc.) moves to the next one instead of
    failing the whole agent run. Only raises once every candidate in the
    list has failed."""

    def __init__(self, models: list[str] | None = None, **kwargs):
        models = models or DEFAULT_FALLBACK_MODELS
        super().__init__(model=models[0], **kwargs)
        object.__setattr__(self, "_fallback_models", models)

    async def generate_content_async(self, llm_request, stream: bool = False):
        last_error = None
        for candidate in self._fallback_models:
            self.model = candidate
            try:
                async for response in super().generate_content_async(llm_request, stream=stream):
                    yield response
                return
            except (genai_errors.ServerError, genai_errors.ClientError) as e:
                last_error = e
                continue
        if last_error:
            raise last_error
