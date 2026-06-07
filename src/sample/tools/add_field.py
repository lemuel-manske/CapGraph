from typing import Annotated, Literal

from pydantic import BaseModel, Field

from src.engine.api import Capability, Injected, State
from src.sample.domain.api import SchematicsTree
from src.sample.json_schema import get_schema
from src.sample.utils import next_id


class FieldComponent(BaseModel):
    label: str = Field(description="The label of the field.")

    type: Literal["text", "numeric", "checkbox"] = Field(description="The data type of the field")

    required: bool = Field(
        default=False,
        description="Indicates whether the field is required.",
    )

    description: str | None = Field(
        default=None,
        description="A brief description of the field.",
    )


def serialize(src: FieldComponent) -> dict:
    def serialize_type(ftype: str) -> str:
        types = {
            "text": "string",
            "numeric": "number",
            "checkbox": "boolean",
        }

        return types.get(ftype, "string")

    field_schema = get_schema("field")

    return field_schema.wrap(
        {
            "id": next_id(),
            "name": src.label,
            "type": serialize_type(src.type),
            "required": src.required,
            "description": src.description,
        }
    )


def _fn(
    state: Annotated[State, Injected], node_id: Annotated[str, Injected], field: FieldComponent
) -> State:
    tree = state.get("schematics_tree", SchematicsTree())

    assert isinstance(tree, SchematicsTree), (
        "schematics_tree must be an instance of SchematicsTree."
    )

    node = tree.at(node_id)

    if node is None:
        raise ValueError(f"Node with id {node_id} not found in schematics tree.")

    fields = node.get("fields", [])
    new_fields = fields + [serialize(field)]

    return state.append(
        [
            {
                "op": "json_patch",
                "target": f"schematics_tree:{node_id}",
                "patches": [
                    {
                        "op": "replace",
                        "path": "/fields",
                        "value": new_fields,
                    }
                    if fields
                    else {
                        "op": "add",
                        "path": "/fields",
                        "value": new_fields,
                    }
                ],
            }
        ]
    )


DEFINITION = Capability(
    takes=FieldComponent,
    name="add_field",
    needs=["form"],
    produces=["field"],
    description="Adds a new field to a form.",
    fn=_fn,
)
