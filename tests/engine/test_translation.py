from pydantic import BaseModel, Field

from src.engine.api import Capability


class SomeModel(BaseModel):
    field: str = Field(..., description="A field in SomeModel")


def test_capability_to_schema():
    _def = Capability(
        takes=SomeModel,
        produces=[],
        needs=[],
        fn=lambda x: x,
        name="test_capability",
        description="A test capability",
    )

    schema = _def.model_json_schema()

    assert schema == {
        "type": "function",
        "function": {
            "name": "test_capability",
            "description": "A test capability",
            "parameters": {
                "type": "object",
                "properties": {
                    "field": {
                        "type": "string",
                        "description": "A field in SomeModel",
                    }
                },
                "required": ["field"],
            },
        },
    }
