from src.sample.schematics import root


def test_explore():
    form = root.explore("form")

    assert [c.name for c in form.capabilities()] == ["add_field"]

    field = form.explore("field")

    assert field.capabilities() == []
