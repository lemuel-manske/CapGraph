from src.sample.json_patch import PatchOperation, apply_patches

def test_apply_patches():
    document = {
        "name": "John",
        "age": 30,
        "city": "New York"
    }

    patches: list[PatchOperation] = [
        {"op": "replace", "path": "/name", "value": "Jane"},
        {"op": "add", "path": "/country", "value": "USA"},
        {"op": "remove", "path": "/age"}
    ]

    expected_result = {
        "name": "Jane",
        "city": "New York",
        "country": "USA"
    }

    result = apply_patches(document, patches)

    assert result == expected_result, f"Expected {expected_result}, but got {result}"
