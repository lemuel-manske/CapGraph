from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Callable, Literal, Sequence, TypedDict

from pydantic import BaseModel

from src.llm.api import ToolCall
from src.utils.json_patch import PatchOperation


class Injected:
    """
    Marker for injected parameters.
    """

    ...


class JsonPathOperation(TypedDict):
    """
    Defines a JSON patch operation, which applies a JSON patch to the target JSON document.
    """

    op: Literal["json_patch"]
    target: str
    patches: list[PatchOperation]


class NavigationOperation(TypedDict):
    """
    Defines a navigation operation, which navigates to the target node.
    """

    op: Literal["navigate"]
    target: str


class EndLoopOperation(TypedDict):
    """
    Defines an end loop operation, which tells the engine to stop.
    """

    op: Literal["end_loop"]


type Operation = JsonPathOperation | NavigationOperation | EndLoopOperation


class CapGraph(ABC):
    """
    A capability graph, which defines the capabilities that can be explored from the current node.
    """

    @abstractmethod
    def explore(self, capability: str) -> CapGraph:
        """
        Explores the current graph, and navigates to the target capability, exposing a new set
        of capabilities.
        """

        ...

    @abstractmethod
    def capabilities(self) -> list[Capability]:
        """
        Returns only the capabilities that expand from the current node.
        """

        ...


@dataclass(frozen=True)
class ToolCalled:
    """Emitted after each tool invocation during the engine loop."""

    info: ToolCall


@dataclass(frozen=True)
class AssistantReply:
    """Emitted when the LLM responds with text and no tool calls."""

    tokens: int
    text: str


type EngineEvent = AssistantReply | ToolCalled


@dataclass(frozen=True)
class LoopFrame:
    """Pairs an engine event with the state at the moment it was emitted."""

    event: EngineEvent
    state: State


class State:
    """
    The engine state. Carries both the accumulated operations and an injection
    context that tools can read via state.get().
    """

    def __init__(self, operations: Sequence[Operation] | None = None, **ctx) -> None:
        self._ops = list(operations or [])
        self._ctx = dict(ctx)

    @property
    def operations(self) -> Sequence[Operation]:
        return self._ops

    def append(self, operations: Sequence[Operation]) -> State:
        """Return a new state with operations appended, context preserved."""
        return State([*self._ops, *operations], **self._ctx)

    def with_ctx(self, **kwargs) -> State:
        """Return a new state with context updated."""
        return State(self._ops, **{**self._ctx, **kwargs})

    def get(self, key: str, default=None):
        return self._ctx.get(key, default)


@dataclass
class Capability:
    """
    Defines an engine capability.
    """

    name: str
    description: str

    needs: list[str]
    produces: list[str]

    fn: Callable[...]

    takes: type[BaseModel] | None = None

    def model_json_schema(self) -> dict:
        if self.takes is None:
            return {
                "type": "function",
                "function": {
                    "name": self.name,
                    "description": self.description,
                    "parameters": {"type": "object", "properties": {}, "required": []},
                },
            }

        schema = self.takes.model_json_schema()

        properties = {
            name: {k: v for k, v in field.items() if k != "title"}
            for name, field in schema.get("properties", {}).items()
        }

        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": schema.get("required", []),
                },
            },
        }

    def __call__(self, *args, **kwargs):
        return self.fn(*args, **kwargs)
