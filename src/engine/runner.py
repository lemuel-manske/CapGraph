import inspect
import json
from typing import Generator

from src.engine.api import (
    AssistantReply,
    Capability,
    CapGraph,
    LoopFrame,
    State,
    ToolCalled,
)
from src.engine.tools import DEFINITIONS
from src.engine.utils import base_type, is_injected
from src.llm.api import Chat, ChatMessage, ToolCall


def loop(
    anchor: str,
    chat: Chat,
    graph: CapGraph,
    history: list[ChatMessage],
    **ctx,
) -> Generator[LoopFrame]:
    _history = list(history)

    def _turn(current_node: str, state: State) -> Generator[LoopFrame]:
        capabilities = _available_capabilities(graph.explore(current_node))
        response = chat.send_message(
            messages=_history, tools=[c.model_json_schema() for c in capabilities]
        )

        if not response.tool_calls:
            yield LoopFrame(
                event=AssistantReply(text=response.text, tokens=response.usage.total_tokens),
                state=state,
            )

            return

        _history.append(
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": tc.tool_call_id,
                        "type": "function",
                        "function": {"name": tc.function_name, "arguments": tc.arguments},
                    }
                    for tc in response.tool_calls
                ],
            }
        )

        for tool_call in response.tool_calls:
            state = _call(_find_capability(tool_call.function_name, capabilities), state, tool_call)

            yield LoopFrame(event=ToolCalled(info=tool_call), state=state)

            _history.append(
                {
                    "role": "tool",
                    "content": "done",
                    "tool_call_id": tool_call.tool_call_id,
                }
            )

        last_op = state.operations[-1] if state.operations else None

        if last_op and last_op["op"] == "end_loop":
            return

        if last_op and last_op["op"] == "navigate":
            yield from _turn(last_op["target"], state.with_ctx(node_id=last_op["target"]))
        else:
            yield from _turn(current_node, state)

    yield from _turn(anchor, State().with_ctx(node_id=anchor, **ctx))


def _call(capability: Capability, state: State, tool_call: ToolCall) -> State:
    kwargs = _resolve_params(capability, state, tool_call)
    return capability.fn(**kwargs)


def _resolve_params(capability: Capability, state: State, tool_call: ToolCall) -> dict:
    sig = inspect.signature(capability.fn)
    kwargs = {}

    model_instance = None
    if capability.takes is not None:
        model_instance = capability.takes.model_validate(json.loads(tool_call.arguments))

    for name, param in sig.parameters.items():
        annotation = param.annotation

        if is_injected(annotation):
            base = base_type(annotation)
            kwargs[name] = state if base is State else state.get(name)
        elif model_instance is not None:
            kwargs[name] = model_instance

    return kwargs


def _available_capabilities(g: CapGraph) -> list[Capability]:
    return g.capabilities() + DEFINITIONS


def _find_capability(name: str, capabilities: list[Capability]) -> Capability:
    for c in capabilities:
        if c.name == name:
            return c

    raise ValueError(f"Tool {name} not found")
