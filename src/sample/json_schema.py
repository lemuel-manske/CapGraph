import copy
import json
from pathlib import Path

import referencing
import referencing.jsonschema
from jsonschema import ValidationError
from jsonschema.validators import validator_for

_SCHEMAS_DIR = Path(__file__).parent / "__schemas__"
_ALL_SCHEMAS = list(_SCHEMAS_DIR.rglob("*.schema.json"))


class JsonSchemaValidationIssue:
    """
    Wraps a jsonschema.ValidationError to a more user-friendly concept.
    """

    def __init__(self, error: ValidationError):
        self.error = error

    @property
    def message(self) -> str:
        return self.error.message


class CompiledSchema(dict):
    """
    A compiled JSON schema, which can be used for navigation.
    """

    ...


class JsonSchema(dict):
    """
    Wraps a dict to a JSON schema concept.
    """

    def __init__(self, *args, registry: referencing.Registry | None = None, **kwargs):
        self._registry = registry
        self._resolver = registry.resolver() if registry else None

        super().__init__(*args, **kwargs)

    def wrap(self, data: dict) -> dict:
        """
        Evolve the given data by assigning default values from the schema,
        merged with provided data.
        """

        compiled = self.compile()
        properties = compiled.get("properties", {})

        result = {}

        for prop_name, prop_schema in properties.items():
            if prop_schema.get("$lazy"):
                if "default" in prop_schema:
                    result[prop_name] = copy.deepcopy(prop_schema["default"])
                continue
            if "const" in prop_schema:
                result[prop_name] = prop_schema["const"]
            elif "default" in prop_schema:
                result[prop_name] = copy.deepcopy(prop_schema["default"])
            elif prop_schema.get("type") == "object" and "properties" in prop_schema:
                nested = JsonSchema(prop_schema).wrap({})
                if nested:
                    result[prop_name] = nested

        result.update(data)

        return result

    def compile(self) -> CompiledSchema:
        """
        Compile the schema into a fully inlined, reference-free dict.
        """

        root = dict(self)
        defs = root.pop("$defs", {})

        return CompiledSchema(self._compile_node(root, defs))

    def validate(self, data: dict) -> list[JsonSchemaValidationIssue]:
        """
        Validate the given data against the schema, returning a list of validation issues if any.
        """

        validator = self._get_validator()

        errors = list(validator.iter_errors(data))

        return [JsonSchemaValidationIssue(error) for error in errors]

    def is_valid(self, data: dict) -> bool:
        """
        Returns whether the given data is valid against the schema.
        """

        errors = self.validate(data)

        return len(errors) == 0

    def _get_validator(self):
        validator_cls = validator_for(self)

        if self._registry:
            return validator_cls(self, registry=self._registry)
        else:
            return validator_cls(self)

    def _compile_property(self, prop: dict, defs: dict) -> dict:
        if set(prop.keys()) == {"$ref"}:
            return self._compile_node(self._resolve_ref(prop["$ref"]), defs)

        items = prop.get("items", {})

        should_lazyfy = (
            isinstance(items, dict)
            and "oneOf" in items
            and all("$ref" in entry for entry in items["oneOf"])
        )

        if should_lazyfy:
            not_items = {k: v for k, v in prop.items() if k != "items"}
            child_ids = [entry["$ref"] for entry in items["oneOf"]]

            return {**not_items, "$lazy": True, "$items": child_ids, "items": {}}

        return self._compile_node(prop, defs)

    def _compile_node(self, node: dict, defs: dict) -> dict:
        if set(node.keys()) == {"$ref"}:
            return self._compile_node(self._resolve_ref(node["$ref"]), defs)

        result = {}

        merged_defs = {**defs, **node.pop("$defs", {})}

        if "$ref" in node:
            ref = node["$ref"]

            target = (
                merged_defs[ref.removeprefix("#/$defs/")]
                if ref.startswith("#/$defs/")
                else self._resolve_ref(ref)
            )

            result.update(self._compile_node(target, merged_defs))

        for key, value in node.items():
            if key in ("$ref", "allOf"):
                continue

            if key == "properties" and isinstance(value, dict):
                result[key] = {k: self._compile_property(v, merged_defs) for k, v in value.items()}
                continue

            result[key] = value

        for entry in node.get("allOf", []):
            for branch_key in ("then", "else"):
                branch = entry.get(branch_key, {})

                for prop_name, prop in branch.get("properties", {}).items():
                    compiled = self._compile_property(prop, merged_defs)

                    if not compiled.get("$lazy"):
                        continue

                    if prop_name not in result.setdefault("properties", {}):
                        result["properties"][prop_name] = compiled
                    else:
                        existing = result["properties"][prop_name]

                        merged_items = list(
                            dict.fromkeys(existing.get("$items", []) + compiled.get("$items", []))
                        )

                        result["properties"][prop_name] = {
                            **existing,
                            "$lazy": True,
                            "$items": merged_items,
                        }

        return result

    def _resolve_ref(self, ref: str) -> dict:
        assert self._resolver, "Cannot resolve reference without a registry"

        return dict(self._resolver.lookup(ref).contents)


def _build_registry() -> referencing.Registry:
    resources = []

    for schema_path in _ALL_SCHEMAS:
        schema = json.loads(schema_path.read_text())

        resource = referencing.Resource.from_contents(
            schema, default_specification=referencing.jsonschema.DRAFT202012
        )

        resources.append((schema["$id"], resource))

    return referencing.Registry().with_resources(resources)


_REGISTRY = _build_registry()


_SCHEMAS_CACHE = {}



def get_schema(name: str) -> JsonSchema:
    """
    Return the JSON schema dict for the given name.
    """

    def _get_raw_schema(name: str) -> dict:
        schema_path = _SCHEMAS_DIR / f"{name}.schema.json"
        return json.loads(schema_path.read_text())

    if (name) in _SCHEMAS_CACHE:
        return _SCHEMAS_CACHE[(name)]

    raw = _get_raw_schema(name)

    s = JsonSchema(raw, registry=_REGISTRY)
    _SCHEMAS_CACHE[(name)] = s

    return s


def get_all_schemas() -> dict[str, JsonSchema]:
    """
    Return a dict of all schemas, keyed by name.
    """

    schemas = {}

    for schema_path in _ALL_SCHEMAS:
        schema = json.loads(schema_path.read_text())
        schemas[schema["$id"]] = JsonSchema(schema, registry=_REGISTRY)

    return schemas
