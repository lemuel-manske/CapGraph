from __future__ import annotations

import logging
from typing import Any

from openai import OpenAI

from .api import Chat, ChatMessage, ChatResponse, TokenUsage, ToolCall, ToolChoice

_BASE_URL = "http://localhost:11434/v1/"


logger = logging.getLogger(__name__)


class OllamaChat(Chat):
    """A Chat implementation that uses Ollama chat API."""

    def __init__(self, model: str) -> None:
        self._model = model
        self._client = OpenAI(base_url=_BASE_URL, api_key="ollama")

    def send_message(
        self,
        messages: list[ChatMessage],
        tools: list[dict] | None = None,
        tool_choice: ToolChoice = "auto",
    ) -> ChatResponse:
        kwargs: dict[str, Any] = {
            "model": self._model,
            "messages": messages,
            "temperature": 0,
        }

        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = tool_choice

        response = self._client.chat.completions.create(**kwargs)
        choice = response.choices[0]

        raw_tool_calls = choice.message.tool_calls or []
        tool_calls = [
            ToolCall(
                tool_call_id=tc.id,
                function_name=tc.function.name,
                arguments=tc.function.arguments,
            )
            for tc in raw_tool_calls
        ]

        usage = TokenUsage(
            prompt_tokens=response.usage.prompt_tokens,
            completion_tokens=response.usage.completion_tokens,
            total_tokens=response.usage.total_tokens,
        )

        logger.info(
            "[OllamaChat] : tool_calls=%d text=%s total_tokens=%s",
            len(tool_calls),
            bool(choice.message.content),
            usage.total_tokens if usage else "n/a",
        )

        return ChatResponse(text=choice.message.content, tool_calls=tool_calls, usage=usage)
