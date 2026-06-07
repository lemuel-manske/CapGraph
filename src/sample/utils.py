def next_id() -> str:
    """Generates a unique ID."""

    import uuid

    return str(uuid.uuid4())
