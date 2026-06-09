from __future__ import annotations

import json
import urllib.error
import urllib.request
import time
from dataclasses import dataclass

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


class OfflineProvider(ChatProvider):
    name = "offline"

    def complete(self, messages: list[Message]) -> str:
        latest = messages[-1].content if messages else ""
        request = latest.split("User request:\n", 1)[-1].split("\n\n", 1)[0].strip()
        if request.lower() in {"hi", "hello", "hey"}:
            return "Hello. I am ready."
        return (
            "Offline mode: no model provider is active. I can still use local tools and repository context "
            "when the request needs it.\n\n"
            f"{latest}"
        )


class OpenAICompatibleProvider(ChatProvider):
    def __init__(self, name: str, base_url: str, api_key: str, model: str, extra_headers: dict[str, str] | None = None):
        self.name = name
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.extra_headers = extra_headers or {}

    def complete(self, messages: list[Message]) -> str:
        payload = {
            "model": self.model,
            "messages": [message.__dict__ for message in messages],
            "temperature": 0.2,
            "max_tokens": 900,
        }
        data = json.dumps(payload).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
            **self.extra_headers,
        }
        req = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=data,
            headers=headers,
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


def configured_providers(config: AgentConfig) -> list[ChatProvider]:
    providers: list[ChatProvider] = []
    if config.openrouter_api_key:
        providers.append(
            OpenAICompatibleProvider(
                "openrouter",
                "https://openrouter.ai/api/v1",
                config.openrouter_api_key,
                config.openrouter_model,
                {"HTTP-Referer": "http://127.0.0.1:8765", "X-Title": "OSS Agent Workbench"},
            )
        )
    if config.groq_api_key:
        providers.append(
            OpenAICompatibleProvider(
                "groq",
                "https://api.groq.com/openai/v1",
                config.groq_api_key,
                config.groq_model,
            )
        )
    providers.append(OpenAICompatibleProvider("local", config.local_base_url, "local", config.local_model))
    providers.append(OfflineProvider())
    order = [config.provider] + [provider.name for provider in providers if provider.name != config.provider]
    by_name = {provider.name: provider for provider in providers}
    return [by_name[name] for name in order if name in by_name]


def build_provider(config: AgentConfig) -> ChatProvider:
    return ProviderRouter(configured_providers(config))
