from src.utils.json_patch import PatchOperation, apply_patches, diff, patches_equal


def test_apply_patches():
    document = {"name": "John", "age": 30, "city": "New York"}

    patches: list[PatchOperation] = [
        {"op": "replace", "path": "/name", "value": "Jane"},
        {"op": "add", "path": "/country", "value": "USA"},
        {"op": "remove", "path": "/age"},
    ]

    expected_result = {"name": "Jane", "city": "New York", "country": "USA"}

    result = apply_patches(document, patches)

    assert result == expected_result, f"Expected {expected_result}, but got {result}"


def test_diff():
    doc = {"name": "John", "age": 30, "city": "New York"}

    modified = {"name": "Jane", "city": "New York", "country": "USA"}

    expected_patches: list[PatchOperation] = [
        {"op": "remove", "path": "/age"},
        {"op": "add", "path": "/country", "value": "USA"},
        {"op": "replace", "path": "/name", "value": "Jane"},
    ]

    patches = diff(doc, modified)

    assert patches_equal(patches, expected_patches), (
        f"Expected {expected_patches}, but got {patches}"
    )
