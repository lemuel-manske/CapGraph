from src.sample.json_schema import get_schema


def test_field_validates_no_errors():
    schema = get_schema("field")

    data = {
        "name": "test",
        "type": "string",
    }

    errs = schema.validate(data)

    assert errs == []


def test_field_validates_with_errors():
    schema = get_schema("field")

    data = {
        "name": "test",
        "type": "invalid_type",
    }

    errs = schema.validate(data)

    assert len(errs) == 1
    assert errs[0].message == "'invalid_type' is not one of ['string', 'number', 'boolean']"
