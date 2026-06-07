from typing import Annotated, get_args, get_origin

from src.engine.api import Injected


def is_injected(annotation) -> bool:
    """
    Returns whether the it is Injected.
    """

    if get_origin(annotation) is Annotated:
        return Injected in get_args(annotation)[1:]

    return False


def base_type(annotation):
    """
    Returns the base annotation type.
    """

    if get_origin(annotation) is Annotated:
        return get_args(annotation)[0]

    return annotation
