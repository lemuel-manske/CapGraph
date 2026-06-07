from unittest.mock import ANY

from src.app.app import run


def test_add_contact_form():
    result = run(
        "root", "build a contact form with name and email fields", {"id": "root", "children": []}
    )

    assert result == {
        "id": "root",
        "children": [
            {
                "componentType": "form",
                "id": ANY,
                "title": ANY,
                "fields": [
                    {
                        "componentType": "field",
                        "id": ANY,
                        "name": ANY,
                        "type": "string",
                        "required": False,
                        "description": None,
                    },
                    {
                        "componentType": "field",
                        "id": ANY,
                        "name": ANY,
                        "type": "string",
                        "required": False,
                        "description": None,
                    },
                ],
            }
        ],
    }
