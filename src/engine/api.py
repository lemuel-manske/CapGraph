from dataclasses import dataclass
from typing import Callable, Sequence, TypedDict


class Injected:
    """
    Marker for injected parameters.
    """

    ...


class Operation(TypedDict):
    """
    An operation to be performed on the engine state.
    """

    ...


class State:
    """
    The engine state.
    """

    def __init__(self):
        self.operations = []

    def append(self, operations: Sequence[Operation]):
        self.operations.append(operations)

    def get(self, key: str, default=None):
        return getattr(self, key, default)


@dataclass
class Capability:
    """
    Defines an engine capability.
    """

    cap_id: str
    description: str

    needs: list[str]
    produces: list[str]

    fn: Callable[...]
