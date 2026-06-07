from typing import Annotated

from src.engine.api import Capability, Injected, State


def _fn(
    state: Annotated[State, Injected],
):
    return state.append([{"op": "end_loop"}])


DEFINITION = Capability(
    name="done",
    needs=[],
    produces=[],
    description="Teels the engine to stop.",
    fn=_fn,
)
