"""LLM providers for the Phantom generator.

Providers only turn a prompt into text. Their output is untrusted data: the
workflow parses it as a JSON plan and never evaluates it.
"""

from __future__ import annotations

import os
import re
import time
from abc import ABC, abstractmethod
from collections.abc import Callable

DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"


class ProviderError(RuntimeError):
    """Raised when a provider is unavailable or a request fails."""


_SECRET_PATTERNS = (
    re.compile(r"AIza[0-9A-Za-z_\-]{20,}"),
    re.compile(r"sk-[0-9A-Za-z_\-]{16,}"),
    re.compile(r"gh[pousr]_[0-9A-Za-z]{20,}"),
    re.compile(r"(?i)(api[_-]?key|token|secret|password)\s*[=:]\s*\S+"),
)


def redact(text: str, extra_secrets: tuple[str, ...] = ()) -> str:
    """Mask credentials in text destined for logs or error messages."""
    for secret in extra_secrets:
        if secret:
            text = text.replace(secret, "[REDACTED]")
    for pattern in _SECRET_PATTERNS:
        text = pattern.sub("[REDACTED]", text)
    return text


class LLMProvider(ABC):
    """Minimal text-in, text-out provider interface."""

    name = "provider"

    @abstractmethod
    def complete(self, prompt: str) -> str:
        """Return the model's text response for a prompt."""


class GeminiProvider(LLMProvider):
    """Google Gemini via the optional `google-genai` package."""

    name = "gemini"

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        timeout: float = 60.0,
    ) -> None:
        self.timeout = timeout
        key = api_key or os.environ.get("GEMINI_API_KEY")
        if not key:
            raise ProviderError("GEMINI_API_KEY is not set")
        self.api_key: str = key
        self.model = model or os.environ.get("PHANTOM_GEMINI_MODEL", DEFAULT_GEMINI_MODEL)

    def complete(self, prompt: str) -> str:
        try:
            from google import genai  # type: ignore
            from google.genai import types  # type: ignore
        except ImportError as exc:
            raise ProviderError(
                "google-genai is not installed; run: pip install 'phantom-lang[llm]'"
            ) from exc
        try:
            client = genai.Client(
                api_key=self.api_key,
                http_options=types.HttpOptions(timeout=int(self.timeout * 1000)),
            )
            response = client.models.generate_content(model=self.model, contents=prompt)
            return response.text or ""
        except Exception as exc:
            raise ProviderError(
                f"Gemini request failed: {redact(str(exc), (self.api_key,))}"
            ) from None


class StaticProvider(LLMProvider):
    """Returns a canned or computed response. Used for tests and offline runs."""

    name = "static"

    def __init__(self, response: str | Callable[[str], str]) -> None:
        self._response = response

    def complete(self, prompt: str) -> str:
        return self._response(prompt) if callable(self._response) else self._response


class RetryingProvider(LLMProvider):
    """Wraps a provider with bounded retries and exponential backoff."""

    def __init__(
        self,
        inner: LLMProvider,
        retries: int = 2,
        backoff: float = 1.0,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.inner = inner
        self.name = inner.name
        self.retries = max(0, min(retries, 5))
        self.backoff = backoff
        self._sleep = sleep

    def complete(self, prompt: str) -> str:
        last: ProviderError | None = None
        for attempt in range(self.retries + 1):
            try:
                return self.inner.complete(prompt)
            except ProviderError as exc:
                last = exc
                if attempt < self.retries:
                    self._sleep(self.backoff * (2**attempt))
        assert last is not None
        raise last


def get_provider(name: str = "gemini") -> LLMProvider:
    """Construct a provider by name."""
    if name == "gemini":
        return GeminiProvider()
    raise ProviderError(f"Unknown provider: '{name}'")
