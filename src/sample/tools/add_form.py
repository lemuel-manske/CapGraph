from typing import Annotated
from pydantic import BaseModel, Field

from src.engine.api import Injected, Capability, State
from src.sample.domain.api import SchematicsTree
from src.sample.json_patch import PatchOperation

from .add_field import FieldComponent, serialize as serialize_field


class FormComponent(BaseModel):
    title: str = Field(
        description="The title of the form."
    )

    fields: list[FieldComponent] = Field(
        default_factory=list,
        description="The list of fields in the form."
    )


def serialize(src: FormComponent) -> dict:
    return {
        "title": src.title,
        "fields": [serialize_field(field) for field in src.fields],
    }


def _fn(
    state: Annotated[State, Injected],
    node_id: Annotated[str, Injected],
    form: FormComponent
) -> State:
    tree = state.get("schematics_tree", SchematicsTree())

    assert isinstance(tree, SchematicsTree), "schematics_tree must be an instance of SchematicsTree."

    node = tree.at(node_id)

    if node is None:
        raise ValueError(f"Node with id {node_id} not found in schematics tree.")

    ops: list[PatchOperation] = node.add(node_id, serialize(form))

    return state.append(ops)


DEFINITION = Capability(
    name="add_form",
    description="Adds a form to the schematics tree.",
    needs=["root"],
    produces=["form"],
    fn=_fn,
)
