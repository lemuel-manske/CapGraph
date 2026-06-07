from typing import Annotated

from pydantic import BaseModel

from src.engine.api import (
    AssistantReply,
    Capability,
    CapGraph,
    Injected,
    LoopFrame,
    State,
    ToolCalled,
)
from src.engine.runner import loop
from src.llm.api import Chat, ChatResponse, TokenUsage, ToolCall


def test_text_reply_yields_assistant_reply():
    chat = _stub_chat([_text("hello", 5)])
    frames = _run(loop("root", chat, _graph({}), []))

    assert frames[0].event == AssistantReply(text="hello", tokens=5)


def test_text_reply_frame_carries_state():
    chat = _stub_chat([_text("hello")])
    frames = _run(loop("root", chat, _graph({}), []))

    assert frames[0].state is not None


def test_done_yields_tool_called():
    chat = _stub_chat([_tools(_tc("done"))])
    frames = _run(loop("root", chat, _graph({}), []))

    assert len(frames) == 1
    assert isinstance(frames[0].event, ToolCalled)
    assert frames[0].event.info.function_name == "done"


def test_done_frame_state_has_end_loop_operation():
    chat = _stub_chat([_tools(_tc("done"))])
    frames = _run(loop("root", chat, _graph({}), []))

    assert {"op": "end_loop"} in frames[-1].state.operations


def test_navigate_re_explores_new_node():
    explored = []
    chat = _stub_chat(
        [
            _tools(_tc("navigate", '{"node_name": "b"}')),
            _text("ok"),
        ]
    )
    _run(loop("root", chat, _graph({}, on_explore=explored.append), []))

    assert explored == ["root", "b"]


def test_navigate_updates_node_id_in_context():
    chat = _stub_chat(
        [
            _tools(_tc("navigate", '{"node_name": "b"}')),
            _text("ok"),
        ]
    )
    frames = _run(loop("root", chat, _graph({}), []))

    assert frames[-1].state.get("node_id") == "b"


def test_capability_args_parsed_from_json():
    cap, received = _recording_capability()
    chat = _stub_chat(
        [
            _tools(_tc("record", '{"value": "red"}')),
            _text("ok"),
        ]
    )
    _run(loop("root", chat, _graph({"root": [cap]}), []))

    assert received == ["red"]


# --- helpers ---


def _run(gen) -> list[LoopFrame]:
    frames = []
    try:
        while True:
            frames.append(next(gen))
    except StopIteration:
        return frames


def _stub_chat(responses: list[ChatResponse]) -> Chat:
    class _Stub(Chat):
        def __init__(self):
            self._it = iter(responses)

        def send_message(self, messages, tools=None, tool_choice="auto"):
            return next(self._it)

    return _Stub()


def _graph(caps_by_node: dict, on_explore=None) -> CapGraph:
    class _Stub(CapGraph):
        def __init__(self):
            self._current = None

        def explore(self, capability: str) -> CapGraph:
            if on_explore:
                on_explore(capability)
            self._current = capability
            return self

        def capabilities(self) -> list[Capability]:
            return caps_by_node.get(self._current, [])

    return _Stub()


def _tc(name: str, args: str = "{}") -> ToolCall:
    return ToolCall(tool_call_id=name, function_name=name, arguments=args)


def _text(text: str = "", tokens: int = 0) -> ChatResponse:
    return ChatResponse(text=text, usage=TokenUsage(total_tokens=tokens))


def _tools(*calls: ToolCall) -> ChatResponse:
    return ChatResponse(text="", usage=TokenUsage(), tool_calls=list(calls))


class _RecordingArgs(BaseModel):
    value: str


def _recording_capability():
    received = []

    def _fn(state: Annotated[State, Injected], args: _RecordingArgs):
        received.append(args.value)
        return state

    cap = Capability(
        name="record",
        description="records a value",
        needs=[],
        produces=[],
        fn=_fn,
        takes=_RecordingArgs,
    )
    return cap, received
