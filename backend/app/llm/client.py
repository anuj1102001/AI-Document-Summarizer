"""LLM access behind a small interface.

Every call asks for structured output validated against a Pydantic model, records token usage and latency, retries
transient failures with backoff, and maps provider errors to user-safe messages. Tests use FakeLLM, so the whole API
can be exercised without a key or network.
"""

import re
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol, TypeVar

from pydantic import BaseModel, ValidationError

from app.config import Settings
from app.errors import AppError
from app.logging_setup import get_logger

log = get_logger(__name__)
T = TypeVar("T", bound=BaseModel)


@dataclass
class Usage:
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: int = 0


class LLM(Protocol):
    configured: bool
    model: str

    def generate(
        self, *, system: str, prompt: str, schema: type[T], temperature: float = 0.1, max_output_tokens: int = 4096
    ) -> tuple[T, Usage]: ...


def _retry_after(err: Exception) -> float | None:
    """Seconds the provider asked us to wait on a 429, if it said."""
    m = re.search(r"retry in ([\d.]+)s", str(err)) or re.search(r"'retryDelay': '(\d+)s'", str(err))
    return float(m.group(1)) + 1 if m else None


class NotConfiguredLLM:
    configured = False
    model = "none"

    def generate(self, **_) -> tuple[BaseModel, Usage]:
        raise AppError("AI features are switched off because no GEMINI_API_KEY is set on the server.", 503, "AI_NOT_CONFIGURED")


class GeminiLLM:
    configured = True

    def __init__(self, api_key: str, model: str, timeout_s: float, max_retries: int):
        from google import genai
        from google.genai import types

        self._types = types
        self._client = genai.Client(api_key=api_key, http_options=types.HttpOptions(timeout=int(timeout_s * 1000)))
        self.model = model
        self._max_retries = max_retries

    def generate(
        self, *, system: str, prompt: str, schema: type[T], temperature: float = 0.1, max_output_tokens: int = 4096
    ) -> tuple[T, Usage]:
        from google.genai import errors as gerr

        config = self._types.GenerateContentConfig(
            system_instruction=system,
            temperature=temperature,
            max_output_tokens=max_output_tokens,
            response_mime_type="application/json",
            response_schema=schema,
        )
        attempt = 0
        while True:
            started = time.perf_counter()
            try:
                resp = self._client.models.generate_content(model=self.model, contents=prompt, config=config)
                latency = int((time.perf_counter() - started) * 1000)
                um = resp.usage_metadata
                usage = Usage(self.model, getattr(um, "prompt_token_count", 0) or 0, getattr(um, "candidates_token_count", 0) or 0, latency)
                parsed = resp.parsed if isinstance(resp.parsed, schema) else schema.model_validate_json(resp.text or "")
                log.info(
                    "llm_call",
                    extra={
                        "model": self.model,
                        "schema": schema.__name__,
                        "in_tokens": usage.input_tokens,
                        "out_tokens": usage.output_tokens,
                        "latency_ms": latency,
                    },
                )
                return parsed, usage
            except ValidationError:
                if attempt < self._max_retries:
                    attempt += 1
                    continue
                raise AppError("The AI returned an answer in an unexpected format. Please try again.", 502, "AI_BAD_OUTPUT") from None
            except gerr.ClientError as e:
                if e.code == 429 and attempt < self._max_retries:
                    attempt += 1
                    # Free-tier quotas are per minute and Google says how long to wait ("Please retry in 42.8s").
                    time.sleep(min(_retry_after(e) or 2**attempt, 60))
                    continue
                if e.code in (401, 403):
                    raise AppError(
                        "The server's AI key was rejected. The site owner needs to update it.", 503, "AI_NOT_CONFIGURED"
                    ) from None
                if e.code == 429:
                    raise AppError(
                        "The AI provider is rate-limiting requests. Please try again in a minute.", 429, "AI_RATE_LIMITED"
                    ) from None
                raise AppError("The AI provider rejected this request.", 502, "AI_ERROR") from None
            except gerr.ServerError:
                if attempt < self._max_retries:
                    attempt += 1
                    time.sleep(5 * attempt)  # 503s are usually "model overloaded"; give it a moment
                    continue
                raise AppError("The AI provider is having problems. Please try again shortly.", 502, "AI_UNAVAILABLE") from None


class FakeLLM:
    """Test double: a function decides the response for each (schema, prompt)."""

    configured = True
    model = "fake"

    def __init__(self, respond: Callable[[type[BaseModel], str], BaseModel]):
        self._respond = respond
        self.calls: list[tuple[str, str]] = []

    def generate(
        self, *, system: str, prompt: str, schema: type[T], temperature: float = 0.1, max_output_tokens: int = 4096
    ) -> tuple[T, Usage]:
        self.calls.append((schema.__name__, prompt))
        result = self._respond(schema, prompt)
        return schema.model_validate(result.model_dump()), Usage("fake", len(prompt) // 4, 50, 1)


def build_llm(settings: Settings) -> LLM:
    if settings.llm_provider == "offline-demo":
        from app.llm.offline import OfflineDemoLLM

        return OfflineDemoLLM()
    if not settings.gemini_api_key:
        return NotConfiguredLLM()
    return GeminiLLM(settings.gemini_api_key, settings.gemini_model, settings.llm_timeout_s, settings.llm_max_retries)
