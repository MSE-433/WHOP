"""Provider-agnostic LLM wrapper.

Supports Ollama, llama.cpp, vLLM, Claude (Anthropic), and OpenAI.
All errors are wrapped in LLMClientError for uniform handling.
"""

import re
from dataclasses import dataclass

import httpx

from config import settings


def _strip_thinking(text: str) -> str:
    """Remove <think>...</think> blocks from reasoning model output."""
    return re.sub(r"<think>[\s\S]*?</think>\s*", "", text).strip()


class LLMClientError(Exception):
    """Raised when an LLM call fails for any reason."""
    pass


@dataclass
class LLMResponse:
    """Successful LLM completion result."""

    text: str
    provider: str
    model: str


class LLMClient:
    """Dispatches completion requests to the configured LLM provider."""

    def __init__(self):
        self._provider = settings.llm_provider.lower()

    def is_available(self) -> bool:
        """Check whether a usable LLM provider is configured."""
        return self._provider != "none"

    def complete(self, system_prompt: str, user_prompt: str) -> LLMResponse:
        """Send a completion request to the configured provider."""
        if not self.is_available():
            raise LLMClientError("No LLM provider configured (provider='none')")

        dispatch = {
            "ollama": self._complete_ollama,
            "llamacpp": self._complete_llamacpp,
            "vllm": self._complete_vllm,
            "claude": self._complete_claude,
            "openai": self._complete_openai,
        }

        handler = dispatch.get(self._provider)
        if handler is None:
            raise LLMClientError(f"Unknown LLM provider: {self._provider}")

        try:
            return handler(system_prompt, user_prompt)
        except LLMClientError:
            raise
        except Exception as e:
            raise LLMClientError(f"{self._provider} error: {e}") from e

    def chat(self, system_prompt: str, messages: list[dict]) -> LLMResponse:
        """Send a multi-turn chat request to the configured provider.

        Args:
            system_prompt: System-level instructions.
            messages: List of {"role": "user"|"assistant", "content": "..."} dicts.

        Returns:
            LLMResponse with the assistant's reply.
        """
        if not self.is_available():
            raise LLMClientError("No LLM provider configured (provider='none')")

        dispatch = {
            "ollama": self._chat_ollama,
            "llamacpp": self._chat_llamacpp,
            "vllm": self._chat_vllm,
            "claude": self._chat_claude,
            "openai": self._chat_openai,
        }

        handler = dispatch.get(self._provider)
        if handler is None:
            raise LLMClientError(f"Unknown LLM provider: {self._provider}")

        try:
            return handler(system_prompt, messages)
        except LLMClientError:
            raise
        except Exception as e:
            raise LLMClientError(f"{self._provider} error: {e}") from e

    # ── Provider implementations ─────────────────────────────────────────

    def _complete_ollama(self, system_prompt: str, user_prompt: str) -> LLMResponse:
        base_url = settings.ollama_base_url.rstrip("/")
        model = settings.ollama_model
        with httpx.Client(timeout=settings.llm_timeout_seconds) as client:
            r = client.post(
                f"{base_url}/api/chat",
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "stream": False,
                    "think": False,
                    "options": {
                        "temperature": settings.llm_temperature,
                        "num_predict": settings.llm_max_tokens,
                    },
                },
            )
            r.raise_for_status()
            data = r.json()
            text = _strip_thinking(data.get("message", {}).get("content", ""))
            return LLMResponse(text=text, provider="ollama", model=model)

    def _complete_llamacpp(self, system_prompt: str, user_prompt: str) -> LLMResponse:
        server_url = settings.llamacpp_server_url.rstrip("/")
        prompt = f"<|system|>\n{system_prompt}\n<|user|>\n{user_prompt}\n<|assistant|>\n"
        with httpx.Client(timeout=settings.llm_timeout_seconds) as client:
            r = client.post(
                f"{server_url}/completion",
                json={
                    "prompt": prompt,
                    "temperature": settings.llm_temperature,
                    "n_predict": settings.llm_max_tokens,
                    "stop": ["<|user|>", "<|system|>"],
                },
            )
            r.raise_for_status()
            data = r.json()
            text = _strip_thinking(data.get("content", ""))
            return LLMResponse(text=text, provider="llamacpp", model="local")

    def _complete_vllm(self, system_prompt: str, user_prompt: str) -> LLMResponse:
        server_url = settings.vllm_server_url.rstrip("/")
        model = settings.vllm_model
        with httpx.Client(timeout=settings.llm_timeout_seconds) as client:
            r = client.post(
                f"{server_url}/v1/chat/completions",
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "temperature": settings.llm_temperature,
                    "max_tokens": settings.llm_max_tokens,
                },
            )
            r.raise_for_status()
            data = r.json()
            text = data["choices"][0]["message"]["content"]
            return LLMResponse(text=text, provider="vllm", model=model)

    def _complete_claude(self, system_prompt: str, user_prompt: str) -> LLMResponse:
        try:
            import anthropic
        except ImportError:
            raise LLMClientError("anthropic package not installed (pip install anthropic)")

        api_key = settings.anthropic_api_key
        if not api_key:
            raise LLMClientError("WHOP_ANTHROPIC_API_KEY not set")

        model = settings.anthropic_model
        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model=model,
            max_tokens=settings.llm_max_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
            temperature=settings.llm_temperature,
        )
        text = message.content[0].text
        return LLMResponse(text=text, provider="claude", model=model)

    def _complete_openai(self, system_prompt: str, user_prompt: str) -> LLMResponse:
        try:
            import openai
        except ImportError:
            raise LLMClientError("openai package not installed (pip install openai)")

        api_key = settings.openai_api_key
        if not api_key:
            raise LLMClientError("WHOP_OPENAI_API_KEY not set")

        model = settings.openai_model
        client = openai.OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=settings.llm_temperature,
            max_tokens=settings.llm_max_tokens,
        )
        text = response.choices[0].message.content
        return LLMResponse(text=text, provider="openai", model=model)

    # ── Multi-turn chat implementations ───────────────────────────────────

    def _chat_ollama(self, system_prompt: str, messages: list[dict]) -> LLMResponse:
        base_url = settings.ollama_base_url.rstrip("/")
        model = settings.ollama_model
        all_messages = [{"role": "system", "content": system_prompt}] + messages
        with httpx.Client(timeout=settings.llm_timeout_seconds) as client:
            r = client.post(
                f"{base_url}/api/chat",
                json={
                    "model": model,
                    "messages": all_messages,
                    "stream": False,
                    "think": False,
                    "options": {
                        "temperature": settings.llm_temperature,
                        "num_predict": settings.llm_max_tokens,
                    },
                },
            )
            r.raise_for_status()
            data = r.json()
            text = _strip_thinking(data.get("message", {}).get("content", ""))
            return LLMResponse(text=text, provider="ollama", model=model)

    def _chat_llamacpp(self, system_prompt: str, messages: list[dict]) -> LLMResponse:
        server_url = settings.llamacpp_server_url.rstrip("/")
        parts = [f"<|system|>\n{system_prompt}"]
        for msg in messages:
            parts.append(f"<|{msg['role']}|>\n{msg['content']}")
        parts.append("<|assistant|>\n")
        prompt = "\n".join(parts)
        with httpx.Client(timeout=settings.llm_timeout_seconds) as client:
            r = client.post(
                f"{server_url}/completion",
                json={
                    "prompt": prompt,
                    "temperature": settings.llm_temperature,
                    "n_predict": settings.llm_max_tokens,
                    "stop": ["<|user|>", "<|system|>"],
                },
            )
            r.raise_for_status()
            data = r.json()
            text = data.get("content", "")
            return LLMResponse(text=text, provider="llamacpp", model="local")

    def _chat_vllm(self, system_prompt: str, messages: list[dict]) -> LLMResponse:
        server_url = settings.vllm_server_url.rstrip("/")
        model = settings.vllm_model
        all_messages = [{"role": "system", "content": system_prompt}] + messages
        with httpx.Client(timeout=settings.llm_timeout_seconds) as client:
            r = client.post(
                f"{server_url}/v1/chat/completions",
                json={
                    "model": model,
                    "messages": all_messages,
                    "temperature": settings.llm_temperature,
                    "max_tokens": settings.llm_max_tokens,
                },
            )
            r.raise_for_status()
            data = r.json()
            text = data["choices"][0]["message"]["content"]
            return LLMResponse(text=text, provider="vllm", model=model)

    def _chat_claude(self, system_prompt: str, messages: list[dict]) -> LLMResponse:
        try:
            import anthropic
        except ImportError:
            raise LLMClientError("anthropic package not installed (pip install anthropic)")

        api_key = settings.anthropic_api_key
        if not api_key:
            raise LLMClientError("WHOP_ANTHROPIC_API_KEY not set")

        model = settings.anthropic_model
        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model=model,
            max_tokens=settings.llm_max_tokens,
            system=system_prompt,
            messages=messages,
            temperature=settings.llm_temperature,
        )
        text = message.content[0].text
        return LLMResponse(text=text, provider="claude", model=model)

    def _chat_openai(self, system_prompt: str, messages: list[dict]) -> LLMResponse:
        try:
            import openai
        except ImportError:
            raise LLMClientError("openai package not installed (pip install openai)")

        api_key = settings.openai_api_key
        if not api_key:
            raise LLMClientError("WHOP_OPENAI_API_KEY not set")

        model = settings.openai_model
        all_messages = [{"role": "system", "content": system_prompt}] + messages
        client = openai.OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model=model,
            messages=all_messages,
            temperature=settings.llm_temperature,
            max_tokens=settings.llm_max_tokens,
        )
        text = response.choices[0].message.content
        return LLMResponse(text=text, provider="openai", model=model)
