from typing import Annotated

from pydantic import BaseModel, Field

from src.engine.api import Capability, Injected, State
from src.sample.domain.api import SchematicsTree
from src.sample.json_schema import get_schema
from src.sample.utils import next_id

from .add_field import FieldComponent
from .add_field import serialize as serialize_field


class FormComponent(BaseModel):
    title: str = Field(
        description="The title of the form.",
        min_length=1,
        max_length=100,
        pattern=r"^[a-zA-Z0-9\s]+$",
    )

    fields: list[FieldComponent] = Field(
        default_factory=list,
        description="The list of fields in the form.",
        min_length=1,
    )


def serialize(src: FormComponent) -> dict:
    form_schema = get_schema("form")

    return form_schema.wrap(
        {
            "id": next_id(),
            "title": src.title,
            "fields": [serialize_field(field) for field in src.fields],
        }
    )


def _fn(
    state: Annotated[State, Injected], node_id: Annotated[str, Injected], form: FormComponent
) -> State:
    tree = state.get("schematics_tree", SchematicsTree())

    assert isinstance(tree, SchematicsTree), (
        "schematics_tree must be an instance of SchematicsTree."
    )

    node = tree.at(node_id)

    if node is None:
        raise ValueError(f"Node with id {node_id} not found in schematics tree.")

    ops = node.add(node_id, serialize(form))

    return state.append(
        [
            {
                "op": "json_patch",
                "target": f"schematics_tree:{node_id}",
                "patches": ops,
            }
        ]
    )


DEFINITION = Capability(
    takes=FormComponent,
    name="add_form",
    description="Adds a form to the schematics tree.",
    needs=["root"],
    produces=["form"],
    fn=_fn,
)
