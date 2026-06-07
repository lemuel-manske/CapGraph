from src.engine.api import State


def test_get_returns_context_value():
    assert State(schematics_tree="tree").get("schematics_tree") == "tree"


def test_get_returns_default_when_missing():
    assert State().get("missing", "default") == "default"


def test_with_ctx_returns_new_state():
    assert State().with_ctx(node_id="root").get("node_id") == "root"


def test_append_preserves_context():
    assert State(node_id="root").append([{"op": "end_loop"}]).get("node_id") == "root"


def test_append_accumulates_operations():
    original = State(node_id="root")
    updated = original.append([{"op": "end_loop"}])

    assert list(updated.operations) == [{"op": "end_loop"}]
    assert list(original.operations) == []
