"""
LLM Client for OpenFinance.

Provides unified interface for LLM operations with Qwen support.
"""

import json
import logging
import os
from typing import Any, AsyncIterator

logger = logging.getLogger(__name__)


class LLMClient:
    """Unified LLM client supporting OpenAI-compatible APIs."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
    ) -> None:
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        self.base_url = base_url or os.environ.get("OPENAI_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
        self.model = model or os.environ.get("LLM_MODEL", "qwen-max")
        self._client = None

    def _get_client(self) -> Any:
        """Get OpenAI client (lazy initialization)."""
        if self._client is None:
            try:
                import openai
                self._client = openai.OpenAI(
                    api_key=self.api_key,
                    base_url=self.base_url,
                )
            except ImportError:
                logger.warning("OpenAI package not installed")
                return None
        return self._client

    def _get_async_client(self) -> Any:
        """Get AsyncOpenAI client (lazy initialization)."""
        try:
            import openai
            return openai.AsyncOpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
            )
        except ImportError:
            logger.warning("OpenAI package not installed")
            return None

    async def chat(
        self,
        messages: list[dict[str, str]],
        tools: list[dict] | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> str:
        """Send a chat request and get response."""
        client = self._get_client()
        if client is None:
            return "LLM client not available"

        try:
            response = client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=tools,
                tool_choice="auto" if tools else None,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            logger.error(f"LLM chat failed: {e}")
            return f"Error: {str(e)}"

    async def stream(
        self,
        messages: list[dict[str, str]],
        tools: list[dict] | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> AsyncIterator[str]:
        """Stream chat response."""
        client = self._get_async_client()
        if client is None:
            yield "LLM client not available"
            return

        try:
            stream = await client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=tools,
                tool_choice="auto" if tools else None,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
            )

            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        except Exception as e:
            logger.error(f"LLM stream failed: {e}")
            yield f"Error: {str(e)}"


_llm_client: LLMClient | None = None


def get_llm_client() -> LLMClient:
    """Get the global LLM client instance."""
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient()
    return _llm_client
