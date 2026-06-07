from typing import Annotated

from pydantic import BaseModel, Field

from src.engine.api import Capability, Injected, State


class Navigate(BaseModel):
    node_name: str = Field(..., description="The name of the node to navigate to.")


def _fn(state: Annotated[State, Injected], navigate: Navigate):
    node_name = navigate.node_name
    return state.append([{"op": "navigate", "target": node_name}])


DEFINITION = Capability(
    takes=Navigate,
    name="navigate",
    needs=[],
    produces=[":node_name:"],
    description="Navigates to the specified node by it's name.",
    fn=_fn,
)
