"""LLM client wrapper — OpenAI-compatible with function calling.

Provides a unified interface for LLM calls across providers
(OpenAI, Azure OpenAI, Groq, Ollama, etc.).

The client:
- Manages API key injection (never stored in mission state)
- Handles function calling (tool use) protocol
- Enforces JSON-mode output for structured agent responses
- Implements timeout and error handling
"""

from __future__ import annotations

import json
from typing import Any

from tros.config import (
    LLM_API_KEY,
    LLM_BASE_URL,
    LLM_MAX_TOKENS,
    LLM_MODEL,
    LLM_TEMPERATURE,
    LLM_TIMEOUT,
)
from tros.utils.logging import get_logger

logger = get_logger("LLMClient")


class LLMError(Exception):
    """Raised when an LLM call fails."""


class LLMClient:
    """OpenAI-compatible LLM client with function calling support."""

    def __init__(
        self,
        model: str | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        timeout: int | None = None,
    ) -> None:
        self._model = model or LLM_MODEL
        self._api_key = api_key or LLM_API_KEY
        self._base_url = base_url or LLM_BASE_URL
        self._temperature = temperature if temperature is not None else LLM_TEMPERATURE
        self._max_tokens = max_tokens or LLM_MAX_TOKENS
        self._timeout = timeout or LLM_TIMEOUT
        self._client: Any = None

    def _get_client(self) -> Any:
        """Lazy-initialize the OpenAI client."""
        if self._client is None:
            try:
                from openai import OpenAI
            except ImportError:
                raise LLMError(
                    "openai package not installed. "
                    "Run: pip install 'openai>=1.30.0'"
                )
            kwargs: dict[str, Any] = {"api_key": self._api_key, "timeout": self._timeout}
            if self._base_url:
                kwargs["base_url"] = self._base_url
            self._client = OpenAI(**kwargs)
        return self._client

    @property
    def is_available(self) -> bool:
        """Check if the LLM client can be initialized."""
        if not self._api_key:
            return False
        try:
            self._get_client()
            return True
        except LLMError:
            return False

    def chat(
        self,
        system_prompt: str,
        user_message: str,
        tools: list[dict[str, Any]] | None = None,
        tool_results: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Send a chat completion request with optional function calling.

        Args:
            system_prompt: The system instruction for the agent.
            user_message: The user/agent message with context.
            tools: Optional list of tool (function) definitions.
            tool_results: Optional previous tool call results to continue the conversation.

        Returns:
            dict with keys:
            - "content": str — the text response
            - "tool_calls": list — any function calls requested
            - "raw": dict — the full response object
        """
        client = self._get_client()

        messages: list[dict[str, Any]] = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ]

        # Add tool results as assistant + tool messages if present
        if tool_results:
            for tr in tool_results:
                messages.append({
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [{
                        "id": tr["call_id"],
                        "type": "function",
                        "function": {
                            "name": tr["name"],
                            "arguments": json.dumps(tr["arguments"]),
                        },
                    }],
                })
                messages.append({
                    "role": "tool",
                    "tool_call_id": tr["call_id"],
                    "content": json.dumps(tr["result"]),
                })

        kwargs: dict[str, Any] = {
            "model": self._model,
            "messages": messages,
            "temperature": self._temperature,
            "max_tokens": self._max_tokens,
        }

        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        # Force JSON output for structured responses
        kwargs["response_format"] = {"type": "json_object"}

        try:
            logger.info("LLM call: model=%s, tools=%d, temp=%.1f",
                        self._model, len(tools or []), self._temperature)
            response = client.chat.completions.create(**kwargs)
        except Exception as exc:
            logger.error("LLM API call failed: %s", exc)
            raise LLMError(f"LLM API call failed: {exc}") from exc

        # Parse response
        choice = response.choices[0]
        message = choice.message

        result: dict[str, Any] = {
            "content": message.content or "",
            "tool_calls": [],
            "finish_reason": choice.finish_reason,
        }

        # Extract tool calls if present
        if message.tool_calls:
            for tc in message.tool_calls:
                result["tool_calls"].append({
                    "id": tc.id,
                    "name": tc.function.name,
                    "arguments": json.loads(tc.function.arguments),
                })

        logger.info("LLM response: finish_reason=%s, tool_calls=%d, tokens=%s",
                     choice.finish_reason,
                     len(result["tool_calls"]),
                     getattr(response.usage, "total_tokens", "N/A"))

        return result

    def chat_json(
        self,
        system_prompt: str,
        user_message: str,
        tools: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Convenience: call chat() and parse the JSON content directly.

        Returns the parsed JSON dict from the LLM content field.
        Raises LLMError if the content is not valid JSON.
        """
        result = self.chat(system_prompt, user_message, tools=tools)

        if result["tool_calls"]:
            # LLM wants to call a tool — return the tool call info
            return {"_tool_calls": result["tool_calls"]}

        content = result["content"]
        if not content:
            raise LLMError("LLM returned empty content")

        try:
            return json.loads(content)
        except json.JSONDecodeError as exc:
            raise LLMError(f"LLM returned invalid JSON: {exc}") from exc
