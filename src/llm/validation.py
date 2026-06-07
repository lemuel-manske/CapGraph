from __future__ import annotations

import json
import logging
from abc import abstractmethod
from typing import Any

from jsonschema import ValidationError as JsonSchemaValidationError
from jsonschema import validate

logger = logging.getLogger(__name__)


def validate_tool_arguments(
    tool_name: str,
    arguments_json: str,
    tool_definitions: list[dict],
) -> tuple[bool, dict[str, Any] | None, list[str]]:
    """
    Validate tool arguments against the tool's parameter schema.
    """

    try:
        arguments = json.loads(arguments_json)
    except json.JSONDecodeError as e:
        error_msg = f"Invalid JSON in tool arguments: {e}. Expected valid JSON object."

        logger.warning(f"[VALIDATION] Tool '{tool_name}': {error_msg}")

        return False, None, [error_msg]

    tool_def = None

    for tool_def in tool_definitions:
        if tool_def["function"]["name"] == tool_name:
            tool_def = tool_def
            break

    if tool_def is None:
        error_msg = f"Tool '{tool_name}' not found in provided tool definitions"

        logger.warning(f"[VALIDATION] {error_msg}")

        return False, arguments, [error_msg]

    parameter_schema = tool_def["function"].get("parameters", {})

    if not parameter_schema:
        return True, arguments, []

    try:
        validate(instance=arguments, schema=parameter_schema)

        logger.debug(f"[VALIDATION] Tool '{tool_name}': arguments valid")

        return True, arguments, []

    except JsonSchemaValidationError as e:
        error_messages = _format(e)

        logger.warning(
            f"[VALIDATION] Tool '{tool_name}' validation failed: {'; '.join(error_messages)}"
        )

        return False, arguments, error_messages


def _format(err: JsonSchemaValidationError) -> list[str]:
    """
    Format a JsonSchemaValidationError into a human-readable string.
    """

    fmts = {
        "type": TypeErrFmt(),
        "required": RequiredErrFmt(),
        "enum": EnumErrFmt(),
        "additionalProperties": AdditionalPropsErrFmt(),
        "minItems": MinItemsErrFmt(),
        "maxItems": MaxItemsErrFmt(),
    }

    messages = []

    for suberror in err.context:
        messages.extend(_format(suberror))

    assert isinstance(err.validator, str)

    v = fmts.get(err.validator)

    if v:
        messages.append(v.format(err))
    else:
        path = ".".join(str(p) for p in err.absolute_path) if err.absolute_path else "root"
        messages.append(f"{err.message} at path '{path}'")

    return messages


class Formatter:
    @abstractmethod
    def format(self, err: JsonSchemaValidationError) -> str:
        """
        Format a JsonSchemaValidationError into a human-readable string.
        """
        pass


class TypeErrFmt(Formatter):
    def format(self, err: JsonSchemaValidationError) -> str:
        expected_type = err.validator_value
        received_value = err.instance
        received_type = type(received_value).__name__

        path = ".".join(str(p) for p in err.absolute_path)

        return (
            f"'{received_value}' is not of type '{expected_type}' at path "
            f"'{path}'. "
            f"Expected type: {expected_type}, received: {received_type}."
        )


class RequiredErrFmt(Formatter):
    def format(self, err: JsonSchemaValidationError) -> str:
        missing_props = err.validator_value

        assert isinstance(missing_props, list)

        path = ".".join(str(p) for p in err.absolute_path)
        missing = ", ".join(missing_props)

        return f"Missing required properties at path '{path}': {missing}"


class EnumErrFmt(Formatter):
    def format(self, err: JsonSchemaValidationError) -> str:
        allowed_values = err.validator_value
        received_value = err.instance

        path = ".".join(str(p) for p in err.absolute_path)

        return (
            f"'{received_value}' is not one of the allowed values at path "
            f"'{path}'. Allowed: {allowed_values}"
        )


class AdditionalPropsErrFmt(Formatter):
    def format(self, err: JsonSchemaValidationError) -> str:
        assert isinstance(err.instance, dict)
        assert isinstance(err.schema, dict)

        extra_props = [p for p in err.instance.keys() if p not in err.schema.get("properties", {})]

        path = ".".join(str(p) for p in err.absolute_path)
        extra = ", ".join(extra_props)

        return f"Additional properties not allowed at path '{path}': {extra}"


class MinItemsErrFmt(Formatter):
    def format(self, err: JsonSchemaValidationError) -> str:
        assert isinstance(err.instance, list)

        min_items = err.validator_value
        actual_items = len(err.instance)

        path = ".".join(str(p) for p in err.absolute_path)

        return f"Array at path '{path}' has {actual_items} items, minimum {min_items} required"


class MaxItemsErrFmt(Formatter):
    def format(self, err: JsonSchemaValidationError) -> str:
        max_items = err.validator_value

        assert isinstance(err.instance, list)

        actual_items = len(err.instance)

        path = ".".join(str(p) for p in err.absolute_path)

        return f"Array at path '{path}' has {actual_items} items, maximum {max_items} allowed"
