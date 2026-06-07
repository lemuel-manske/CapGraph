from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Literal, NotRequired, TypedDict


class ChatMessage(TypedDict):
    """
    Represents a single message in the chat conversation.
    """

    role: Literal["system", "user", "assistant", "tool"]
    content: str | None
    tool_calls: NotRequired[list[dict[str, Any]]]
    tool_call_id: NotRequired[str]


class FunctionDefinition(TypedDict):
    """
    Represents the definition of a function that can be called as a tool by the assistant.
    """

    name: str
    description: str
    parameters: dict[str, Any]


class ToolDefinition(TypedDict):
    """
    Represents a tool that the assistant can call, defined by a function signature.
    """

    tool_type: Literal["function"]
    function: FunctionDefinition


@dataclass(frozen=True)
class ToolCall:
    """
    Represents a single call to a tool by the assistant, including the function name and arguments.
    """

    tool_call_id: str
    function_name: str
    arguments: str

    def is_done(self) -> bool:
        return self.function_name == "done"


@dataclass(frozen=True)
class TokenUsage:
    """
    Represents the token usage for a single chat response, including prompt tokens, completion tokens, and total tokens.
    """

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

    def __add__(self, other: TokenUsage) -> TokenUsage:
        return TokenUsage(
            prompt_tokens=self.prompt_tokens + other.prompt_tokens,
            completion_tokens=self.completion_tokens + other.completion_tokens,
            total_tokens=self.total_tokens + other.total_tokens,
        )


@dataclass(frozen=True)
class ChatResponse:
    """
    Represents the response from the chat model.
    """

    text: str
    usage: TokenUsage
    tool_calls: list[ToolCall] = field(default_factory=list)


type ToolChoice = Literal["auto", "required"]


class ToolValidationError(Exception):
    """
    Raised when tool arguments fail schema validation after all retry attempts.
    """

    def __init__(self, tool_name: str, errors: list[str], attempts: int) -> None:
        self.tool_name = tool_name
        self.errors = errors
        self.attempts = attempts

        error_summary = "; ".join(errors[:3])

        if len(errors) > 3:
            error_summary += f" ... and {len(errors) - 3} more errors"

        super().__init__(
            f"Tool '{tool_name}' validation failed after {attempts} attempts: {error_summary}"
        )


class Chat(ABC):
    """
    Represents an LLM-powered chat.
    """

    @abstractmethod
    def send_message(
        self,
        messages: list[ChatMessage],
        tools: list[ToolDefinition] | None = None,
        tool_choice: ToolChoice = "auto",
    ) -> ChatResponse:
        """
        Sends a message to the chat model and returns the response.
        """

        ...
