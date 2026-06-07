from src.sample.schematics import root


def test_explore():
    s = root.explore('form')

    assert s.capabilities() == [
        'add_field',
    ]
