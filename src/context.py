from contextvars import ContextVar

from src.llm.api import Chat

_chat: ContextVar[Chat] = ContextVar("chat")

"""
ContextVar's are a poor man's DI container.
"""


def set_chat(value: Chat) -> None:
    """Sets the Chat instance for the current request context."""

    _chat.set(value)


def get_chat() -> Chat:
    """Returns the Chat instance for the current request context."""

    return _chat.get()
