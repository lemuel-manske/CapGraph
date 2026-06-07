import pytest

from src.llm.api import Chat, ChatMessage
from src.llm.ollama_impl import OllamaChat


@pytest.fixture
def chat():
    return OllamaChat(model="gemma3:4b")


def test_hello(chat: Chat):
    msgs = [
        ChatMessage(role="user", content="hello"),
    ]

    response = chat.send_message(msgs)

    assert response
