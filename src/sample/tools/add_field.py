from typing import Annotated, Literal
from pydantic import BaseModel, Field

from src.engine.api import Injected, Capability, State
from src.sample.domain.api import SchematicsTree
from src.sample.json_patch import PatchOperation


class FieldComponent(BaseModel):
    name: str = Field(
        description="The name of the field."
    )

    ftype: Literal["text", "numeric", "checkbox"] = Field(
        description="The data type of the field"
    )

    required: bool = Field(
        default=False,
        description="Indicates whether the field is required.",
    )

    description: str | None = Field(
        default=None,
        description="A brief description of the field.",
    )


def _serialize(src: FieldComponent) -> dict:
    def serialize_type(ftype: str) -> str:
        types = {
            "text": "string",
            "numeric": "number",
            "checkbox": "boolean",
        }

        return types.get(ftype, "string")

    return {
        "name": src.name,
        "type": serialize_type(src.ftype),
        "required": src.required,
        "description": src.description,
    }


def _fn(
    state: Annotated[State, Injected],
    node_id: Annotated[str, Injected],
    field: FieldComponent
) -> State:
    tree = state.get("schematics_tree", SchematicsTree())

    assert isinstance(tree, SchematicsTree), "schematics_tree must be an instance of SchematicsTree."

    node = tree.at(node_id)

    if node is None:
        raise ValueError(f"Node with id {node_id} not found in schematics tree.")

    ops: list[PatchOperation] = node.add(node_id, _serialize(field))

    state.append(ops)
    return state


def define() -> Capability:
    return Capability(
        cap_id="add_field",
        needs=["form"],
        produces=["field"],
        description="Adds a new field to a form.",
        fn=_fn,
    )
