"""LLM provider abstraction with streaming support."""
from __future__ import annotations

import json
import time
import http.client
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Iterator

from .config import AgentConfig


@dataclass
class Message:
    role: str
    content: str


class ProviderError(RuntimeError):
    pass


class ChatProvider:
    name = "unknown"

    def complete(self, messages: list[Message]) -> str:
        raise NotImplementedError

    def stream(self, messages: list[Message]) -> Iterator[str]:
        """Stream tokens. Default wraps complete() and yields word by word."""
        response = self.complete(messages)
        for word in response.split(" "):
            yield word + " "


class OfflineProvider(ChatProvider):
    name = "offline"

    def complete(self, messages: list[Message]) -> str:
        latest = messages[-1].content if messages else ""
        request = latest.split("User request:\n", 1)[-1].split("\n\n", 1)[0].strip()
        if request.lower() in {"hi", "hello", "hey"}:
            return "Hello. I am ready."
        return "I need a working model provider to answer that fully. I can still help with local tools when your request needs them."

    def stream(self, messages: list[Message]) -> Iterator[str]:
        response = self.complete(messages)
        for word in response.split(" "):
            yield word + " "


class OpenAICompatibleProvider(ChatProvider):
    def __init__(
        self,
        name: str,
        base_url: str,
        api_key: str,
        model: str,
        max_tokens: int,
        extra_headers: dict[str, str] | None = None,
    ):
        self.name = name
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.max_tokens = max_tokens
        self.extra_headers = extra_headers or {}

    def _build_headers(self) -> dict[str, str]:
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
            **self.extra_headers,
        }

    def complete(self, messages: list[Message]) -> str:
        payload = {
            "model": self.model,
            "messages": [message.__dict__ for message in messages],
            "temperature": 0.2,
            "max_tokens": self.max_tokens,
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=data,
            headers=self._build_headers(),
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=90) as response:
                body = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise ProviderError(f"Provider HTTP {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise ProviderError(f"Provider connection failed: {exc}") from exc

        try:
            return body["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ProviderError(f"Unexpected provider response: {body}") from exc

    def stream(self, messages: list[Message]) -> Iterator[str]:
        """Stream tokens via OpenAI-compatible SSE endpoint.

        Args:
            messages: Conversation messages.

        Yields:
            Token strings as they arrive from the API.

        Raises:
            ProviderError: On HTTP or connection failure.
        """
        payload = {
            "model": self.model,
            "messages": [message.__dict__ for message in messages],
            "temperature": 0.2,
            "max_tokens": self.max_tokens,
            "stream": True,
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=data,
            headers=self._build_headers(),
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=120) as response:
                for raw_line in response:
                    line = raw_line.decode("utf-8", errors="replace").strip()
                    if not line.startswith("data:"):
                        continue
                    payload_str = line[5:].strip()
                    if payload_str == "[DONE]":
                        break
                    try:
                        chunk = json.loads(payload_str)
                        token = chunk["choices"][0]["delta"].get("content", "")
                        if token:
                            yield token
                    except (json.JSONDecodeError, KeyError, IndexError, TypeError):
                        continue
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise ProviderError(f"Stream HTTP {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise ProviderError(f"Stream connection failed: {exc}") from exc
        except (http.client.RemoteDisconnected, TimeoutError, OSError) as exc:
            raise ProviderError(f"Stream connection failed: {exc}") from exc


@dataclass(frozen=True)
class ProviderAttempt:
    provider: str
    ok: bool
    duration_ms: int
    error: str | None = None


@dataclass(frozen=True)
class ProviderResult:
    answer: str
    provider: str
    attempts: list[ProviderAttempt]
    fallback_used: bool
    error: str | None


class ProviderRouter(ChatProvider):
    def __init__(self, providers: list[ChatProvider]):
        self.providers = providers or [OfflineProvider()]
        self.name = self.providers[0].name

    def complete(self, messages: list[Message]) -> str:
        return self.complete_with_metadata(messages).answer

    def complete_with_metadata(self, messages: list[Message]) -> ProviderResult:
        attempts: list[ProviderAttempt] = []
        first_provider = self.providers[0].name
        last_error = None
        for provider in self.providers:
            started = time.perf_counter()
            try:
                answer = provider.complete(messages)
                attempts.append(
                    ProviderAttempt(provider.name, True, int((time.perf_counter() - started) * 1000))
                )
                return ProviderResult(
                    answer=answer,
                    provider=provider.name,
                    attempts=attempts,
                    fallback_used=provider.name != first_provider,
                    error=last_error,
                )
            except ProviderError as exc:
                last_error = str(exc)
                attempts.append(
                    ProviderAttempt(provider.name, False, int((time.perf_counter() - started) * 1000), str(exc))
                )
        offline = OfflineProvider()
        started = time.perf_counter()
        answer = offline.complete(messages)
        attempts.append(ProviderAttempt(offline.name, True, int((time.perf_counter() - started) * 1000)))
        return ProviderResult(
            answer=answer,
            provider=offline.name,
            attempts=attempts,
            fallback_used=True,
            error=last_error,
        )

    def stream(self, messages: list[Message]) -> Iterator[str]:
        """Stream tokens, falling back to next provider on connection failure.

        Args:
            messages: Conversation messages.

        Yields:
            Token strings from the first responsive provider.
        """
        for provider in self.providers:
            try:
                gen = provider.stream(messages)
                first = next(gen)
                yield first
                yield from gen
                return
            except (ProviderError, StopIteration):
                continue
        yield from OfflineProvider().stream(messages)

    def stream_with_metadata(self, messages: list[Message]) -> Iterator[dict[str, object]]:
        """Stream token events and finish with provider attempt metadata.

        Args:
            messages: Conversation messages.

        Yields:
            Token events followed by one metadata event containing provider,
            attempts, fallback_used, and error.
        """

        attempts: list[ProviderAttempt] = []
        first_provider = self.providers[0].name
        last_error = None
        for provider in self.providers:
            started = time.perf_counter()
            emitted = False
            try:
                for token in provider.stream(messages):
                    emitted = True
                    yield {"type": "token", "token": token}
                attempts.append(
                    ProviderAttempt(provider.name, True, int((time.perf_counter() - started) * 1000))
                )
                yield {
                    "type": "metadata",
                    "provider": provider.name,
                    "attempts": attempts,
                    "fallback_used": provider.name != first_provider,
                    "error": last_error,
                }
                return
            except ProviderError as exc:
                last_error = str(exc)
                attempts.append(
                    ProviderAttempt(provider.name, False, int((time.perf_counter() - started) * 1000), str(exc))
                )
                if emitted:
                    yield {"type": "token", "token": f"\n\nProvider stream failed: {exc}\n"}
                continue
        offline = OfflineProvider()
        started = time.perf_counter()
        for token in offline.stream(messages):
            yield {"type": "token", "token": token}
        attempts.append(ProviderAttempt(offline.name, True, int((time.perf_counter() - started) * 1000)))
        yield {
            "type": "metadata",
            "provider": offline.name,
            "attempts": attempts,
            "fallback_used": True,
            "error": last_error,
        }


def configured_providers(config: AgentConfig) -> list[ChatProvider]:
    providers: list[ChatProvider] = []
    if config.openrouter_api_key:
        providers.append(
            OpenAICompatibleProvider(
                "openrouter",
                "https://openrouter.ai/api/v1",
                config.openrouter_api_key,
                config.openrouter_model,
                config.provider_max_tokens,
                {"HTTP-Referer": "http://127.0.0.1:8765", "X-Title": "Midday Workbench"},
            )
        )
    if config.groq_api_key:
        providers.append(
            OpenAICompatibleProvider(
                "groq",
                "https://api.groq.com/openai/v1",
                config.groq_api_key,
                config.groq_model,
                config.provider_max_tokens,
            )
        )
    providers.append(
        OpenAICompatibleProvider("local", config.local_base_url, "local", config.local_model, config.provider_max_tokens)
    )
    providers.append(OfflineProvider())
    order = [config.provider] + [provider.name for provider in providers if provider.name != config.provider]
    by_name = {provider.name: provider for provider in providers}
    return [by_name[name] for name in order if name in by_name]


def provider_diagnostics(config: AgentConfig) -> dict[str, object]:
    """Return safe provider readiness metadata without exposing secrets."""

    providers = configured_providers(config)
    records = []
    for index, provider in enumerate(providers):
        record: dict[str, object] = {
            "name": provider.name,
            "order": index,
            "selected": index == 0,
            "configured": True,
            "kind": "remote" if provider.name in {"openrouter", "groq"} else "local" if provider.name == "local" else "offline",
        }
        if isinstance(provider, OpenAICompatibleProvider):
            record["model"] = provider.model
            record["base_url"] = provider.base_url
            record["output_limit"] = provider.max_tokens
            record["configured"] = provider.name == "local" or bool(provider.api_key)
        if provider.name == "offline":
            record["model"] = "offline-fallback"
            record["base_url"] = ""
        records.append(record)
    return {
        "selected_provider": providers[0].name if providers else "offline",
        "route": [provider.name for provider in providers],
        "providers": records,
        "remote_ready": any(record["kind"] == "remote" and record["configured"] for record in records),
    }


def build_provider(config: AgentConfig) -> ChatProvider:
    return ProviderRouter(configured_providers(config))
